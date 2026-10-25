"""FF-10: every external step has an idempotency key and a crash-and-resume test."""

from pathlib import Path

from scripts.ff.idempotency import external_steps, violations

from tests.fitness.helpers import REPO

KEYED = '''
from grindstone.store import IdempotencyKey, external_step


@external_step("demo.push", effect="pushes a branch")
def push(key: IdempotencyKey, branch: str) -> str:
    """Pushes once per key."""
    return remote.push(str(key), branch)
'''

UNANNOTATED = """
from grindstone import store


@store.external_step("demo.push", effect="pushes a branch")
def push(branch: str) -> str:
    return remote.push(branch)
"""

UNUSED_KEY = """
from grindstone.store import IdempotencyKey, external_step


@external_step("demo.push", effect="pushes a branch")
async def push(key: IdempotencyKey, branch: str) -> str:
    return await remote.push(branch)
"""

SCENARIO = """
from tests.crash.harness import crash_scenario

crash_scenario("demo.push", workflow=push_workflow, record="rec-1")
"""


def _tree(root: Path, step: str, *, scenario: str | None = SCENARIO) -> Path:
    demo = root / "packages/grindstone/src/grindstone/demo"
    demo.mkdir(parents=True)
    (demo / "steps.py").write_text(step, encoding="utf-8")
    if scenario is not None:
        scenarios = root / "tests/crash/scenarios"
        scenarios.mkdir(parents=True)
        (scenarios / "demo.py").write_text(scenario, encoding="utf-8")
    return root


def test_repository_passes_ff10() -> None:
    assert violations(REPO) == []


def test_ff10_requires_idempotency_key(tmp_path: Path) -> None:
    """AC-0204-2."""
    keyed = _tree(tmp_path / "keyed", KEYED)
    assert [s.name for s in external_steps(keyed)] == ["demo.push"]
    assert violations(keyed) == []

    for name, source in (("unannotated", UNANNOTATED), ("unused", UNUSED_KEY)):
        found = violations(_tree(tmp_path / name, source))
        assert found == [
            "packages/grindstone/src/grindstone/demo/steps.py:6: external step 'demo.push' "
            "has no idempotency key: its first parameter must be an `IdempotencyKey` that "
            "the step hands to its target"
        ], name


def test_ff10_requires_crash_test(tmp_path: Path) -> None:
    """AC-0213-2."""
    found = violations(_tree(tmp_path / "untested", KEYED, scenario=None))
    assert found == [
        "packages/grindstone/src/grindstone/demo/steps.py:6: external step 'demo.push' "
        'has no crash-and-resume test: declare `crash_scenario("demo.push", ...)` '
        "under tests/crash/scenarios/"
    ]

    other = SCENARIO.replace('"demo.push"', '"demo.other"')
    assert len(violations(_tree(tmp_path / "other", KEYED, scenario=other))) == 1
    named = SCENARIO.replace('crash_scenario("demo.push",', 'crash_scenario(step="demo.push",')
    assert violations(_tree(tmp_path / "keyword", KEYED, scenario=named)) == []
