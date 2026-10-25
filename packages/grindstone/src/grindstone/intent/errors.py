"""Errors `intent` refuses with, carrying their envelope (SPEC-04)."""

from pydantic import JsonValue

from grindstone.contracts.errors import ErrorClass, ErrorEnvelope, error_class_of


class IntentError(Exception):
    """A refusal with a kernel error code and structured detail."""

    def __init__(self, code: str, message: str, **detail: JsonValue) -> None:
        super().__init__(message)
        error_class = error_class_of(code) or ErrorClass.INTERNAL
        self.code = code
        self.envelope = ErrorEnvelope(
            code=code,
            error_class=error_class,
            message=message,
            detail=dict(detail),
            retryable=error_class is ErrorClass.TRANSIENT,
        )
