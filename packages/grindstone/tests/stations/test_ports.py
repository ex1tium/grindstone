"""SPEC-06 part 1, TKT-0607: the workspace ports, their contracts and the kernel resolvers."""

import io
import typing
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

import pytest
from pydantic import TypeAdapter

from grindstone import sdk
from grindstone.contracts.evidence import CheckSpec
from grindstone.contracts.ids import ProjectId, RunId, TaskId, new_record_id
from grindstone.contracts.platform import TaskMode
from grindstone.contracts.ports import PinnedItem
from grindstone.contracts.refs import (
    BlobRef,
    BlobSetSubject,
    BlobSubject,
    GitCommitSubject,
    ItemRef,
    ItemRevisionSubject,
)
from grindstone.contracts.stations import Collected, CollectRefused, PermissionRequest
from grindstone.stations import SubjectMismatchError, blob_file_name, kernel_resolvers

H1, H2 = "sha256:" + "1" * 64, "sha256:" + "2" * 64


# A provider and a resolver in the `notes` style, written against the SDK alone.


class NotesProvider:
    def prepare(self, ctx: sdk.RunContext) -> sdk.Materialization:
        return sdk.Materialization(archive=f"staging/{ctx.run}.tar", base=ctx.base)

    def collect(self, ctx: sdk.RunContext) -> sdk.CollectOutcome:
        note = BlobRef(sha256=H1, media_type="text/markdown", size=12)
        return Collected(
            subject=BlobSubject(blob=note),
            extra_checks=(CheckSpec(method="notes.read_review", by="notes.review"),),
            prover_context=(note,),
        )

    def discard(self, ctx: sdk.RunContext) -> None:
        return None


class NotesResolver:
    def materialize(self, ctx: sdk.Context, subject: sdk.SubjectRef, directory: Path) -> None:
        (directory / "note.md").write_text("A note.\n", encoding="utf-8")

    def read_file(self, ctx: sdk.Context, subject: sdk.SubjectRef, path: str) -> bytes:
        return b"A note.\n"


# A kernel-built context, as the composition root would build it.


@dataclass
class _Blobs:
    content: dict[str, bytes]

    def open(self, sha256: str) -> BinaryIO:
        return io.BytesIO(self.content[sha256])


@dataclass
class _Items:
    rendered: str

    def read(self, ref: ItemRef) -> PinnedItem:
        return PinnedItem(ref=ref, kind="notes.note", title="t", rendered=self.rendered)


class _Storage:
    def directory(self) -> Path:
        return Path("unused")


class _Secrets:
    def read(self, name: str) -> str:
        raise KeyError(name)


@dataclass
class _RunContext:
    blobs: _Blobs = field(default_factory=lambda: _Blobs({H1: b"one", H2: b"two"}))
    items: _Items = field(default_factory=lambda: _Items("# N-3 — Note\n"))
    project: ProjectId = field(default_factory=lambda: ProjectId(new_record_id()))
    factory: str = "notes"
    storage: _Storage = field(default_factory=_Storage)
    secrets: _Secrets = field(default_factory=_Secrets)
    run: RunId = field(default_factory=lambda: RunId(new_record_id()))
    task: TaskId = field(default_factory=lambda: TaskId(new_record_id()))
    mode: TaskMode = TaskMode.WORK
    workspace_ref: str = "notes-run"
    base: GitCommitSubject | None = None


def test_workspace_ports(tmp_path: Path) -> None:
    provider: sdk.WorkspaceProvider = NotesProvider()
    resolver: sdk.SubjectResolver = NotesResolver()
    ctx: sdk.RunContext = _RunContext()
    assert provider.prepare(ctx).archive == f"staging/{ctx.run}.tar"
    resolver.materialize(
        ctx, BlobSubject(blob=BlobRef(sha256=H1, media_type="a/b", size=1)), tmp_path
    )
    assert (tmp_path / "note.md").read_text(encoding="utf-8") == "A note.\n"

    outcome = provider.collect(ctx)
    adapter: TypeAdapter[sdk.CollectOutcome] = TypeAdapter(sdk.CollectOutcome)
    assert adapter.validate_json(adapter.dump_json(outcome)) == outcome
    assert isinstance(outcome, Collected)
    assert outcome.prover_context
    assert outcome.extra_checks[0].by == "notes.review"
    refused = CollectRefused(paths=(".grindstone/config.toml",), cause="protected path")
    assert adapter.validate_json(adapter.dump_json(refused)) == refused
    PermissionRequest(action="write .github/", reason="CI configuration changes need a person")

    # A factory cannot obtain a context for another factory: the SDK offers
    # protocols and no constructor, and contexts come only from kernel code.
    for name in ("Context", "RunContext"):
        assert typing.is_protocol(getattr(sdk, name))
    assert not any("context_for" in name for name in sdk.__all__)
    with pytest.raises(TypeError):
        sdk.Context()  # type: ignore[misc]


def test_kernel_resolvers(tmp_path: Path) -> None:
    resolvers = kernel_resolvers()
    assert set(resolvers) == {"blob", "blob_set", "item_revision"}
    ctx = _RunContext()
    one, two = (BlobRef(sha256=h, media_type="text/plain", size=3) for h in (H1, H2))

    blob = BlobSubject(blob=one)
    resolvers["blob"].materialize(ctx, blob, tmp_path)
    assert (tmp_path / blob_file_name(one)).read_bytes() == b"one"
    assert resolvers["blob"].read_file(ctx, blob, blob_file_name(one)) == b"one"

    members = BlobSetSubject(members=(two, one))
    (tmp_path / "set").mkdir()
    resolvers["blob_set"].materialize(ctx, members, tmp_path / "set")
    assert sorted(p.name for p in (tmp_path / "set").iterdir()) == sorted(
        blob_file_name(b) for b in (one, two)
    )
    with pytest.raises(SubjectMismatchError):
        resolvers["blob_set"].read_file(ctx, members, "not-a-member")

    revision = ItemRevisionSubject(item=ItemRef(id="N-3", hash=H1))
    (tmp_path / "item").mkdir()
    resolvers["item_revision"].materialize(ctx, revision, tmp_path / "item")
    assert (tmp_path / "item" / "N-3.md").read_text(encoding="utf-8") == "# N-3 — Note\n"
    with pytest.raises(SubjectMismatchError):
        resolvers["item_revision"].materialize(ctx, blob, tmp_path / "item")
