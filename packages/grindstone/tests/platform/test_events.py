"""SPEC-03, TKT-0304: the event outbox, the dispatcher and order-independent consumers."""

import os
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from dbos import DBOS
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from packages.grindstone.tests.store.runtime_child import running
from sqlalchemy import Engine, make_url, text
from sqlalchemy.exc import DBAPIError

from grindstone.contracts.events import (
    INSTANCE_STREAM,
    EventEnvelope,
    FactoryLoaded,
    FactoryRefused,
    ProjectConfigured,
)
from grindstone.contracts.health import HealthStatus, ServiceHealth
from grindstone.platform.events import (
    Consumer,
    Dispatcher,
    DispatcherThread,
    decode,
    emit,
    events_after,
)
from grindstone.store import (
    KILL_AT_ENV,
    KILL_MARKER_ENV,
    Database,
    Uow,
    transaction,
    unit_of_work,
    workflow,
)

REPO = Path(__file__).resolve().parents[4]
CHILD_MODULE = "packages.grindstone.tests.platform.events_child"
DIGEST = "sha256:" + "0" * 64


def _loaded(name: str = "notes") -> FactoryLoaded:
    return FactoryLoaded(factory=name, version="0.1.0", manifest_hash=DIGEST)


class _RollbackError(Exception):
    pass


@settings(
    max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    plans=st.lists(st.lists(st.booleans(), min_size=1, max_size=6), min_size=2, max_size=3),
)
def test_event_sequence_gapless(store: Database, plans: list[list[bool]]) -> None:
    """Concurrent units of work, some rolled back, leave a stream numbered 1..n."""
    project = uuid.uuid4()
    committed: list[uuid.UUID] = []
    rolled_back: list[uuid.UUID] = []
    lock = threading.Lock()

    def unit(commit: bool) -> None:
        def work(uow: Uow) -> uuid.UUID:
            envelope = emit(uow, ProjectConfigured(version=1, hash=DIGEST), project)
            if not commit:
                with lock:
                    rolled_back.append(envelope.event_id)
                raise _RollbackError
            return envelope.event_id

        try:
            event_id = unit_of_work(work)
        except _RollbackError:
            return
        with lock:
            committed.append(event_id)

    def worker(plan: list[bool]) -> None:
        for commit in plan:
            unit(commit)

    with ThreadPoolExecutor(len(plans)) as pool:
        for future in [pool.submit(worker, plan) for plan in plans]:
            future.result()

    stream = unit_of_work(lambda uow: events_after(uow, project, 0))
    assert [e.seq for e in stream] == list(range(1, len(committed) + 1))
    assert {e.event_id for e in stream} == set(committed)
    assert not {e.event_id for e in stream} & set(rolled_back)


def test_emit_round_trips_and_refuses_other_models(store: Database) -> None:
    project = uuid.uuid4()
    instance = unit_of_work(lambda uow: emit(uow, _loaded()))
    configured = unit_of_work(
        lambda uow: emit(uow, ProjectConfigured(version=3, hash=DIGEST), project)
    )
    assert (instance.project, instance.seq) == (INSTANCE_STREAM, 1)
    assert (configured.project, configured.seq) == (project, 1)
    assert configured.event_id.version == 7
    assert decode(instance) == _loaded()
    assert decode(configured) == ProjectConfigured(version=3, hash=DIGEST)
    assert configured.payload == {"version": 3, "hash": DIGEST}
    assert EventEnvelope.model_validate_json(configured.model_dump_json()) == configured

    with pytest.raises(TypeError, match="not a registered event model"):
        emit(
            cast(Uow, None),
            ServiceHealth(service="grindstone", version="1", status=HealthStatus.OK),
        )
    with pytest.raises(DBAPIError, match="insert-only"):
        unit_of_work(lambda uow: uow.execute("UPDATE platform.events SET type = 'x'"))


def test_consumer_registration_is_checked() -> None:
    dispatcher = Dispatcher()
    dispatcher.consume("audit", {"factory.loaded"}, _probe)
    with pytest.raises(ValueError, match="already registered"):
        dispatcher.consume("audit", {"factory.loaded"}, _probe)
    with pytest.raises(ValueError, match="unknown event types"):
        dispatcher.consume("other", {"task.done"}, _probe)
    with pytest.raises(ValueError, match="no '-'"):
        dispatcher.consume("a-b", {"factory.loaded"}, _probe)
    assert [c.name for c in dispatcher.consumers] == ["audit"]


def _child(database_url: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", CHILD_MODULE, database_url],
        cwd=REPO,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_event_dispatch_once(database_url: str, engine: Engine, tmp_path: Path) -> None:
    """Killed between the start and the cursor, the dispatcher delivers once after restart."""
    marker = tmp_path / "killed"
    env = {**os.environ, KILL_AT_ENV: "dispatch.after_start", KILL_MARKER_ENV: str(marker)}

    first = _child(database_url, env)
    assert first.returncode != 0, first.stderr
    assert marker.exists()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM platform.event_cursors")).scalar_one() == 0

    second = _child(database_url, env)
    assert second.returncode == 0, second.stderr
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM scratch.deliveries")).scalar_one() == 1
        cursor = text("SELECT seq FROM platform.event_cursors WHERE consumer = 'probe'")
        assert conn.execute(cursor).scalar_one() == 1


# A consumer run by the dispatcher in this process.


@transaction
def _record(uow: Uow, event_id: str, event_type: str) -> None:
    uow.execute(
        "INSERT INTO scratch.probed (event_id, type) VALUES (:id, :type)",
        {"id": event_id, "type": event_type},
    )


@workflow("test.events.probe")
def _probe(event_id: str, envelope: str) -> None:
    _record(event_id, EventEnvelope.model_validate_json(envelope).type)


def _wait_for[T](probe: Callable[[], T | None], timeout: float = 15) -> T:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = probe()
        if found:
            return found
        time.sleep(0.05)
    raise AssertionError("timed out waiting")


def test_dispatcher_thread_delivers_on_notify(database_url: str, engine: Engine) -> None:
    """The listening thread delivers each event of its consumer's types, and skips others."""
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA scratch"))
        conn.execute(text("CREATE TABLE scratch.probed (event_id text, type text)"))
    conninfo = make_url(database_url).set(drivername="postgresql")
    with running(database_url):
        dispatching = DispatcherThread(
            Dispatcher([Consumer("probe", frozenset({"factory.loaded"}), _probe)]),
            conninfo.render_as_string(hide_password=False),
            poll_seconds=60,
        )
        dispatching.start()
        try:
            started = time.monotonic()
            loaded = unit_of_work(lambda uow: emit(uow, _loaded()))
            unit_of_work(lambda uow: emit(uow, FactoryRefused(factory="x", problems=("p",))))

            def cursor() -> int | None:
                with engine.connect() as conn:
                    query = text("SELECT seq FROM platform.event_cursors WHERE consumer = 'probe'")
                    return conn.execute(query).scalar_one_or_none()

            assert _wait_for(lambda: cursor() == 2 or None)
            DBOS.retrieve_workflow(f"evt-probe-{loaded.event_id}").get_result()
            assert time.monotonic() - started < 30
        finally:
            dispatching.stop()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT event_id, type FROM scratch.probed")).all()
    assert [tuple(r) for r in rows] == [(str(loaded.event_id), "factory.loaded")]


# REQ-0319: a consumer reads current state through its owner's interface.


class _Tasks:
    """A fixture owner: a task's current state, behind the owner's interface."""

    def __init__(self) -> None:
        self.states: dict[uuid.UUID, int] = {}

    def current(self, task: uuid.UUID) -> int:
        return self.states[task]


class _Board:
    """A fixture consumer: it mirrors each task's state from the owner, not from the event."""

    def __init__(self, tasks: _Tasks) -> None:
        self.tasks = tasks
        self.shown: dict[uuid.UUID, int] = {}

    def handle(self, envelope: EventEnvelope) -> None:
        task = envelope.project
        current = self.tasks.current(task)
        if self.shown.get(task) == current:
            return  # the state has moved on, or this event changes nothing
        self.shown[task] = current


def test_consumer_order_independent() -> None:
    task = uuid.uuid4()
    tasks = _Tasks()
    tasks.states[task] = 2
    events = [
        EventEnvelope(
            event_id=uuid.uuid7(),
            project=task,
            seq=version,
            type="project.configured",
            event_version=1,
            occurred_at=datetime.now(UTC),
            payload={"version": version, "hash": DIGEST},
        )
        for version in (1, 2)
    ]
    in_order, reversed_order = _Board(tasks), _Board(tasks)
    for envelope in events:
        in_order.handle(envelope)
    for envelope in reversed(events):
        reversed_order.handle(envelope)
    assert in_order.shown == reversed_order.shown == {task: 2}
