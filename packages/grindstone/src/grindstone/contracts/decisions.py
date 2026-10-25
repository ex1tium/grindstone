"""Decision records, answers and the kernel decision kinds' payloads and answers (SPEC-04).

A decision is a typed question only a person (in M1) may answer, raised with
a recommendation and its source, a scope, kernel-set flags and a context hash
over what the answerer is shown (ADR-28). Its kind is a registry entry
(SPEC-03); the kernel kinds' payload and answer models are here. SPEC-04's
ChangeSet module supplies the `approval` payload and SPEC-08 the `delivery`
one when they raise them.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, JsonValue

from grindstone.contracts.base import Contract
from grindstone.contracts.change import Verdict
from grindstone.contracts.ids import ChangeSetId, DecisionId, ProjectId, RunId, TaskId
from grindstone.contracts.refs import SemanticHash


class DecisionFlag(StrEnum):
    """How a decision may be answered; set only by the kernel code that raises it (Concepts)."""

    SCOPE_EXPANSION = "scope_expansion"
    PRINCIPLE = "principle"
    UNTRUSTED = "untrusted"
    ROUNDS_EXHAUSTED = "rounds_exhausted"
    REVERT_CONFLICT = "revert_conflict"
    CAP_REACHED = "cap_reached"
    IRREVERSIBLE = "irreversible"


class DecisionState(StrEnum):
    """The decision lifecycle; `expired` is reserved for SPEC-15 and has no writer in M1."""

    OPEN = "open"
    ANSWERED = "answered"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"


class RecommendationSource(StrEnum):
    FIXED = "fixed"
    AGENT = "agent"
    ADVISOR = "advisor"


class Channel(StrEnum):
    """Where an answer was given, from the authenticated session (SPEC-10)."""

    UI = "ui"
    API = "api"
    VSCODE = "vscode"
    PLUGIN = "plugin"


class Recommendation(Contract):
    """The recommended answer, why, and who recommends it."""

    answer: dict[str, JsonValue]
    reason: str = Field(min_length=1)
    source: RecommendationSource


class DecisionScope(Contract):
    """The records a decision is about."""

    task: TaskId | None = None
    changeset: ChangeSetId | None = None
    delivery: uuid.UUID | None = None
    run: RunId | None = None


class Decision(Contract):
    """One decision record (REQ-0416)."""

    schema_version: Literal[1] = 1
    id: DecisionId
    project: ProjectId
    kind: str
    flags: tuple[DecisionFlag, ...] = ()
    scope: DecisionScope
    context_hash: SemanticHash
    title: str = Field(min_length=1)
    payload: dict[str, JsonValue]
    recommendation: Recommendation
    state: DecisionState
    raised_by: str
    """The module that raised it, and the only one that may supersede it (REQ-0419)."""
    raised_at: datetime
    superseded_by: DecisionId | None = None


class Answer(Contract):
    """An accepted answer: what, by whom, through which channel and against which context.

    REQ-0417.
    """

    schema_version: Literal[1] = 1
    decision: DecisionId
    answer: dict[str, JsonValue]
    answered_by: str
    channel: Channel
    context_hash_seen: SemanticHash
    client_key: str = Field(min_length=1)
    at: datetime


# The kernel kinds' answers and the payloads this specification fixes.


class Approve(Contract):
    answer: Literal["approve"] = "approve"
    verdicts: tuple[Verdict, ...] = ()


class Reject(Contract):
    answer: Literal["reject"] = "reject"
    notes: str = Field(min_length=1)


ApprovalAnswer = Annotated[Approve | Reject, Field(discriminator="answer")]


class QuestionPayload(Contract):
    task: TaskId
    run: RunId
    question: str = Field(min_length=1)
    refs: tuple[str, ...] = ()
    answer_schema: dict[str, JsonValue]
    """The JSON Schema the answer's `answer` field must satisfy."""


class QuestionAnswer(Contract):
    answer: JsonValue


class PermissionPayload(Contract):
    task: TaskId
    action: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class PermissionAnswer(Contract):
    answer: Literal["allow_once", "allow_task", "deny"]


class DeliveryAnswer(Contract):
    answer: Literal["deliver", "hold", "cancel"]


class EscalationPayload(Contract):
    task: TaskId | None = None
    run: RunId | None = None
    cause: str = Field(min_length=1)
    evidence: tuple[str, ...] = ()


class EscalationAnswer(Contract):
    answer: Literal["retry", "cancel"]


# Events.


class DecisionRaised(Contract):
    schema_version: Literal[1] = 1
    type: Literal["decision.raised"] = "decision.raised"
    decision: DecisionId
    kind: str
    flags: tuple[DecisionFlag, ...] = ()


class DecisionAnswered(Contract):
    schema_version: Literal[1] = 1
    type: Literal["decision.answered"] = "decision.answered"
    decision: DecisionId
    kind: str


class DecisionSuperseded(Contract):
    schema_version: Literal[1] = 1
    type: Literal["decision.superseded"] = "decision.superseded"
    decision: DecisionId
    replacement: DecisionId
