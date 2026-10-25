"""The store's own scenario: a test external step against the fake target.

The store registers no external step of its own; this one exercises the
helper, the kill points and the harness that every later step relies on
(AC-0204-1, AC-0204-3, AC-0213-1).
"""

from grindstone.store import IdempotencyKey, external_step, workflow
from tests.crash.harness import crash_scenario
from tests.crash.target import FakeTarget

STEP = "test.crash.apply"


@external_step(STEP, effect="records one effect in the fake target")
def apply_effect(key: IdempotencyKey, payload: str) -> str:
    return FakeTarget.from_env().apply(str(key), payload)


@workflow("test.crash.effect")
def effect_workflow(record: str) -> str:
    return apply_effect(f"payload:{record}")


SCENARIO = crash_scenario(STEP, workflow=effect_workflow, record="rec-crash-1")
