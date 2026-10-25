"""The crash harness: kill the control plane at a named point, restart it, read the effects.

SPEC-02, REQ-0213. A crash scenario names a registered external step, the
workflow that runs it and the record that workflow is started for. The
harness starts the control plane (`tests.crash.control_plane`) as a
subprocess against a test database with `GRINDSTONE_KILL_AT` set to one of
the step's kill points, so the process is killed there; it then restarts it,
DBOS recovers the workflow, and the scenario's check reads what the fake
target recorded.

Every registered external step needs a scenario: FF-10 reads the
`crash_scenario("<step>", ...)` declarations in the tests, and the matrix
(`test_crash_matrix_runs_every_registered_step`) runs each at every kill point
its step registered. Scenarios live in modules under `tests/crash/scenarios/`,
one per owning module, which `load_scenarios` imports.
"""

import importlib
import os
import pkgutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from sqlalchemy import text

import grindstone
from grindstone.store import (
    KILL_AT_ENV,
    KILL_MARKER_ENV,
    WORKFLOW_VERSION,
    ExternalStepSpec,
    create_engine,
    registered_external_steps,
)
from tests.crash.target import TARGET_DIR_ENV, FakeTarget

REPO = Path(__file__).resolve().parents[2]
CONTROL_PLANE = "tests.crash.control_plane"
SCENARIO_PACKAGE = "tests.crash.scenarios"
TIMEOUT_SECONDS = 120


@dataclass(frozen=True, slots=True)
class CrashRun:
    """What one kill and restart left behind."""

    workflow_id: str
    key: str
    kill_at: str | None
    killed: bool
    status: str | None
    target: FakeTarget


def effect_once(run: CrashRun) -> None:
    """The default check: the workflow finished, and the target holds one effect, under its key."""
    assert run.status == "SUCCESS", run
    calls = run.target.calls()
    assert calls, "the step never called its target"
    assert {c.key for c in calls} == {run.key}, calls
    assert list(run.target.effects()) == [run.key]


@dataclass(frozen=True, slots=True)
class Scenario:
    """How to drive one external step: a workflow started for a record, and a check."""

    step: str
    workflow: Callable[..., object]
    record: str
    args: tuple[object, ...] = ()
    check: Callable[[CrashRun], None] = field(default=effect_once)

    @property
    def workflow_id(self) -> str:
        return f"crash-{self.record}"

    @property
    def key(self) -> str:
        return f"{self.record}:{self.step}"


class _Scenarios:
    by_step: dict[str, Scenario]

    def __init__(self) -> None:
        self.by_step = {}


_scenarios = _Scenarios()


def crash_scenario(
    step: str,
    *,
    workflow: Callable[..., object],
    record: str,
    args: tuple[object, ...] = (),
    check: Callable[[CrashRun], None] = effect_once,
) -> Scenario:
    """Declare the crash-and-resume scenario of the external step `step`."""
    if step in _scenarios.by_step:
        raise ValueError(f"external step {step!r} already has a crash scenario")
    scenario = Scenario(step=step, workflow=workflow, record=record, args=args, check=check)
    _scenarios.by_step[step] = scenario
    return scenario


def load_scenarios() -> Mapping[str, Scenario]:
    """Import every scenario module, and so the steps and workflows they drive."""
    package = importlib.import_module(SCENARIO_PACKAGE)
    for info in pkgutil.iter_modules(package.__path__, f"{SCENARIO_PACKAGE}."):
        importlib.import_module(info.name)
    return MappingProxyType(_scenarios.by_step)


def load_external_steps() -> Mapping[str, ExternalStepSpec]:
    """Every external step the kernel and the scenarios register.

    Importing every kernel module runs its registrations; factories register
    theirs through the SDK when SPEC-06 and later specifications add them.
    """
    for info in pkgutil.walk_packages(grindstone.__path__, "grindstone."):
        if not info.name.endswith("__main__"):
            importlib.import_module(info.name)
    load_scenarios()
    return registered_external_steps()


class CrashHarness:
    """Runs the control plane as a subprocess against one test database."""

    def __init__(self, database_url: str, directory: Path) -> None:
        self.database_url = database_url
        self.directory = directory
        self.marker = directory / "killed"
        self.target = FakeTarget(directory / "target")

    def run(
        self,
        step: str,
        *,
        kill_at: str | None = None,
        version: str = WORKFLOW_VERSION,
        wait: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Start the control plane, run `step`'s scenario (or wait for `wait`), and stop."""
        env = {**os.environ, TARGET_DIR_ENV: str(self.target.directory)}
        env.pop(KILL_AT_ENV, None)
        if kill_at is not None:
            env[KILL_AT_ENV] = kill_at
            env[KILL_MARKER_ENV] = str(self.marker)
        command = [sys.executable, "-m", CONTROL_PLANE, self.database_url, step, version]
        return subprocess.run(
            [*command, *([wait] if wait else [])],
            cwd=REPO,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )

    def kill(self, scenario: Scenario, kill_at: str, *, version: str = WORKFLOW_VERSION) -> None:
        """Run the scenario until the process is killed at `kill_at`."""
        killed = self.run(scenario.step, kill_at=kill_at, version=version)
        assert killed.returncode != 0, f"not killed at {kill_at}: {killed.stderr}"
        assert self.marker.read_text(encoding="utf-8") == kill_at, killed.stderr

    def crash_and_resume(self, scenario: Scenario, kill_at: str) -> CrashRun:
        """Kill the control plane at `kill_at`, restart it, and return what it recorded."""
        self.kill(scenario, kill_at)
        restarted = self.run(scenario.step, kill_at=kill_at)
        assert restarted.returncode == 0, restarted.stderr
        return self.result(scenario, scenario.workflow_id, kill_at)

    def result(self, scenario: Scenario, workflow_id: str, kill_at: str | None) -> CrashRun:
        """What the workflow `workflow_id` and the target recorded."""
        return CrashRun(
            workflow_id=workflow_id,
            key=scenario.key,
            kill_at=kill_at,
            killed=self.marker.exists(),
            status=self.status(workflow_id),
            target=self.target,
        )

    def status(self, workflow_id: str) -> str | None:
        """The workflow's DBOS status, read from DBOS's own table."""
        engine = create_engine(self.database_url)
        try:
            with engine.connect() as conn:
                query = text("SELECT status FROM dbos.workflow_status WHERE workflow_uuid = :id")
                return conn.execute(query, {"id": workflow_id}).scalar_one_or_none()
        finally:
            engine.dispose()
