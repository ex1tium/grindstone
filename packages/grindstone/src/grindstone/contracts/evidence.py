"""Evidence contracts: how a check is specified (SPEC-08).

`CheckSpec` arrives first, with SPEC-06 part 1's collect outcome, because a
workspace provider adds checks to a task's plan at collect. SPEC-08 owns the
rest of this module: checks, evidence records, test outcomes and review
verdicts.
"""

from typing import Literal

from pydantic import Field, JsonValue

from grindstone.contracts.base import Contract


class CheckSpec(Contract):
    """One check in a task's plan: the method, who performs it, and what it proves."""

    schema_version: Literal[1] = 1
    method: str
    by: str
    """`station` for a mechanical method run on a check station, or the prover's need."""
    required: bool = True
    targets: tuple[str, ...] = ()
    """The selection of the task's inputs this check proves: kinds, field equalities or IDs."""
    params: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])
    """JSON handed to the performer."""
    acknowledge: tuple[str, ...] = ()
    """Keys the prover must pass explicitly, such as reviewed-tier paths."""
