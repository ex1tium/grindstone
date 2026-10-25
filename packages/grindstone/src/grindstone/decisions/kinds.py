"""What each decision kind accepts: its payload, its answer, and any rule on the answer.

A decision kind is a registry entry (SPEC-03); this module holds how the
kernel validates the kinds it knows. The five kernel kinds have their answer
models here, and the payloads SPEC-04 fixes. A module that raises a kernel
kind with a payload model of its own (`change` for `approval`, `delivery` for
`delivery`) or a rule on its answers (`change`'s `verdict_missing`) passes a
refined `DecisionKind` to `Decisions` at the composition root. A factory's
decision kind, declared by name only in SDK 0.1.0, takes any JSON object as
payload and answer.
"""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from pydantic import JsonValue, TypeAdapter

from grindstone.contracts.base import Contract
from grindstone.contracts.decisions import (
    ApprovalAnswer,
    DeliveryAnswer,
    EscalationAnswer,
    EscalationPayload,
    PermissionAnswer,
    PermissionPayload,
    QuestionAnswer,
    QuestionPayload,
)
from grindstone.decisions.errors import DecisionError

type Json = dict[str, JsonValue]
type AnswerCheck = Callable[[Json, Json], None]
"""A rule on an answer given the decision's payload; it raises `DecisionError` to refuse."""


@dataclass(frozen=True, slots=True)
class DecisionKind:
    """How the kernel validates one decision kind."""

    name: str
    answer: TypeAdapter[Any]
    payload: type[Contract] | None = None
    """The payload model; None accepts any JSON object."""
    check: AnswerCheck | None = None

    def refined(
        self, *, payload: type[Contract] | None = None, check: AnswerCheck | None = None
    ) -> DecisionKind:
        """The same kind with a payload model or an answer rule supplied by its raiser."""
        return replace(self, payload=payload or self.payload, check=check or self.check)


def _question_check(payload: Json, answer: Json) -> None:
    """A question's answer satisfies the schema the question carries."""
    schema = payload.get("answer_schema")
    schema = schema if isinstance(schema, dict) else {}
    try:
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        found = cast(
            Iterable[ValidationError], cast(Any, validator).iter_errors(answer.get("answer"))
        )
        errors = sorted(found, key=str)
    except SchemaError as exc:
        raise DecisionError("answer_invalid", "the question's answer schema is invalid") from exc
    if errors:
        raise DecisionError(
            "answer_invalid",
            "the answer does not satisfy the question's schema",
            errors=[e.message for e in errors],
        )


KERNEL_DECISION_KINDS: Mapping[str, DecisionKind] = {
    kind.name: kind
    for kind in (
        DecisionKind("approval", TypeAdapter(ApprovalAnswer)),
        DecisionKind(
            "question", TypeAdapter(QuestionAnswer), QuestionPayload, check=_question_check
        ),
        DecisionKind("permission", TypeAdapter(PermissionAnswer), PermissionPayload),
        DecisionKind("delivery", TypeAdapter(DeliveryAnswer)),
        DecisionKind("escalation", TypeAdapter(EscalationAnswer), EscalationPayload),
    )
}

FACTORY_ANSWER: TypeAdapter[Json] = TypeAdapter(dict[str, JsonValue])
