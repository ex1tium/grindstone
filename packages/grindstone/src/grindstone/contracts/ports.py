"""Contexts and port protocols: what kernel code hands a factory, and what it calls (DEC-0308).

They live in `contracts`, beside the models the ports exchange, so the kernel
modules that build contexts or call ports type their calls without importing
the SDK, which re-exports these same objects. Protocols are not models and
are never exported to the schema bundle (FF-02).

Factories never build a context: kernel code binds `project` and `factory`,
so the factory identity a secret check reads is one the kernel chose. Port
protocols arrive with the specifications that own them: `WorkspaceProvider`
and `SubjectResolver` (SPEC-06 part 1), `CheckMethod` and `DeliveryAdapter`
(SPEC-08).
"""

from pathlib import Path
from typing import BinaryIO, Protocol

from pydantic import Field, JsonValue

from grindstone.contracts.base import Contract
from grindstone.contracts.ids import ProjectId, RunId, TaskId
from grindstone.contracts.platform import TaskMode
from grindstone.contracts.refs import BlobHash, ItemRef, SubjectRef
from grindstone.contracts.stations import CollectOutcome, Materialization


class PinnedItem(Contract):
    """An item revision as a factory reads it: typed fields and its rendering.

    SPEC-04 owns revisions and rendering; this is the read model a context
    returns, so a factory never sees the store.
    """

    ref: ItemRef
    kind: str
    title: str
    semantic: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])
    rendered: str


class ItemReader(Protocol):
    def read(self, ref: ItemRef) -> PinnedItem:
        """The pinned revision `ref` names, typed and rendered."""
        ...


class BlobReader(Protocol):
    def open(self, sha256: BlobHash) -> BinaryIO:
        """A blob's bytes, opened for reading."""
        ...


class FactoryStorage(Protocol):
    def directory(self) -> Path:
        """This factory's disposable storage directory for this project (DEC-0306)."""
        ...


class SecretReader(Protocol):
    def read(self, name: str) -> str:
        """A secret this factory declares and this project grants; else `secret_not_granted`."""
        ...


class Context(Protocol):
    """What every port method receives; built only by kernel code."""

    @property
    def project(self) -> ProjectId: ...

    @property
    def factory(self) -> str: ...

    @property
    def items(self) -> ItemReader: ...

    @property
    def blobs(self) -> BlobReader: ...

    @property
    def storage(self) -> FactoryStorage: ...

    @property
    def secrets(self) -> SecretReader: ...


class RunContext(Context, Protocol):
    """A context for one task run, which workspace providers receive (SPEC-06 part 1)."""

    @property
    def run(self) -> RunId: ...

    @property
    def task(self) -> TaskId: ...

    @property
    def mode(self) -> TaskMode: ...

    @property
    def workspace_ref(self) -> str:
        """Where the provider keeps this run's working state, such as a worktree name."""
        ...

    @property
    def base(self) -> SubjectRef | None:
        """The subject the run starts from, once known."""
        ...


class WorkspaceProvider(Protocol):
    """Prepares a writing workspace and collects it into a subject (ADR-27, REQ-0624)."""

    def prepare(self, ctx: RunContext) -> Materialization:
        """Stage the workspace as an archive and say what it starts from."""
        ...

    def collect(self, ctx: RunContext) -> CollectOutcome:
        """Turn the finished workspace into a subject, or refuse it with paths and cause."""
        ...

    def discard(self, ctx: RunContext) -> None:
        """Release whatever the provider holds for the run."""
        ...


class SubjectResolver(Protocol):
    """Reads a subject kind: materializes it for a prover, or reads one file of it."""

    def materialize(self, ctx: Context, subject: SubjectRef, directory: Path) -> None:
        """Write the subject's contents into an empty `directory` (I-15: from the subject alone)."""
        ...

    def read_file(self, ctx: Context, subject: SubjectRef, path: str) -> bytes:
        """One file of the subject, by its path within a materialization."""
        ...
