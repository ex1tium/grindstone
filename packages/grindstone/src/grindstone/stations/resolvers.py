"""The kernel's subject resolvers: blobs, blob sets and item revisions (SPEC-06 part 1).

A resolver materializes a subject for a prover from the subject alone, never
from a maker's workspace (I-15), and reads one file of it. It reaches blobs
and items only through the kernel-built context it is given. Factory subject
kinds reduce to these or to their own resolvers (Concepts, "Subjects").
"""

import shutil
from pathlib import Path
from typing import override

from grindstone.contracts.ports import Context, SubjectResolver
from grindstone.contracts.refs import (
    BlobRef,
    BlobSetSubject,
    BlobSubject,
    ItemRevisionSubject,
    SubjectRef,
)


class SubjectMismatchError(ValueError):
    """A resolver was handed a subject of another kind, or a path it does not hold."""


def blob_file_name(blob: BlobRef) -> str:
    """A blob's file name in a materialization: its content hash's hex digits."""
    return blob.sha256.removeprefix("sha256:")


class _BlobFiles:
    """Shared by the blob and blob-set resolvers: members as files named by hash."""

    def _members(self, subject: SubjectRef) -> tuple[BlobRef, ...]:
        raise NotImplementedError

    def materialize(self, ctx: Context, subject: SubjectRef, directory: Path) -> None:
        for blob in self._members(subject):
            with (
                ctx.blobs.open(blob.sha256) as source,
                (directory / blob_file_name(blob)).open("wb") as target,
            ):
                shutil.copyfileobj(source, target)

    def read_file(self, ctx: Context, subject: SubjectRef, path: str) -> bytes:
        for blob in self._members(subject):
            if blob_file_name(blob) == path:
                with ctx.blobs.open(blob.sha256) as source:
                    return source.read()
        raise SubjectMismatchError(f"{path!r} is not a member of the subject")


class BlobResolver(_BlobFiles):
    """Subjects of kind `blob`."""

    @override
    def _members(self, subject: SubjectRef) -> tuple[BlobRef, ...]:
        if not isinstance(subject, BlobSubject):
            raise SubjectMismatchError(f"expected a blob subject, got {subject.kind}")
        return (subject.blob,)


class BlobSetResolver(_BlobFiles):
    """Subjects of kind `blob_set`, members sorted and unique by hash."""

    @override
    def _members(self, subject: SubjectRef) -> tuple[BlobRef, ...]:
        if not isinstance(subject, BlobSetSubject):
            raise SubjectMismatchError(f"expected a blob set subject, got {subject.kind}")
        return subject.members


class ItemRevisionResolver:
    """Subjects of kind `item_revision`: the revision's rendering, as `<ID>.md`."""

    def _ref(self, subject: SubjectRef) -> ItemRevisionSubject:
        if not isinstance(subject, ItemRevisionSubject):
            raise SubjectMismatchError(f"expected an item revision subject, got {subject.kind}")
        return subject

    def materialize(self, ctx: Context, subject: SubjectRef, directory: Path) -> None:
        ref = self._ref(subject).item
        (directory / f"{ref.id}.md").write_text(ctx.items.read(ref).rendered, encoding="utf-8")

    def read_file(self, ctx: Context, subject: SubjectRef, path: str) -> bytes:
        ref = self._ref(subject).item
        if path != f"{ref.id}.md":
            raise SubjectMismatchError(f"{path!r} is not this revision's file")
        return ctx.items.read(ref).rendered.encode("utf-8")


def kernel_resolvers() -> dict[str, SubjectResolver]:
    """The resolver for each kernel subject kind but `git_commit`, which a factory provides."""
    return {
        "blob": BlobResolver(),
        "blob_set": BlobSetResolver(),
        "item_revision": ItemRevisionResolver(),
    }
