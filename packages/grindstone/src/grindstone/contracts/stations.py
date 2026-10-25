"""What workspace providers return: materializations and collect outcomes (SPEC-06 part 1).

A provider prepares a writing workspace as an archive in the staging area and,
when the maker is done, collects it into a subject. Collect also says what
the kernel must add before verifying: extra checks, which it adds and never
removes, permission requests for a person, and prover context every prover
of the subject is given. A refusal names the paths and the cause instead.
"""

from typing import Annotated, Literal

from pydantic import Field

from grindstone.contracts.base import Contract
from grindstone.contracts.evidence import CheckSpec
from grindstone.contracts.refs import BlobRef, SubjectRef


class Materialization(Contract):
    """A workspace's contents, staged as an archive for the host to extract."""

    schema_version: Literal[1] = 1
    archive: str
    """The archive's path in the staging area."""
    base: SubjectRef | None = None
    """The subject the workspace starts from, once known (for SDLC, the base commit)."""


class PermissionRequest(Contract):
    """Something the factory's policy says needs a person, such as a protected path."""

    action: str
    reason: str = Field(min_length=1)


class Collected(Contract):
    """A workspace collected into a subject."""

    schema_version: Literal[1] = 1
    outcome: Literal["collected"] = "collected"
    subject: SubjectRef
    extra_checks: tuple[CheckSpec, ...] = ()
    permission_requests: tuple[PermissionRequest, ...] = ()
    prover_context: tuple[BlobRef, ...] = ()
    """Blobs every prover of the subject is given, such as a diff against its base."""


class CollectRefused(Contract):
    """A workspace that cannot become a subject, with the paths and the cause."""

    schema_version: Literal[1] = 1
    outcome: Literal["refused"] = "refused"
    paths: tuple[str, ...] = ()
    cause: str = Field(min_length=1)


CollectOutcome = Annotated[Collected | CollectRefused, Field(discriminator="outcome")]
"""What `WorkspaceProvider.collect` returns (REQ-0624)."""
