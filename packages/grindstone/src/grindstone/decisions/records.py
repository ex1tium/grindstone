"""Decision records: raise, answer, supersede, read, and continuations (SPEC-04, ADR-28).

- `Decisions.raise_decision` validates the payload against the kind, refuses
  a missing recommendation and flags smuggled in the payload, computes the
  context hash over what the answerer is shown, inserts the decision and its
  continuation, and emits `decision.raised` (REQ-0416).
- `Decisions.answer` runs in the caller's unit of work: it locks the row,
  returns the original answer to a repeat with the same client key, refuses a
  superseded, closed or changed decision and an answer the kind refuses, then
  inserts the answer, moves the decision to `answered` and emits
  `decision.answered` (REQ-0417).
- The `decisions` consumer of `decision.answered` (SPEC-03's dispatcher)
  starts `decision-<id>`, which runs the registered continuation with the
  answer; the answer and its event commit together, so a crash after the
  answer still starts it, and the IDs make it run once (REQ-0418, DEC-0403).
- Only the raising module supersedes a decision, naming its replacement;
  both stay readable (REQ-0419).

Continuations are registered by name at the composition root, so this module
imports no higher one (Components, "Module map").
"""

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from pydantic import JsonValue, ValidationError

from grindstone.contracts.base import Contract
from grindstone.contracts.decisions import (
    Answer,
    Channel,
    Decision,
    DecisionAnswered,
    DecisionFlag,
    DecisionRaised,
    DecisionScope,
    DecisionState,
    DecisionSuperseded,
    Recommendation,
)
from grindstone.contracts.events import EventEnvelope
from grindstone.contracts.hashing import semantic_hash
from grindstone.contracts.ids import DecisionId, ProjectId, new_record_id
from grindstone.decisions.errors import DecisionError
from grindstone.decisions.kinds import FACTORY_ANSWER, KERNEL_DECISION_KINDS, DecisionKind, Json
from grindstone.platform import Category, Registries
from grindstone.platform.events import Consumer, emit
from grindstone.store import Uow, start, transaction, workflow

type ContinuationWorkflow = Callable[[str, str, str], Any]
"""A registered workflow taking the decision ID, the answer and the continuation payload as JSON."""


class _Continuations:
    workflows: dict[str, ContinuationWorkflow]

    def __init__(self) -> None:
        self.workflows = {}


_continuations = _Continuations()


def register_continuation(name: str, workflow: ContinuationWorkflow) -> None:
    """Register the workflow an answered decision naming `name` continues with."""
    if name in _continuations.workflows:
        raise ValueError(f"continuation {name!r} is already registered")
    _continuations.workflows[name] = workflow


def registered_continuations() -> Mapping[str, ContinuationWorkflow]:
    return MappingProxyType(_continuations.workflows)


@dataclass(frozen=True, slots=True)
class Continuation:
    """What runs when a decision is answered: a registered name and its payload."""

    name: str
    payload: Json = field(default_factory=dict[str, JsonValue])


@dataclass(frozen=True, slots=True)
class DecisionRequest:
    """A decision to raise. `flags` come from the raising kernel code, never from the payload."""

    project: ProjectId
    kind: str
    scope: DecisionScope
    title: str
    payload: Contract | Json
    recommendation: Recommendation | None
    raised_by: str
    flags: tuple[DecisionFlag, ...] = ()
    continuation: Continuation | None = None


@dataclass(frozen=True, slots=True)
class AnswerRequest:
    """An answer as the surface received it, with the context hash the answerer saw."""

    decision: DecisionId
    answer: Json
    answered_by: str
    channel: Channel
    context_hash_seen: str
    client_key: str


class _DecisionContext(Contract):
    """What the answerer is shown, hashed into the decision's context hash."""

    kind: str
    scope: DecisionScope
    flags: tuple[DecisionFlag, ...]
    payload: dict[str, JsonValue]


# The decision lifecycle: (from, to) → its one writer (REQ-0420).
_TRANSITIONS: Mapping[tuple[DecisionState, DecisionState], str] = {
    (DecisionState.OPEN, DecisionState.ANSWERED): "answer",
    (DecisionState.OPEN, DecisionState.SUPERSEDED): "owner",
}

_SELECT = (
    "SELECT id, project, kind, flags, scope, context_hash, title, payload, recommendation,"
    " state, raised_by, raised_at, superseded_by FROM decisions.decisions"
)


class Decisions:
    """The decision service, given the registries the decision kinds are registered in."""

    def __init__(self, registries: Registries, kinds: Iterable[DecisionKind] = ()) -> None:
        self._registries = registries
        self._kinds = dict(KERNEL_DECISION_KINDS)
        for kind in kinds:
            self._kinds[kind.name] = kind

    def kind(self, name: str) -> DecisionKind:
        """How `name` is validated; a kind not registered is refused."""
        if self._registries.get(Category.DECISION_KIND, name) is None:
            raise ValueError(f"decision kind {name!r} is not registered")
        return self._kinds.get(name) or DecisionKind(name, FACTORY_ANSWER)

    def raise_decision(self, uow: Uow, request: DecisionRequest) -> Decision:
        """Record and announce a decision (REQ-0416)."""
        kind = self.kind(request.kind)
        if request.recommendation is None:
            raise DecisionError(
                "recommendation_missing", "a decision is raised with a recommendation"
            )
        payload = _payload(kind, request.payload)
        _validate_answer(kind, request.recommendation.answer, "recommended answer")
        if request.continuation and request.continuation.name not in _continuations.workflows:
            raise ValueError(f"continuation {request.continuation.name!r} is not registered")
        flags = tuple(sorted(set(request.flags)))
        context = _DecisionContext(
            kind=kind.name, scope=request.scope, flags=flags, payload=payload
        )
        decision_id = DecisionId(new_record_id())
        uow.execute(
            "INSERT INTO decisions.decisions (id, project, kind, flags, scope, context_hash,"
            " title, payload, recommendation, raised_by) VALUES (:id, :project, :kind,"
            " CAST(:flags AS jsonb), CAST(:scope AS jsonb), :context_hash, :title,"
            " CAST(:payload AS jsonb), CAST(:recommendation AS jsonb), :raised_by)",
            {
                "id": decision_id,
                "project": request.project,
                "kind": kind.name,
                "flags": json.dumps([str(f) for f in flags]),
                "scope": request.scope.model_dump_json(),
                "context_hash": semantic_hash(context),
                "title": request.title,
                "payload": json.dumps(payload),
                "recommendation": request.recommendation.model_dump_json(),
                "raised_by": request.raised_by,
            },
        )
        if request.continuation is not None:
            uow.execute(
                "INSERT INTO decisions.continuations (decision, name, payload)"
                " VALUES (:decision, :name, CAST(:payload AS jsonb))",
                {
                    "decision": decision_id,
                    "name": request.continuation.name,
                    "payload": json.dumps(request.continuation.payload),
                },
            )
        emit(
            uow,
            DecisionRaised(decision=decision_id, kind=kind.name, flags=flags),
            request.project,
        )
        return read(uow, decision_id)

    def answer(self, uow: Uow, request: AnswerRequest) -> Answer:
        """Accept an answer, or refuse it with the reason (REQ-0417)."""
        decision = _locked(uow, request.decision)
        given = previous_answer(uow, decision.id)
        if given is not None:
            if given.client_key == request.client_key:
                return given
            raise DecisionError("decision_closed", f"decision {decision.id} is already answered")
        if decision.state is DecisionState.SUPERSEDED:
            raise DecisionError(
                "decision_superseded",
                f"decision {decision.id} was superseded",
                replacement=str(decision.superseded_by),
            )
        if decision.state is not DecisionState.OPEN:
            raise DecisionError("decision_closed", f"decision {decision.id} is {decision.state}")
        if request.context_hash_seen != decision.context_hash:
            raise DecisionError(
                "context_changed",
                f"decision {decision.id} changed since it was shown",
                context_hash=decision.context_hash,
            )
        kind = self.kind(decision.kind)
        answer = _validate_answer(kind, request.answer, "answer")
        if kind.check is not None:
            kind.check(decision.payload, answer)
        uow.execute(
            "INSERT INTO decisions.answers"
            " (decision, answer, answered_by, channel, context_hash_seen, client_key)"
            " VALUES (:decision, CAST(:answer AS jsonb), :answered_by, :channel,"
            " :context_hash_seen, :client_key)",
            {
                "decision": decision.id,
                "answer": json.dumps(answer),
                "answered_by": request.answered_by,
                "channel": str(request.channel),
                "context_hash_seen": request.context_hash_seen,
                "client_key": request.client_key,
            },
        )
        transition_decision(uow, decision, DecisionState.ANSWERED, "answer")
        emit(uow, DecisionAnswered(decision=decision.id, kind=decision.kind), decision.project)
        accepted = previous_answer(uow, decision.id)
        if accepted is None:  # pragma: no cover - inserted just above
            raise RuntimeError(f"answer to {decision.id} not recorded")
        return accepted

    def supersede(
        self, uow: Uow, decision: DecisionId, replacement: DecisionId, by: str
    ) -> Decision:
        """Supersede an open decision by its replacement; only its raiser may (REQ-0419)."""
        current = _locked(uow, decision)
        if by != current.raised_by:
            raise PermissionError(
                f"decision {decision} was raised by {current.raised_by}, not {by}"
            )
        other = read(uow, replacement)
        if other.id == current.id or other.project != current.project:
            raise ValueError(f"{replacement} cannot replace {decision}")
        if current.state is not DecisionState.OPEN:
            raise DecisionError("decision_closed", f"decision {decision} is {current.state}")
        transition_decision(uow, current, DecisionState.SUPERSEDED, "owner", replacement)
        emit(uow, DecisionSuperseded(decision=decision, replacement=replacement), current.project)
        return read(uow, decision)


def transition_decision(
    uow: Uow,
    decision: Decision,
    to: DecisionState,
    writer: str,
    superseded_by: DecisionId | None = None,
) -> None:
    """The one writer of a decision's `state` and `superseded_by` (REQ-0420)."""
    if _TRANSITIONS.get((decision.state, to)) != writer:
        raise DecisionError(
            "transition_illegal",
            f"decision {decision.id}: {decision.state} → {to} by {writer} is not allowed",
        )
    uow.execute(
        "UPDATE decisions.decisions SET state = :to, superseded_by = :superseded_by WHERE id = :id",
        {"id": decision.id, "to": str(to), "superseded_by": superseded_by},
    )


def read(uow: Uow, decision: DecisionId) -> Decision:
    """A decision, in any state."""
    row = uow.fetch_one(_SELECT + " WHERE id = :id", {"id": decision})
    if row is None:
        raise KeyError(f"no decision {decision}")
    return Decision.model_validate(dict(row))


def open_decisions(uow: Uow, project: ProjectId) -> list[Decision]:
    """A project's open decisions, oldest first."""
    rows = uow.fetch_all(
        _SELECT + " WHERE project = :project AND state = 'open' ORDER BY raised_at, id",
        {"project": project},
    )
    return [Decision.model_validate(dict(row)) for row in rows]


def previous_answer(uow: Uow, decision: DecisionId) -> Answer | None:
    """The accepted answer to a decision, if any."""
    row = uow.fetch_one(
        "SELECT decision, answer, answered_by, channel, context_hash_seen, client_key, at"
        " FROM decisions.answers WHERE decision = :decision",
        {"decision": decision},
    )
    return None if row is None else Answer.model_validate(dict(row))


def _locked(uow: Uow, decision: DecisionId) -> Decision:
    row = uow.fetch_one(
        _SELECT + " WHERE id = :id FOR UPDATE",
        {"id": decision},
    )
    if row is None:
        raise KeyError(f"no decision {decision}")
    return Decision.model_validate(dict(row))


def _payload(kind: DecisionKind, payload: Contract | Json) -> Json:
    raw: Json = payload.model_dump(mode="json") if isinstance(payload, Contract) else payload
    if "flags" in raw:
        raise ValueError("flags are set by the kernel, never in a decision's payload")
    if kind.payload is None:
        return raw
    return kind.payload.model_validate(raw).model_dump(mode="json")


def _validate_answer(kind: DecisionKind, answer: Json, what: str) -> Json:
    try:
        validated = kind.answer.validate_python(answer)
    except ValidationError as exc:
        raise DecisionError(
            "answer_invalid",
            f"the {what} is not a valid {kind.name} answer",
            errors=[str(e["msg"]) for e in exc.errors()],
        ) from None
    dumped: Json = kind.answer.dump_python(validated, mode="json")
    return dumped


# The `decision.answered` consumer, registered at the composition root.


@transaction
def _continuation_of(uow: Uow, decision: str) -> tuple[str, str, str] | None:
    row = uow.fetch_one(
        "SELECT c.name, c.payload, a.answer FROM decisions.continuations c"
        " JOIN decisions.answers a ON a.decision = c.decision WHERE c.decision = :decision",
        {"decision": decision},
    )
    if row is None:
        return None
    return str(row["name"]), json.dumps(row["payload"]), json.dumps(row["answer"])


@workflow("decisions.continue")
def continue_decision(event_id: str, envelope: str) -> str | None:
    """Start the answered decision's continuation as `decision-<id>`, once (REQ-0418)."""
    del event_id
    decision = str(EventEnvelope.model_validate_json(envelope).payload["decision"])
    found = _continuation_of(decision)
    if found is None:
        return None
    name, payload, answer = found
    start(f"decision-{decision}", _continuations.workflows[name], decision, answer, payload)
    return name


CONSUMER = Consumer("decisions", frozenset({"decision.answered"}), continue_decision)
