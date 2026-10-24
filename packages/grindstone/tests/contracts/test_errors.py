"""SPEC-01, TKT-0102: the error envelope and its closed codes."""

import pytest
from pydantic import ValidationError

from grindstone.contracts import (
    KERNEL_ERROR_CODES,
    ErrorClass,
    ErrorEnvelope,
    error_class_of,
    register_error_codes,
)


def test_error_codes_are_closed() -> None:
    assert {c.value for c in ErrorClass} == {
        "validation",
        "rule",
        "authority",
        "limit",
        "transient",
        "internal",
    }
    assert all(KERNEL_ERROR_CODES[c] for c in ErrorClass)

    ok = ErrorEnvelope(
        code="report_invalid",
        error_class=ErrorClass.VALIDATION,
        message="Field `summary` is missing.",
        detail={"pointer": "/summary"},
        retryable=False,
    )
    assert ErrorEnvelope.model_validate_json(ok.model_dump_json()) == ok

    with pytest.raises(ValidationError, match="unknown error code"):
        ErrorEnvelope(
            code="no_such_code", error_class=ErrorClass.RULE, message="x", retryable=False
        )
    with pytest.raises(ValidationError, match="is validation, not transient"):
        ErrorEnvelope(
            code="report_invalid", error_class=ErrorClass.TRANSIENT, message="x", retryable=True
        )


def test_each_kernel_code_has_one_class() -> None:
    seen: dict[str, ErrorClass] = {}
    for error_class, codes in KERNEL_ERROR_CODES.items():
        for code in codes:
            assert code not in seen, f"{code} is both {seen[code]} and {error_class}"
            seen[code] = error_class
            assert error_class_of(code) is error_class


def test_registered_codes_are_admitted_once() -> None:
    register_error_codes(ErrorClass.RULE, ["fixture_rule_broken"])
    ErrorEnvelope(
        code="fixture_rule_broken", error_class=ErrorClass.RULE, message="x", retryable=False
    )
    with pytest.raises(ValueError, match="already declared as validation"):
        register_error_codes(ErrorClass.RULE, ["report_invalid"])
