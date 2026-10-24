"""Provenance: who or what caused a revision, and why (I-02)."""

from enum import StrEnum
from typing import Literal

from pydantic import Field

from grindstone.contracts.base import Contract
from grindstone.contracts.ids import ChangeSetId, DecisionId, ItemId, TaskId


class AuthorKind(StrEnum):
    """The kind of principal that authored a revision."""

    PERSON = "person"
    AGENT = "agent"
    POLICY = "policy"
    SYSTEM = "system"


class Provenance(Contract):
    """Carried by every revision: the author, what it came through, and the reason."""

    schema_version: Literal[1] = 1
    author_kind: AuthorKind
    author: str
    changeset: ChangeSetId | None = None
    task: TaskId | None = None
    finding: ItemId | None = None
    decision: DecisionId | None = None
    reason: str = Field(min_length=1)
