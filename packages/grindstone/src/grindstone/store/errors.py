"""The store's typed failures.

Each carries one of the kernel error codes SPEC-02 declares in
`grindstone.contracts.errors`, and maps onto SPEC-01's `ErrorEnvelope`.
"""

from typing import Literal

from pydantic import JsonValue

from grindstone.contracts import ErrorClass, ErrorEnvelope, error_class_of

type StoreErrorCode = Literal[
    "database_unavailable", "migration_failed", "workflow_version_mismatch"
]


class StoreError(Exception):
    """A store operation failed for a reason the caller may need to act on.

    `database_unavailable` is transient (retry later); `migration_failed` is
    internal and stops start-up; `workflow_version_mismatch` is internal and
    refuses new dispatch while workflows of another version are stranded, with
    the list in `detail`. Messages name the failing object and the exception
    class only, never connection details.
    """

    def __init__(
        self, code: StoreErrorCode, message: str, *, detail: dict[str, JsonValue] | None = None
    ) -> None:
        super().__init__(f"{code}: {message}")
        self.code: StoreErrorCode = code
        self.message = message
        self.detail: dict[str, JsonValue] = detail or {}

    def envelope(self) -> ErrorEnvelope:
        """The error as every interface returns it."""
        error_class = error_class_of(self.code)
        if error_class is None:  # pragma: no cover - every store code is declared
            raise AssertionError(f"undeclared store error code {self.code!r}")
        return ErrorEnvelope(
            code=self.code,
            error_class=error_class,
            message=self.message,
            detail=self.detail,
            retryable=error_class is ErrorClass.TRANSIENT,
        )
