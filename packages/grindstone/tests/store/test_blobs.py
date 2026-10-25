"""SPEC-02, TKT-0205: the blob store and its roots (REQ-0209 to REQ-0212)."""

import hashlib
import io
import os
import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from packages.grindstone.tests.store.blob_child import CONTENT, OWNER
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from grindstone.contracts import BlobRef
from grindstone.contracts.ids import ProjectId
from grindstone.contracts.store import BlobRoot, StoreSettings
from grindstone.store import (
    KILL_AFTER_RENAME,
    KILL_AT_ENV,
    KILL_MARKER_ENV,
    BlobOwner,
    BlobReader,
    BlobStore,
    Database,
    RootId,
    StoreError,
    Uow,
    add_root,
    close_blob_store,
    open_blob,
    open_blob_store,
    project_usage,
    put_blob,
    release_leases,
    release_root,
    unit_of_work,
)

pytestmark = pytest.mark.integration

REPO = Path(__file__).resolve().parents[4]
CHILD_MODULE = "packages.grindstone.tests.store.blob_child"

RUN_A = BlobOwner(module="stations", kind="run", id="run-a")
RUN_B = BlobOwner(module="stations", kind="run", id="run-b")


def _project() -> ProjectId:
    return ProjectId(uuid.uuid4())


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _files(directory: Path) -> list[Path]:
    """Every stored blob file, leaving out temporary files."""
    return sorted(p for p in directory.rglob("*") if p.is_file() and ".tmp" not in p.parts)


def _read_in_chunks(reader: BlobReader) -> None:
    while reader.read(8):
        pass


def _counts(engine: Engine) -> tuple[int, int]:
    with engine.connect() as conn:
        blobs = conn.execute(text("SELECT count(*) FROM store.blobs")).scalar_one()
        roots = conn.execute(text("SELECT count(*) FROM store.blob_roots")).scalar_one()
    return blobs, roots


@pytest.fixture
def blobs(store: Database, tmp_path: Path) -> Iterator[BlobStore]:
    """The process's blob store on a fresh directory, with small limits."""
    del store
    blob_store = open_blob_store(
        StoreSettings(blobs_dir=str(tmp_path / "blobs"), max_blob_bytes=64, max_project_bytes=100)
    )
    try:
        yield blob_store
    finally:
        close_blob_store()


def test_put_blob_is_content_addressed(blobs: BlobStore, engine: Engine) -> None:
    """AC-0209-1."""
    project = _project()
    data = b"the same bytes, twice"

    first = put_blob(data, media_type="text/plain", project=project, owner=RUN_A)
    second = put_blob(io.BytesIO(data), media_type="text/markdown", project=project, owner=RUN_B)
    again = put_blob(data, media_type="text/plain", project=project, owner=RUN_A)

    assert first.ref == BlobRef(sha256=_sha256(data), media_type="text/plain", size=len(data))
    # The media type first recorded stays; it is recorded, not trusted.
    assert second.ref == first.ref
    assert second.root != first.root
    assert again.root == first.root
    assert _counts(engine) == (1, 2)

    hex_digest = first.ref.sha256.removeprefix("sha256:")
    path = blobs.directory / hex_digest[:2] / hex_digest[2:4] / hex_digest
    assert _files(blobs.directory) == [path]
    assert _sha256(path.read_bytes()) == first.ref.sha256
    assert not list((blobs.directory / ".tmp").iterdir())


def test_put_blob_crash_records_once(
    blobs: BlobStore, database_url: str, engine: Engine, tmp_path: Path
) -> None:
    """AC-0209-2."""
    project = _project()
    env = {
        **os.environ,
        KILL_AT_ENV: KILL_AFTER_RENAME,
        KILL_MARKER_ENV: str(tmp_path / "killed"),
    }
    killed = subprocess.run(
        [sys.executable, "-m", CHILD_MODULE, database_url, str(blobs.directory), str(project)],
        cwd=REPO,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert killed.returncode != 0, killed.stderr
    # The file was renamed into place; its row never committed.
    assert [_sha256(p.read_bytes()) for p in _files(blobs.directory)] == [_sha256(CONTENT)]
    assert _counts(engine) == (0, 0)

    stored = put_blob(CONTENT, media_type="text/plain", project=project, owner=OWNER)
    put_blob(CONTENT, media_type="text/plain", project=project, owner=OWNER)

    assert stored.ref.sha256 == _sha256(CONTENT)
    assert _counts(engine) == (1, 1)
    assert len(_files(blobs.directory)) == 1


_OPERATIONS = st.lists(
    st.one_of(
        st.tuples(st.just("put"), st.integers(0, 3), st.integers(0, 2)),
        st.tuples(st.just("root"), st.integers(0, 3), st.integers(0, 2)),
        st.tuples(st.just("release"), st.integers(0, 7), st.just(0)),
        st.tuples(st.just("archive"), st.integers(0, 2), st.just(0)),
    ),
    min_size=1,
    max_size=12,
)


@settings(
    max_examples=25, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(operations=_OPERATIONS)
def test_every_blob_is_rooted(
    blobs: BlobStore, engine: Engine, operations: list[tuple[str, int, int]]
) -> None:
    """AC-0210-1: every blob row had a root at its own commit, whatever follows."""
    del blobs
    project = _project()
    tag = uuid.uuid4().hex
    contents = [f"{tag[:8]}-{n}".encode() for n in range(4)]  # within the 100-byte allowance
    owners = [BlobOwner(module="stations", kind="run", id=f"{tag}-{n}") for n in range(3)]
    roots: list[RootId] = []
    stored: dict[int, BlobRef] = {}

    for op, a, b in operations:
        if op == "put":
            result = put_blob(
                contents[a], media_type="text/plain", project=project, owner=owners[b]
            )
            stored[a] = result.ref
            roots.append(result.root)
        elif op == "root" and a in stored:
            root = BlobRoot(
                blob=stored[a],
                project=project,
                owner_module="intent",
                owner_kind="item_revision",
                owner_id=f"{tag}-{b}",
                lease=False,
            )
            roots.append(unit_of_work(lambda uow, r=root: add_root(uow, r)))
        elif op == "release" and roots:
            root_id = roots[a % len(roots)]
            unit_of_work(lambda uow, r=root_id: release_root(uow, r))
        elif op == "archive":
            unit_of_work(lambda uow, owner=owners[a]: release_leases(uow, owner.kind, owner.id))

        with engine.connect() as conn:
            unrooted = conn.execute(
                text(
                    "SELECT b.sha256 FROM store.blobs b WHERE NOT EXISTS"
                    " (SELECT 1 FROM store.blob_roots r WHERE r.blob = b.sha256"
                    "  AND r.created_at <= b.first_seen)"
                )
            ).all()
        assert unrooted == []


def test_blob_rows_cannot_commit_without_a_root(store: Database) -> None:
    """REQ-0210, enforced by the database: a bare blob row fails at commit."""
    del store

    def bare(uow: Uow) -> None:
        uow.execute(
            "INSERT INTO store.blobs (sha256, size, media_type) VALUES (:h, 0, 'text/plain')",
            {"h": _sha256(b"")},
        )

    with pytest.raises(DBAPIError, match="without a root"):
        unit_of_work(bare)


def test_roots_are_released_once_and_blobs_never_change(blobs: BlobStore) -> None:
    del blobs
    project = _project()
    stored = put_blob(b"held", media_type="text/plain", project=project, owner=RUN_A)

    assert unit_of_work(lambda uow: release_root(uow, stored.root))
    assert not unit_of_work(lambda uow: release_root(uow, stored.root))
    for statement in (
        "UPDATE store.blob_roots SET released_at = NULL",
        "UPDATE store.blob_roots SET owner_id = 'other'",
        "DELETE FROM store.blob_roots",
        "UPDATE store.blobs SET media_type = 'text/html'",
        "DELETE FROM store.blobs",
    ):
        with pytest.raises(DBAPIError, match=r"insert-only|released, once"):
            unit_of_work(lambda uow, s=statement: uow.execute(s))


def test_leases_end_with_their_owner_and_usage_counts_each_blob_once(blobs: BlobStore) -> None:
    del blobs
    project = _project()
    a = put_blob(b"0123456789", media_type="text/plain", project=project, owner=RUN_A)
    put_blob(b"0123456789", media_type="text/plain", project=project, owner=RUN_B)
    put_blob(b"abcde", media_type="text/plain", project=project, owner=RUN_A)
    reference = BlobRoot(
        blob=a.ref,
        project=project,
        owner_module="intent",
        owner_kind="item_revision",
        owner_id="rev-1",
        lease=False,
    )
    kept = unit_of_work(lambda uow: add_root(uow, reference))

    assert unit_of_work(lambda uow: add_root(uow, reference)) == kept
    assert unit_of_work(lambda uow: project_usage(uow, project)) == 15
    assert unit_of_work(lambda uow: release_leases(uow, RUN_A.kind, RUN_A.id)) == 2
    assert unit_of_work(lambda uow: project_usage(uow, project)) == 10
    assert unit_of_work(lambda uow: release_leases(uow, RUN_B.kind, RUN_B.id)) == 1
    # The reference root still holds the blob; it is not a lease.
    assert unit_of_work(lambda uow: project_usage(uow, project)) == 10
    assert unit_of_work(lambda uow: project_usage(uow, _project())) == 0

    missing = reference.model_copy(
        update={"blob": BlobRef(sha256=_sha256(b"no"), media_type="x", size=2)}
    )
    with pytest.raises(StoreError) as refused:
        unit_of_work(lambda uow: add_root(uow, missing))
    assert refused.value.code == "reference_unresolved"


def test_storage_limits_refuse_cleanly(blobs: BlobStore, engine: Engine) -> None:
    """AC-0211-1."""
    project = _project()

    with pytest.raises(StoreError) as too_big:
        put_blob(b"x" * 65, media_type="text/plain", project=project, owner=RUN_A)
    assert too_big.value.code == "storage_limit"
    assert too_big.value.envelope().error_class.value == "limit"
    assert _files(blobs.directory) == []
    assert _counts(engine) == (0, 0)

    put_blob(b"a" * 60, media_type="text/plain", project=project, owner=RUN_A)
    with pytest.raises(StoreError) as over_project:
        put_blob(b"b" * 41, media_type="text/plain", project=project, owner=RUN_A)
    assert over_project.value.code == "storage_limit"
    assert over_project.value.detail["limit"] == "max_project_bytes"
    assert len(_files(blobs.directory)) == 1
    assert _counts(engine) == (1, 1)
    assert not list((blobs.directory / ".tmp").iterdir())

    # Content the project already holds costs nothing more; another project has its own allowance.
    put_blob(b"a" * 60, media_type="text/plain", project=project, owner=RUN_B)
    put_blob(b"b" * 40, media_type="text/plain", project=project, owner=RUN_B)
    put_blob(b"b" * 41, media_type="text/plain", project=_project(), owner=RUN_B)
    assert _counts(engine) == (3, 4)


def test_open_blob_detects_corruption(blobs: BlobStore) -> None:
    """AC-0212-1."""
    data = b"bytes that must not change"
    stored = put_blob(data, media_type="text/plain", project=_project(), owner=RUN_A)

    with open_blob(stored.ref.sha256) as reader:
        assert reader.read() == data
        assert reader.ref == stored.ref

    blobs.path_of(stored.ref.sha256).write_bytes(b"bytes that must not chang3")
    with open_blob(stored.ref.sha256) as reader, pytest.raises(StoreError) as altered:
        _read_in_chunks(reader)
    assert altered.value.code == "invariant_violated"

    blobs.path_of(stored.ref.sha256).write_bytes(data + b"!")
    with open_blob(stored.ref.sha256) as reader, pytest.raises(StoreError) as longer:
        reader.read()
    assert longer.value.code == "invariant_violated"


def test_open_blob_serves_only_recorded_blobs(blobs: BlobStore) -> None:
    unrecorded = b"a file with no row"
    path = blobs.path_of(_sha256(unrecorded))
    path.parent.mkdir(parents=True)
    path.write_bytes(unrecorded)
    with pytest.raises(StoreError) as refused:
        open_blob(_sha256(unrecorded))
    assert refused.value.code == "reference_unresolved"

    stored = put_blob(b"gone", media_type="text/plain", project=_project(), owner=RUN_A)
    blobs.path_of(stored.ref.sha256).unlink()
    with pytest.raises(StoreError) as missing:
        open_blob(stored.ref.sha256)
    assert missing.value.code == "invariant_violated"
