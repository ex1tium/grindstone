"""The error envelope and the closed set of error codes (Components, "Error model").

Every service error is an `ErrorEnvelope`: a stable code, a message for
people, a structured detail for machines, and whether a retry can help. Codes
form a closed list per class. Kernel codes are declared here, each kernel
specification appending its own, so modules below `platform` can use them;
factory codes arrive through the platform registry (SPEC-03), which calls
`register_error_codes`. An unknown code is refused.
"""

from collections.abc import Iterable, Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Literal

from pydantic import Field, JsonValue, model_validator

from grindstone.contracts.base import Contract


class ErrorClass(StrEnum):
    """How an error is handled, and by whom."""

    VALIDATION = "validation"
    RULE = "rule"
    AUTHORITY = "authority"
    LIMIT = "limit"
    TRANSIENT = "transient"
    INTERNAL = "internal"


KERNEL_ERROR_CODES: Mapping[ErrorClass, frozenset[str]] = MappingProxyType(
    {
        ErrorClass.VALIDATION: frozenset(
            {
                "report_invalid",
                "reference_unresolved",
                "manifest_invalid",
                "hash_input_invalid",  # SPEC-01
            }
        ),
        ErrorClass.RULE: frozenset(
            {"transition_illegal", "coverage_missing", "principle_conflict"}
        ),
        ErrorClass.AUTHORITY: frozenset(
            {"permission_required", "decision_superseded", "context_changed"}
        ),
        ErrorClass.LIMIT: frozenset(
            {
                "depth_exceeded",
                "fanout_exceeded",
                "storage_limit",
                "cap_reached",
                "consult_ceiling",
            }
        ),
        ErrorClass.TRANSIENT: frozenset(
            {
                "provider_unavailable",
                "station_unavailable",
                "remote_rejected",
                "database_unavailable",  # SPEC-02
            }
        ),
        ErrorClass.INTERNAL: frozenset(
            {
                "invariant_violated",
                "workflow_version_mismatch",  # SPEC-02
                "migration_failed",  # SPEC-02
            }
        ),
    }
)
"""Codes the kernel declares, per class. Later kernel specifications append here."""

_registered: dict[ErrorClass, set[str]] = {c: set() for c in ErrorClass}


def register_error_codes(error_class: ErrorClass, codes: Iterable[str]) -> None:
    """Admit further codes for a class; the platform registry calls this for factory codes.

    A code belongs to one class only, so a code already known under another
    class is refused.
    """
    for code in codes:
        owner = error_class_of(code)
        if owner is not None and owner is not error_class:
            raise ValueError(f"error code {code!r} is already declared as {owner.value}")
        _registered[error_class].add(code)


def error_class_of(code: str) -> ErrorClass | None:
    """The class a code is declared under, or None if it is unknown."""
    for error_class in ErrorClass:
        if code in KERNEL_ERROR_CODES[error_class] or code in _registered[error_class]:
            return error_class
    return None


class ErrorEnvelope(Contract):
    """One service error, in the shape every interface returns."""

    schema_version: Literal[1] = 1
    code: str
    error_class: ErrorClass
    message: str = Field(min_length=1)
    detail: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])
    retryable: bool

    @model_validator(mode="after")
    def _code_is_declared(self) -> ErrorEnvelope:
        owner = error_class_of(self.code)
        if owner is None:
            raise ValueError(f"unknown error code {self.code!r}")
        if owner is not self.error_class:
            raise ValueError(
                f"error code {self.code!r} is {owner.value}, not {self.error_class.value}"
            )
        return self
