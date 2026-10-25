"""Errors `change` refuses with: one envelope listing every problem, per item (SPEC-04)."""

from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import JsonValue

from grindstone.contracts.errors import ErrorClass, ErrorEnvelope, error_class_of


@dataclass(frozen=True, slots=True)
class Problem:
    """One rule a draft breaks: the item it is about, its error code and why."""

    item: str | None
    code: str
    message: str

    def as_json(self) -> JsonValue:
        return {"item": self.item, "code": self.code, "message": self.message}


class ChangeError(Exception):
    """A refused draft. The envelope's code is the first problem's; `detail.problems` lists all."""

    def __init__(self, problems: Sequence[Problem]) -> None:
        if not problems:
            raise ValueError("a refusal names at least one problem")
        first = problems[0]
        message = (
            first.message
            if len(problems) == 1
            else f"{first.message} (and {len(problems) - 1} more)"
        )
        super().__init__(message)
        error_class = error_class_of(first.code) or ErrorClass.INTERNAL
        self.code = first.code
        self.problems = tuple(problems)
        self.envelope = ErrorEnvelope(
            code=first.code,
            error_class=error_class,
            message=message,
            detail={"problems": [p.as_json() for p in problems]},
            retryable=error_class is ErrorClass.TRANSIENT,
        )

    @classmethod
    def single(cls, about: object, code: str, message: str) -> ChangeError:
        """A refusal with one problem, about an item or a ChangeSet."""
        return cls([Problem(str(about), code, message)])
