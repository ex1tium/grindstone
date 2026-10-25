"""The content-addressed blob store and its roots (SPEC-02, REQ-0209 to REQ-0212, ADR-04).

Every file that is not a commit lives here, under the SHA-256 of its bytes,
at `<blobs_dir>/<h0h1>/<h2h3>/<hex>`. Only the control plane writes it.

- `put_blob` streams content to a temporary file in `.tmp/`, hashing and
  counting, refuses at once past the per-blob limit, and `fsync`s. Then, in
  one unit of work, it checks the project's allowance, renames the file into
  place, and records the blob with a lease root for its producer. A crash
  after the rename leaves a file with no row, which the next put of the same
  content reuses; garbage collection (SPEC-27) removes it otherwise.
- A blob row never commits without a root (REQ-0210); the database checks it
  at commit. Modules add and release roots only through `add_root`,
  `release_root` and `release_leases`, inside their own unit of work, so a
  reference and its root commit together.
- `open_blob` returns a reader that hashes as it streams and fails with
  `invariant_violated` at the end if the bytes do not match their name.

Blob contents are untrusted bytes: the store never interprets them, and
media types are recorded, not trusted. In M1 the store never deletes a blob.
"""

import errno
import hashlib
import io
import os
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import BinaryIO, NewType, Protocol, Self

from grindstone.contracts import BlobRef, new_record_id
from grindstone.contracts.ids import ProjectId
from grindstone.contracts.store import BlobRoot, StoreSettings
from grindstone.store.errors import StoreError
from grindstone.store.steps import kill_point
from grindstone.store.uow import Uow, unit_of_work

RootId = NewType("RootId", uuid.UUID)

TMP_DIR = ".tmp"
KILL_AFTER_RENAME = "after:store.put_blob.rename"
"""Between the rename into place and the commit of the blob's row (AC-0209-2)."""

_CHUNK_BYTES = 1024 * 1024
_HASH_PREFIX = "sha256:"


class Readable(Protocol):
    def read(self, size: int = -1, /) -> bytes: ...


@dataclass(frozen=True, slots=True)
class BlobOwner:
    """The run or job that produces a blob, and so holds its lease root."""

    module: str
    kind: str
    id: str


@dataclass(frozen=True, slots=True)
class StoredBlob:
    """A blob as recorded, and the producer's lease root on it."""

    ref: BlobRef
    root: RootId


class BlobReader:
    """A stored blob's bytes, checked against their hash as they are read.

    The check completes at the end of the stream: the read that reaches it
    raises `StoreError("invariant_violated")` if the bytes do not match, so a
    caller must read to the end before trusting what it read.
    """

    __slots__ = ("_digest", "_file", "_seen", "_verified", "ref")

    def __init__(self, file: BinaryIO, ref: BlobRef) -> None:
        self._file = file
        self._digest = hashlib.sha256()
        self._seen = 0
        self._verified = False
        self.ref = ref

    def read(self, size: int = -1, /) -> bytes:
        data = self._file.read(size)
        self._digest.update(data)
        self._seen += len(data)
        if self._seen > self.ref.size:
            self._corrupt()
        if size < 0 or not data:
            self._verify()
        return data

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def _verify(self) -> None:
        if self._verified:
            return
        sha256 = _HASH_PREFIX + self._digest.hexdigest()
        if self._seen != self.ref.size or sha256 != self.ref.sha256:
            self._corrupt()
        self._verified = True

    def _corrupt(self) -> None:
        raise StoreError(
            "invariant_violated",
            f"blob {self.ref.sha256}: the stored bytes do not match their hash",
            detail={"blob": self.ref.sha256},
        )


class BlobStore:
    """The blob store on one directory, with its limits."""

    __slots__ = ("directory", "settings")

    def __init__(self, settings: StoreSettings) -> None:
        self.settings = settings
        self.directory = Path(settings.blobs_dir)

    def path_of(self, sha256: str) -> Path:
        """Where the bytes of `sha256` live: a two-level fan-out of the hash."""
        hex_digest = sha256.removeprefix(_HASH_PREFIX)
        return self.directory / hex_digest[0:2] / hex_digest[2:4] / hex_digest

    def put(
        self,
        content: bytes | Readable,
        *,
        media_type: str,
        project: ProjectId,
        owner: BlobOwner,
    ) -> StoredBlob:
        """Store `content` once and give `owner` a lease root on it in `project`.

        Putting content already stored adds only the root; putting it again
        for the same owner returns that owner's existing root. The returned
        reference carries the media type first recorded for the content.
        Raises `StoreError("storage_limit")` past the per-blob limit, past the
        project's remaining allowance, or when the volume is full; nothing is
        recorded then, and no file is left behind.
        """
        source: Readable = io.BytesIO(content) if isinstance(content, bytes) else content
        tmp_dir = self.directory / TMP_DIR
        tmp_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=tmp_dir)
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as out:
                sha256, size = self._copy(source, out)
                out.flush()
                os.fsync(out.fileno())
            target = self.path_of(sha256)
            root = BlobRoot(
                blob=BlobRef(sha256=sha256, media_type=media_type, size=size),
                project=project,
                owner_module=owner.module,
                owner_kind=owner.kind,
                owner_id=owner.id,
                lease=True,
            )

            def record(uow: Uow) -> StoredBlob:
                held = _held_root(uow, root)
                if held is None:
                    _check_allowance(uow, root, self.settings.max_project_bytes)
                    # A retried transaction finds the file already in place.
                    if tmp.exists():
                        _move_into_place(tmp, target)
                    kill_point(KILL_AFTER_RENAME)
                    _insert_blob(uow, root.blob)
                    held = _insert_root(uow, root)
                return StoredBlob(ref=_recorded_ref(uow, sha256), root=held)

            return unit_of_work(record)
        except OSError as exc:
            if exc.errno == errno.ENOSPC:
                raise StoreError(
                    "storage_limit", "the blob store's volume is full", detail={"cause": "ENOSPC"}
                ) from None
            raise
        finally:
            tmp.unlink(missing_ok=True)

    def open(self, sha256: str) -> BlobReader:
        """A reader of the recorded blob `sha256`.

        Raises `StoreError("reference_unresolved")` when no blob of that hash
        is recorded, even if a file of that name exists, and
        `StoreError("invariant_violated")` when one is recorded but its file
        is gone.
        """
        ref = unit_of_work(lambda uow: _recorded_ref_or_none(uow, sha256))
        if ref is None:
            raise StoreError(
                "reference_unresolved", f"no blob {sha256} is recorded", detail={"blob": sha256}
            )
        try:
            file = self.path_of(sha256).open("rb")
        except FileNotFoundError:
            raise StoreError(
                "invariant_violated",
                f"blob {sha256} is recorded but its file is missing",
                detail={"blob": sha256},
            ) from None
        return BlobReader(file, ref)

    def _copy(self, source: Readable, out: BinaryIO) -> tuple[str, int]:
        """Copy `source` to `out`, returning its hash and size; refuse past the per-blob limit."""
        digest = hashlib.sha256()
        size = 0
        limit = self.settings.max_blob_bytes
        while chunk := source.read(_CHUNK_BYTES):
            size += len(chunk)
            if size > limit:
                raise StoreError(
                    "storage_limit",
                    f"the blob exceeds the per-blob limit of {limit} bytes",
                    detail={"limit": "max_blob_bytes", "max_bytes": limit},
                )
            digest.update(chunk)
            out.write(chunk)
        return _HASH_PREFIX + digest.hexdigest(), size


def add_root(uow: Uow, root: BlobRoot) -> RootId:
    """Root a recorded blob for `root`'s owner, in the caller's unit of work.

    Returns the owner's existing unreleased root when there is one. Raises
    `StoreError("reference_unresolved")` for a blob that is not recorded.
    """
    if _recorded_ref_or_none(uow, root.blob.sha256) is None:
        raise StoreError(
            "reference_unresolved",
            f"no blob {root.blob.sha256} is recorded",
            detail={"blob": root.blob.sha256},
        )
    held = _held_root(uow, root)
    return held if held is not None else _insert_root(uow, root)


def release_root(uow: Uow, root: RootId) -> bool:
    """Release one root; False if it was already released or never existed."""
    released = uow.execute(
        "UPDATE store.blob_roots SET released_at = now() WHERE id = :id AND released_at IS NULL",
        {"id": root},
    )
    return released == 1


def release_leases(uow: Uow, owner_kind: str, owner_id: str) -> int:
    """End every lease root a run or job holds, when it is archived; returns how many."""
    return uow.execute(
        "UPDATE store.blob_roots SET released_at = now()"
        " WHERE owner_kind = :kind AND owner_id = :id AND lease AND released_at IS NULL",
        {"kind": owner_kind, "id": owner_id},
    )


def project_usage(uow: Uow, project: ProjectId) -> int:
    """Bytes `project` holds: each distinct blob with an unreleased root there, once."""
    row = uow.fetch_one(
        "SELECT bytes FROM store.project_blob_bytes WHERE project = :project", {"project": project}
    )
    return int(row["bytes"]) if row is not None else 0


class _Active:
    """Holds the blob store `open_blob_store` set up for this process."""

    store: BlobStore | None = None


_active = _Active()


def open_blob_store(settings: StoreSettings) -> BlobStore:
    """Set up the process's blob store at start-up."""
    if _active.store is not None:
        raise RuntimeError("the blob store is already open in this process")
    _active.store = BlobStore(settings)
    return _active.store


def close_blob_store() -> None:
    """Forget the process's blob store; `open_blob_store` may run again afterwards."""
    _active.store = None


def current_blob_store() -> BlobStore:
    """The blob store `open_blob_store` set up for this process."""
    if _active.store is None:
        raise RuntimeError("the blob store is not open: call open_blob_store() at start-up")
    return _active.store


def put_blob(
    content: bytes | Readable, *, media_type: str, project: ProjectId, owner: BlobOwner
) -> StoredBlob:
    """`BlobStore.put` on the process's blob store."""
    return current_blob_store().put(content, media_type=media_type, project=project, owner=owner)


def open_blob(sha256: str) -> BlobReader:
    """`BlobStore.open` on the process's blob store."""
    return current_blob_store().open(sha256)


def _move_into_place(tmp: Path, target: Path) -> None:
    """Rename the fsynced file to its name, and make the rename durable."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp.replace(target)
    if sys.platform != "win32":  # Windows cannot open a directory to fsync it.
        dir_fd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)


def _held_root(uow: Uow, root: BlobRoot) -> RootId | None:
    row = uow.fetch_one(
        "SELECT id FROM store.blob_roots"
        " WHERE blob = :blob AND project = :project AND owner_module = :module"
        " AND owner_kind = :kind AND owner_id = :id AND lease = :lease AND released_at IS NULL",
        _root_params(root),
    )
    return RootId(row["id"]) if row is not None else None


def _check_allowance(uow: Uow, root: BlobRoot, max_project_bytes: int) -> None:
    """Refuse a root that would take its project past its limit; one already held there is free."""
    already = uow.fetch_one(
        "SELECT 1 FROM store.blob_roots"
        " WHERE blob = :blob AND project = :project AND released_at IS NULL",
        {"blob": root.blob.sha256, "project": root.project},
    )
    if already is not None:
        return
    held = project_usage(uow, root.project)
    if held + root.blob.size > max_project_bytes:
        raise StoreError(
            "storage_limit",
            f"the blob would take project {root.project} past its limit"
            f" of {max_project_bytes} bytes",
            detail={
                "limit": "max_project_bytes",
                "max_bytes": max_project_bytes,
                "held_bytes": held,
                "blob_bytes": root.blob.size,
            },
        )


def _insert_blob(uow: Uow, ref: BlobRef) -> None:
    uow.execute(
        "INSERT INTO store.blobs (sha256, size, media_type) VALUES (:sha256, :size, :media_type)"
        " ON CONFLICT (sha256) DO NOTHING",
        {"sha256": ref.sha256, "size": ref.size, "media_type": ref.media_type},
    )


def _insert_root(uow: Uow, root: BlobRoot) -> RootId:
    root_id = RootId(new_record_id())
    uow.execute(
        "INSERT INTO store.blob_roots"
        " (id, blob, project, owner_module, owner_kind, owner_id, lease)"
        " VALUES (:root, :blob, :project, :module, :kind, :id, :lease)",
        {"root": root_id, **_root_params(root)},
    )
    return root_id


def _root_params(root: BlobRoot) -> dict[str, object]:
    return {
        "blob": root.blob.sha256,
        "project": root.project,
        "module": root.owner_module,
        "kind": root.owner_kind,
        "id": root.owner_id,
        "lease": root.lease,
    }


def _recorded_ref_or_none(uow: Uow, sha256: str) -> BlobRef | None:
    row = uow.fetch_one(
        "SELECT sha256, size, media_type FROM store.blobs WHERE sha256 = :sha256",
        {"sha256": sha256},
    )
    if row is None:
        return None
    return BlobRef(sha256=row["sha256"], media_type=row["media_type"], size=row["size"])


def _recorded_ref(uow: Uow, sha256: str) -> BlobRef:
    ref = _recorded_ref_or_none(uow, sha256)
    if ref is None:  # pragma: no cover - recorded in the same transaction
        raise AssertionError(f"blob {sha256} vanished inside its own transaction")
    return ref
