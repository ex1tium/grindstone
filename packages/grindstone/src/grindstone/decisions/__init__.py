"""Domain layer. Authority: decisions, kinds and flags, continuations, policy
rules, autonomy state and the tripwire (ADR-28, ADR-30).
"""

from grindstone.decisions.errors import DecisionError
from grindstone.decisions.kinds import KERNEL_DECISION_KINDS, AnswerCheck, DecisionKind
from grindstone.decisions.records import (
    CONSUMER,
    AnswerRequest,
    Continuation,
    DecisionRequest,
    Decisions,
    open_decisions,
    previous_answer,
    read,
    register_continuation,
    registered_continuations,
)

__all__ = [
    "CONSUMER",
    "KERNEL_DECISION_KINDS",
    "AnswerCheck",
    "AnswerRequest",
    "Continuation",
    "DecisionError",
    "DecisionKind",
    "DecisionRequest",
    "Decisions",
    "open_decisions",
    "previous_answer",
    "read",
    "register_continuation",
    "registered_continuations",
]
