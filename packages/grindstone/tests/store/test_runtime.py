"""DBOS in the lifespan, deterministic starts, the version guard and schedules.

REQ-0201, REQ-0205, REQ-0207 and REQ-0214, on real PostgreSQL and DBOS.
"""

import asyncio
import os
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from dbos import DBOS, WorkflowHandle
from fastapi.testclient import TestClient
from packages.grindstone.tests.store.runtime_child import (
    PARENT_ID,
    STRAND_VERSION,
    child,
    create_scratch,
    effects,
    running,
    tick,
)
from sqlalchemy import Engine, make_url, text

from grindstone.__main__ import main
from grindstone.app import create_app
from grindstone.store import (
    WORKFLOW_VERSION,
    DatabaseSettings,
    Runtime,
    Schedule,
    StoreError,
    StrandedWorkflow,
    start,
)

pytestmark = pytest.mark.integration

REPO = Path(__file__).resolve().parents[4]
CHILD_MODULE = "packages.grindstone.tests.store.runtime_child"
# Synchronous DBOS calls that refuse to run, or would block, on the event loop.
SYNC_CALLS = (
    "list_workflows",
    "apply_schedules",
    "create_schedule",
    "register_queue",
    "start_workflow",
    "send",
    "fork_workflow",
)


def _wait_for[T](probe: Callable[[], T | None], timeout: float = 30) -> T:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = probe()
        if found:
            return found
        time.sleep(0.1)
    raise AssertionError("timed out waiting")


def _settings(url: str, tmp_path: Path) -> DatabaseSettings:
    parsed = make_url(url)
    secret = tmp_path / "db-password"
    secret.write_text(parsed.password or "")
    return DatabaseSettings(
        host=parsed.host or "localhost",
        port=parsed.port or 5432,
        dbname=parsed.database or "",
        user=parsed.username or "",
        password_file=secret,
    )


def _child_process(
    *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", CHILD_MODULE, *args],
        cwd=REPO,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_lifespan_launches_dbos(
    database_url: str, engine: Engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-0201-1."""
    on_loop: list[str] = []

    def spy(name: str) -> Callable[..., Any]:
        original = getattr(DBOS, name)

        def call(*args: Any, **kwargs: Any) -> Any:
            try:
                asyncio.get_running_loop()
                on_loop.append(name)
            except RuntimeError:
                pass
            return original(*args, **kwargs)

        return call

    for name in SYNC_CALLS:
        monkeypatch.setattr(DBOS, name, staticmethod(spy(name)))
    schedule = Schedule("lifespan-tick", tick, "0 0 0 1 1 *")

    app = create_app(_settings(database_url, tmp_path), schedules=[schedule])
    with TestClient(app) as client:
        assert client.get("/readyz").status_code == 200
        runtime: Runtime = app.state.runtime
        assert runtime.version == WORKFLOW_VERSION
        assert runtime.dispatching
        create_scratch(engine)
        handle = start("lifespan-rec-1", child, "lifespan")
        assert handle.get_result() == "lifespan"
        assert handle.get_status().app_version == WORKFLOW_VERSION

    assert on_loop == []
    with engine.connect() as conn:
        tables = set(
            conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'dbos'")
            ).scalars()
        )
        versions = list(
            conn.execute(text("SELECT version_name FROM dbos.application_versions")).scalars()
        )
        schedules = list(
            conn.execute(text("SELECT schedule_name FROM dbos.workflow_schedules")).scalars()
        )
    assert {"workflow_status", "operation_outputs", "notifications"} <= tables
    assert versions == [WORKFLOW_VERSION]
    assert schedules == ["lifespan-tick"]


def test_workflow_ids_are_deterministic(database_url: str, engine: Engine, tmp_path: Path) -> None:
    """AC-0205-1."""
    create_scratch(engine)
    with running(database_url):
        first = start("once-rec-1", child, "once")
        again = start("once-rec-1", child, "once")
        assert first.get_result() == again.get_result() == "once"
        assert effects(engine, "child:once") == 1
        for missing in ("", "   "):
            with pytest.raises(ValueError, match="ID derived from its record"):
                start(missing, child, "nothing")

    marker = tmp_path / "killed"
    env = {
        **os.environ,
        "GRINDSTONE_TEST_KILL_AT": "after_child_start",
        "GRINDSTONE_TEST_KILL_MARKER": str(marker),
    }
    killed = _child_process("parent", database_url, env=env)
    assert killed.returncode != 0, killed.stderr
    assert marker.read_text() == "after_child_start"
    restarted = _child_process("parent", database_url, env=env)
    assert restarted.returncode == 0, restarted.stderr

    with running(database_url):
        children = DBOS.list_workflows(parent_workflow_id=PARENT_ID)
        assert [c.workflow_id for c in children] == [f"{PARENT_ID}.child"]
        assert DBOS.retrieve_workflow(PARENT_ID).get_status().status == "SUCCESS"
    assert effects(engine, "child:rec-1") == 1


def test_stranded_workflows_block_dispatch(
    database_url: str, engine: Engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-0207-1."""
    create_scratch(engine)
    parked_run = _child_process("park", database_url, "rec-7")
    assert parked_run.returncode == 0, parked_run.stderr
    assert effects(engine, "parked:rec-7") == 1

    with running(database_url, version="v2") as runtime:
        stranded = StrandedWorkflow(workflow_id="park-rec-7", name="test.parked", version="v1")
        assert runtime.stranded == (stranded,)
        assert not runtime.dispatching
        with pytest.raises(StoreError) as refused:
            start("new-rec-1", child, "new")
        envelope = refused.value.envelope()
        assert envelope.code == "workflow_version_mismatch"
        assert envelope.detail["stranded"] == [
            {"workflow_id": "park-rec-7", "name": "test.parked", "version": STRAND_VERSION}
        ]
        assert DBOS.get_workflow_status("new-rec-1") is None

        # A message sent while stranded wakes nothing: v2 does not run v1's workflow.
        DBOS.send("park-rec-7", "go", topic="go")
        time.sleep(2)
        assert DBOS.retrieve_workflow("park-rec-7").get_status().status == "PENDING"
        assert effects(engine, "received:rec-7:go") == 0

        settings = _settings(database_url, tmp_path)
        monkeypatch.setenv("GRINDSTONE_DB_HOST", settings.host)
        monkeypatch.setenv("GRINDSTONE_DB_PORT", str(settings.port))
        monkeypatch.setenv("GRINDSTONE_DB_NAME", settings.dbname)
        monkeypatch.setenv("GRINDSTONE_DB_USER", settings.user)
        monkeypatch.setenv("GRINDSTONE_DB_PASSWORD_FILE", str(settings.password_file))
        assert main(["workflows", "fork", "park-rec-7", "--version", "v2"]) == 0
        # Repeating the command finds the earlier fork and changes nothing.
        assert main(["workflows", "fork", "park-rec-7", "--version", "v2"]) == 0

        forked: WorkflowHandle[str] = DBOS.retrieve_workflow("park-rec-7@v2")
        assert forked.get_result() == "go"
        assert forked.get_status().app_version == "v2"
        assert DBOS.retrieve_workflow("park-rec-7").get_status().status == "CANCELLED"
        assert effects(engine, "parked:rec-7") == 1
        assert effects(engine, "received:rec-7:go") == 1

        # Nothing is stranded any more, so dispatch resumes.
        assert start("new-rec-2", child, "new").get_result() == "new"
        assert runtime.dispatching


@pytest.mark.parametrize("backfill", [False, True])
def test_schedule_backfill_is_explicit(database_url: str, backfill: bool) -> None:
    """AC-0214-1: missed periods are skipped unless the schedule asks for backfill."""
    name = f"tick-{backfill}".lower()
    every_second = "* * * * * *"
    schedule = (
        Schedule(name, tick, every_second, backfill=True)
        if backfill
        else Schedule(name, tick, every_second)
    )
    prefix = f"sched-{name}-"

    def fired() -> list[datetime]:
        runs = DBOS.list_workflows(schedule_name=name, load_input=False, load_output=False)
        return sorted(datetime.fromisoformat(r.workflow_id.removeprefix(prefix)) for r in runs)

    with running(database_url, schedules=[schedule]):
        _wait_for(fired)
    stopped = datetime.now(UTC)
    time.sleep(5)
    with running(database_url, schedules=[schedule]):
        restarted = datetime.now(UTC)
        _wait_for(lambda: [t for t in fired() if t > restarted])
        time.sleep(1)
        runs = fired()

    missed = [
        t for t in runs if (t - stopped).total_seconds() > 1 and (restarted - t).total_seconds() > 1
    ]
    if backfill:
        assert len(missed) >= 2, runs
    else:
        assert missed == [], runs
