"""External steps across crashes: one effect per key, after a restart or a fork.

REQ-0204 and REQ-0213, on real PostgreSQL and DBOS, with the control plane
killed in a subprocess.
"""

import pytest
from sqlalchemy import make_url

from grindstone.__main__ import main
from grindstone.store import WORKFLOW_VERSION, registered_external_steps
from grindstone.store.admin import fork_id
from tests.crash.harness import CrashHarness, load_external_steps, load_scenarios
from tests.crash.scenarios.store import SCENARIO, STEP

pytestmark = pytest.mark.integration

OLD_VERSION = "0"


def _matrix() -> list[tuple[str, str]]:
    steps = load_external_steps()
    return [(name, point) for name, spec in sorted(steps.items()) for point in spec.kill_points]


def test_external_step_effect_once(crash_harness: CrashHarness) -> None:
    """AC-0204-1."""
    run = crash_harness.crash_and_resume(SCENARIO, f"after:{STEP}")

    assert run.killed
    assert run.status == "SUCCESS"
    calls = run.target.calls()
    # The step ran twice, both times with the key its record gives, not its workflow ID.
    assert [c.key for c in calls] == ["rec-crash-1:test.crash.apply"] * 2
    assert run.target.effects() == {"rec-crash-1:test.crash.apply": "effect-1"}


def test_forked_step_keeps_its_key(
    crash_harness: CrashHarness,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """AC-0204-3."""
    crash_harness.kill(SCENARIO, f"after:{STEP}", version=OLD_VERSION)
    original = SCENARIO.workflow_id
    assert crash_harness.status(original) == "PENDING"

    url = make_url(crash_harness.database_url)
    secret = tmp_path_factory.mktemp("secret") / "db-password"
    secret.write_text(url.password or "", encoding="utf-8")
    monkeypatch.setenv("GRINDSTONE_DB_HOST", url.host or "localhost")
    monkeypatch.setenv("GRINDSTONE_DB_PORT", str(url.port or 5432))
    monkeypatch.setenv("GRINDSTONE_DB_NAME", url.database or "")
    monkeypatch.setenv("GRINDSTONE_DB_USER", url.username or "")
    monkeypatch.setenv("GRINDSTONE_DB_PASSWORD_FILE", str(secret))
    assert main(["workflows", "fork", original, "--version", WORKFLOW_VERSION]) == 0

    forked = fork_id(original, WORKFLOW_VERSION)
    resumed = crash_harness.run(STEP, wait=forked)
    assert resumed.returncode == 0, resumed.stderr

    run = crash_harness.result(SCENARIO, forked, f"after:{STEP}")
    assert run.status == "SUCCESS"
    assert crash_harness.status(original) == "CANCELLED"
    # A new workflow ID re-ran the step, and its key is still the record's.
    assert [c.key for c in run.target.calls()] == ["rec-crash-1:test.crash.apply"] * 2
    assert run.target.effects() == {"rec-crash-1:test.crash.apply": "effect-1"}


@pytest.mark.parametrize(("step", "kill_at"), _matrix())
def test_crash_matrix_runs_every_registered_step(
    crash_harness: CrashHarness, step: str, kill_at: str
) -> None:
    """AC-0213-1: every registered kill point of every registered external step."""
    scenarios = load_scenarios()
    assert step in scenarios, f"external step {step!r} has no crash scenario"
    scenario = scenarios[step]

    run = crash_harness.crash_and_resume(scenario, kill_at)

    assert run.killed
    scenario.check(run)


def test_matrix_covers_the_registry() -> None:
    """AC-0213-1: the matrix is the registry, and the store's step is in it at both points."""
    matrix = _matrix()
    assert {name for name, _ in matrix} == set(registered_external_steps())
    assert (STEP, f"before:{STEP}") in matrix
    assert (STEP, f"after:{STEP}") in matrix
