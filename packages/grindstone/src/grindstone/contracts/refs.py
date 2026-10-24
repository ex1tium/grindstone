"""References between records: pinned item revisions, blobs and subjects.

Every content hash is written `sha256:<64 lowercase hex>`, so the algorithm
travels with the value (DEC-0104). A subject is the version of something a
check proves; factory subject kinds reduce to one of the four kinds here.
"""

from typing import Annotated, Any, Literal, cast

from pydantic import Field, StringConstraints, model_validator

from grindstone.contracts.base import Contract
from grindstone.contracts.ids import ItemId

HASH_PATTERN = r"^sha256:[0-9a-f]{64}$"

SemanticHash = Annotated[str, StringConstraints(pattern=HASH_PATTERN)]
"""The semantic hash of a contract's content (ADR-44)."""

BlobHash = Annotated[str, StringConstraints(pattern=HASH_PATTERN)]
"""The SHA-256 of a blob's bytes, in the same form as a semantic hash."""

GitObjectName = Annotated[str, StringConstraints(pattern=r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")]
"""A git object name: SHA-1 (40 hex) or SHA-256 (64 hex), lowercase."""


class ItemRef(Contract):
    """One item revision, pinned by its semantic hash."""

    schema_version: Literal[1] = 1
    id: ItemId
    hash: SemanticHash


class BlobRef(Contract):
    """Content in the blob store, addressed by the hash of its bytes."""

    schema_version: Literal[1] = 1
    sha256: BlobHash
    media_type: str
    size: int = Field(ge=0)


class GitCommitSubject(Contract):
    """A commit in a repository."""

    schema_version: Literal[1] = 1
    kind: Literal["git_commit"] = "git_commit"
    repo: str
    sha: GitObjectName


class BlobSubject(Contract):
    """A single blob."""

    schema_version: Literal[1] = 1
    kind: Literal["blob"] = "blob"
    blob: BlobRef


class BlobSetSubject(Contract):
    """A set of blobs, held sorted and unique by content hash."""

    schema_version: Literal[1] = 1
    kind: Literal["blob_set"] = "blob_set"
    members: tuple[BlobRef, ...]

    @model_validator(mode="before")
    @classmethod
    def _sort_members(cls, data: object) -> object:
        """Sort members by hash and refuse two members with the same content hash."""
        if not isinstance(data, dict):
            return data
        raw = cast(dict[str, Any], data)
        if "members" in raw:
            members = [BlobRef.model_validate(m) for m in raw["members"]]
            members.sort(key=lambda m: m.sha256)
            hashes = [m.sha256 for m in members]
            if len(set(hashes)) != len(hashes):
                raise ValueError("blob set members must have distinct content hashes")
            return {**raw, "members": tuple(members)}
        return raw


class ItemRevisionSubject(Contract):
    """An item revision, proven as an object in its own right."""

    schema_version: Literal[1] = 1
    kind: Literal["item_revision"] = "item_revision"
    item: ItemRef


SubjectRef = Annotated[
    GitCommitSubject | BlobSubject | BlobSetSubject | ItemRevisionSubject,
    Field(discriminator="kind"),
]
"""The version of whatever a check proves, discriminated on `kind`."""
