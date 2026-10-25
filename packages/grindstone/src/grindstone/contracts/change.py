"""ChangeSet contracts: drafts, walk results, verdicts, the approval payload and events (SPEC-04).

A ChangeDraft is a proposal to change intent: its source, its trust, the
revisions it proposes with the base hash each was drafted against, and the
provenance every revision will carry (REQ-0410). A ChangeSet walks it, raises
one `approval` decision, and applies it in one transaction when approved
(ADR-10). Each walk round records the bases it was walked against; the latest
round's are the ChangeSet's effective bases (DEC-0407).
"""

import uuid
from enum import StrEnum
from typing import Literal

from pydantic import Field, JsonValue

from grindstone.contracts.base import Contract
from grindstone.contracts.ids import ChangeSetId, DecisionId, ItemId, ProjectId, RevisionId
from grindstone.contracts.provenance import Provenance
from grindstone.contracts.refs import SemanticHash


class Verdict(Contract):
    """A reviewer's verdict on an item the walk reached; M1 accepts only `unaffected` (DEC-0402).

    An empty reason is a valid verdict here; applying the approval refuses it
    with `verdict_missing` (REQ-0413).
    """

    item: ItemId
    verdict: Literal["unaffected"] = "unaffected"
    reason: str


class DraftSource(StrEnum):
    """Where a draft came from."""

    OPERATOR = "operator"
    TASK_OUTPUT = "task_output"
    DELEGATION_RESULT = "delegation_result"
    INTAKE = "intake"
    REVERT = "revert"


class Trust(StrEnum):
    """Whether a draft's content may be treated as instructions (I-07)."""

    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


class ProposedRevision(Contract):
    """One revision a draft proposes, with the hash of the revision it was drafted against."""

    item: ItemId
    kind: str = Field(min_length=1)
    base: SemanticHash | None
    """The current hash when drafted; None for a new item."""
    title: str = Field(min_length=1)
    fields: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])


class ChangeDraft(Contract):
    """A recorded draft. Insert-only; a repeated client key in its project returns it."""

    schema_version: Literal[1] = 1
    id: uuid.UUID
    project: ProjectId
    source: DraftSource
    trust: Trust
    revisions: tuple[ProposedRevision, ...] = Field(min_length=1)
    provenance: Provenance
    client_key: str | None = None


class ItemBase(Contract):
    """The base one proposed revision is walked against in a round."""

    item: ItemId
    base: SemanticHash | None


class Reached(Contract):
    """An item outside the ChangeSet with an edge to a changed item."""

    item: ItemId
    via_edge: str
    to: ItemId


class WalkResult(Contract):
    """One walk round: its bases, the changed items, and who they reach.

    `reached` holds the sources of `review` edges, which need a verdict;
    `informed` the sources of `notify` and `render` edges, listed for
    information only (ADR-09).
    """

    schema_version: Literal[1] = 1
    round: int = Field(ge=1)
    bases: tuple[ItemBase, ...]
    changed: tuple[ItemId, ...]
    reached: tuple[Reached, ...]
    informed: tuple[Reached, ...] = ()


class ChangeSetState(StrEnum):
    """The ChangeSet lifecycle; `transition_changeset` is its one writer (REQ-0420)."""

    DRAFTED = "drafted"
    WALKED = "walked"
    AWAITING_APPROVAL = "awaiting_approval"
    APPLIED = "applied"
    REJECTED = "rejected"


class ChangeSet(Contract):
    schema_version: Literal[1] = 1
    id: ChangeSetId
    project: ProjectId
    draft: uuid.UUID
    state: ChangeSetState
    decision: DecisionId | None = None
    """The open or last approval decision."""


class RevisionDiff(Contract):
    """What applying one proposed revision would change, against its effective base."""

    item: ItemId
    kind: str
    base: SemanticHash | None
    proposed: SemanticHash
    before: dict[str, JsonValue] | None
    """The base revision's title and semantic fields; None for a new item."""
    after: dict[str, JsonValue]
    changed_fields: tuple[str, ...]


class ApprovalPayload(Contract):
    """The `approval` decision's payload: everything its context hash covers (REQ-0412)."""

    schema_version: Literal[1] = 1
    changeset: ChangeSetId
    round: int = Field(ge=1)
    trust: Trust
    revisions: tuple[RevisionDiff, ...]
    reached: tuple[Reached, ...]
    informed: tuple[Reached, ...] = ()


# Events.


class ChangeSetDrafted(Contract):
    schema_version: Literal[1] = 1
    type: Literal["changeset.drafted"] = "changeset.drafted"
    changeset: ChangeSetId
    draft: uuid.UUID
    source: DraftSource
    trust: Trust


class ChangeSetWalked(Contract):
    schema_version: Literal[1] = 1
    type: Literal["changeset.walked"] = "changeset.walked"
    changeset: ChangeSetId
    round: int = Field(ge=1)
    reached: tuple[ItemId, ...] = ()


class ChangeSetApplied(Contract):
    schema_version: Literal[1] = 1
    type: Literal["changeset.applied"] = "changeset.applied"
    changeset: ChangeSetId
    decision: DecisionId
    revisions: tuple[RevisionId, ...]


class ChangeSetRejected(Contract):
    schema_version: Literal[1] = 1
    type: Literal["changeset.rejected"] = "changeset.rejected"
    changeset: ChangeSetId
    decision: DecisionId
