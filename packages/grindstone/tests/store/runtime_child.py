"""Workflows for the runtime tests, and a stand-in control plane that runs them.

The test module imports the workflows, so both processes register the same
names. As a subprocess, run from the repository root:

    python -m packages.grindstone.tests.store.runtime_child park <database_url> <record>
        Start as version `v1`, start `test.parked` for <record>, and exit
        abruptly once it waits for its message, leaving it pending under `v1`.
    python -m packages.grindstone.tests.store.runtime_child parent <database_url>
        Start `test.parent`, which starts a child. With `GRINDSTONE_TEST_KILL_AT`
        set to `after_child_start`, die there the first time (a marker file in
        `GRINDSTONE_TEST_KILL_MARKER` records it); a restart recovers the parent.
"""

import asyncio
import os
import signal
import sys
import time
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from dbos import DBOS
from sqlalchemy import Engine, text

from grindstone.store import (
    WORKFLOW_VERSION,
    QueueSpec,
    Runtime,
    Schedule,
    Uow,
    start,
    start_runtime,
    stop_runtime,
    transaction,
    workflow,
)

STRAND_VERSION = "v1"
PARENT_ID = "parent-rec-1"
KILL_AT_ENV = "GRINDSTONE_TEST_KILL_AT"
MARKER_ENV = "GRINDSTONE_TEST_KILL_MARKER"


def create_scratch(engine: Engine) -> None:
    """The table the test workflows record their effects in."""
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA scratch"))
        conn.execute(text("CREATE TABLE scratch.effects (what text NOT NULL)"))


def effects(engine: Engine, what: str) -> int:
    """How many times the effect `what` was recorded."""
    with engine.connect() as conn:
        query = text("SELECT count(*) FROM scratch.effects WHERE what = :what")
        return conn.execute(query, {"what": what}).scalar_one()


@transaction
def record_effect(uow: Uow, what: str) -> None:
    uow.execute("INSERT INTO scratch.effects (what) VALUES (:what)", {"what": what})


@workflow("test.child")
def child(record: str) -> str:
    record_effect(f"child:{record}")
    return record


@workflow("test.parent")
def parent(record: str) -> str:
    handle = start(f"{DBOS.workflow_id}.child", child, record)
    _kill_point("after_child_start")
    return handle.get_result()


@workflow("test.parked")
def parked(record: str) -> str:
    record_effect(f"parked:{record}")
    message = DBOS.recv("go", timeout_seconds=300)
    record_effect(f"received:{record}:{message}")
    return str(message)


@workflow("test.tick")
def tick(at: datetime, context: object) -> None:
    del at, context


def _kill_point(name: str) -> None:
    """Die abruptly at `name`, once: no cleanup, no checkpoint."""
    if os.environ.get(KILL_AT_ENV) != name:
        return
    marker = Path(os.environ[MARKER_ENV])
    if marker.exists():
        return
    marker.write_text(name)
    if sys.platform != "win32":
        os.kill(os.getpid(), signal.SIGKILL)
    os._exit(137)


@contextmanager
def running(
    url: str,
    version: str = WORKFLOW_VERSION,
    schedules: Sequence[Schedule] = (),
    queues: Sequence[QueueSpec] = (),
) -> Generator[Runtime]:
    """The runtime started as the lifespan starts it, on an event loop kept open.

    DBOS makes its executor the loop's default one, so the loop must outlive
    the runtime: closing it would shut the executor down.
    """
    with asyncio.Runner() as runner:
        runtime = runner.run(
            start_runtime(url, application_version=version, schedules=schedules, queues=queues)
        )
        try:
            yield runtime
        finally:
            runner.run(stop_runtime())


def _park(database_url: str, record: str) -> int:
    with running(database_url, STRAND_VERSION):
        start(f"park-{record}", parked, record)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            steps = DBOS.list_workflow_steps(f"park-{record}")
            # The parked effect is checkpointed, and recv has started its timeout.
            if len(steps) >= 2:
                time.sleep(0.5)
                os._exit(0)
            time.sleep(0.1)
    return 1


def _parent(database_url: str) -> int:
    with running(database_url):
        # On restart the parent already exists and DBOS's recovery runs it.
        if DBOS.get_workflow_status(PARENT_ID) is None:
            start(PARENT_ID, parent, "rec-1")
        DBOS.retrieve_workflow(PARENT_ID).get_result()
    return 0


if __name__ == "__main__":
    mode, url = sys.argv[1], sys.argv[2]
    sys.exit(_park(url, sys.argv[3]) if mode == "park" else _parent(url))
