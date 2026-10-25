"""DBOS in the control plane: launch, the workflow registry, starts and the version guard.

Every workflow runs on DBOS Transact inside the control-plane process (ADR-03).
This module is the only place that configures DBOS (SPEC-02, DEC-0204):

- `start_runtime` runs in the FastAPI lifespan. It opens the store (migrations
  and the datasource, which DBOS needs before launch), launches DBOS with its
  system tables in schema `dbos` of the same database and an explicit
  application version, and from then on uses only DBOS's asynchronous calls,
  because DBOS refuses its synchronous ones while the event loop runs (SPK-2).
- `WORKFLOW_VERSION` is that application version. DBOS recovers only workflows
  of its own version, and its default is a hash of the workflow source, which
  would strand every workflow in flight on any code change. So the version is
  explicit and rises only when workflow code changes incompatibly; CI's
  workflow-version check (`scripts/ff/workflow_versions.py`) enforces it.
- The start-up guard (REQ-0207): DBOS recovers this version's pending
  workflows by itself. If workflows of another version are pending, the
  process still serves, but `start` refuses new dispatch with
  `workflow_version_mismatch` and the list of stranded workflows, until the
  operator drains them on the old image or moves each with
  `grindstone workflows fork` (`grindstone.store.admin`).
- `start` gives every workflow an ID derived from its record (REQ-0205), so
  starting it twice runs it once, and checks that the workflow's first input
  is that record's ID, from which its external steps' idempotency keys are
  built (REQ-0204, `grindstone.store.steps`).
- `Schedule` states for every scheduled workflow whether missed periods are
  backfilled; the default skips them (REQ-0214, DEC-0205).
- Lanes and the modules' other queues are registered at launch
  (`grindstone.store.lanes`, REQ-0206); `enqueue` puts a workflow on one,
  under the same ID and record rules as `start`.
"""

import asyncio
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any

import sqlalchemy
from dbos import DBOS, Queue, ScheduleInput, SetWorkflowID, WorkflowHandle
from dbos import WorkflowStatus as DBOSWorkflowStatus
from pydantic import JsonValue
from sqlalchemy import URL

from grindstone.store.database import close_database, open_database
from grindstone.store.errors import StoreError
from grindstone.store.lanes import QueueSpec, register_queues
from grindstone.store.schema import MigrationSources
from grindstone.store.steps import bind_record

_log = logging.getLogger(__name__)

WORKFLOW_VERSION = "1"
"""DBOS's application version. Raise it only for a replay-incompatible workflow change."""

APP_NAME = "grindstone"
SYSTEM_SCHEMA = "dbos"
# Workflows that still hold work: started and not finished, or waiting on a queue.
_UNFINISHED = ["PENDING", "ENQUEUED"]

type ScheduledWorkflow = Callable[[datetime, Any], None]


class _Registry:
    """Workflows registered through `workflow`, by their registered name."""

    workflows: dict[str, Callable[..., Any]]

    def __init__(self) -> None:
        self.workflows = {}


_registry = _Registry()


def workflow[**P, R](name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Register the decorated function as the DBOS workflow `name`.

    The name, not the function's import path, is what DBOS records and
    recovers by, so moving or renaming the function keeps workflows in
    flight. The workflow-version check hashes every function registered here.
    The workflow's first input is the causing record's ID, which keys its
    external steps.
    """

    def register(func: Callable[P, R]) -> Callable[P, R]:
        if name in _registry.workflows:
            raise ValueError(f"workflow {name!r} is already registered")
        registered = DBOS.workflow(name=name)(bind_record(func))
        _registry.workflows[name] = registered
        return registered

    return register


def registered_workflows() -> Mapping[str, Callable[..., Any]]:
    """Every workflow registered through `workflow`, by name."""
    return MappingProxyType(_registry.workflows)


@dataclass(frozen=True, slots=True)
class Schedule:
    """A scheduled workflow: what runs, when, and whether missed periods run later.

    `cron` has six fields, seconds first. With `backfill` false (the default)
    periods missed while the control plane was down are skipped, because
    every M1 schedule is a poll whose next run covers them (DEC-0205).
    """

    name: str
    workflow: ScheduledWorkflow
    cron: str
    backfill: bool = False

    def as_dbos(self) -> ScheduleInput:
        return {
            "schedule_name": self.name,
            "workflow_fn": self.workflow,
            "schedule": self.cron,
            "automatic_backfill": self.backfill,
        }


@dataclass(frozen=True, slots=True)
class StrandedWorkflow:
    """A workflow of another application version, which this process will not run."""

    workflow_id: str
    name: str
    version: str | None


@dataclass(slots=True)
class Runtime:
    """What `start_runtime` found and set up."""

    version: str
    stranded: tuple[StrandedWorkflow, ...] = field(default=())
    queues: Mapping[str, Queue] = field(default_factory=lambda: MappingProxyType({}))
    """The lanes and declared queues, by name."""

    @property
    def dispatching(self) -> bool:
        """Whether new workflows may start: no workflow of another version is pending."""
        return not self.stranded


class _Active:
    runtime: Runtime | None = None


_active = _Active()


async def start_runtime(
    url: URL | str,
    *,
    application_version: str = WORKFLOW_VERSION,
    schedules: Sequence[Schedule] = (),
    queues: Sequence[QueueSpec] = (),
    migrations: MigrationSources | None = None,
) -> Runtime:
    """Open the store and launch DBOS; call once, from the async lifespan.

    Migrations run in a worker thread, so the event loop never blocks on
    them. Every queue (`queue_specs`: the lanes and the modules' declared
    queues) is registered, so this version's queued workflows resume on them.
    When workflows of another version are pending, the guard reports them,
    schedules are not applied, and `start` and `enqueue` refuse new dispatch.
    """
    if _active.runtime is not None:
        raise RuntimeError("the runtime is already started in this process")
    system_url = sqlalchemy.make_url(url).set(drivername="postgresql+psycopg")
    # DBOS is configured first, so the datasource registers with this instance
    # rather than one an earlier start left behind; it launches only after.
    DBOS(
        config={
            "name": APP_NAME,
            "system_database_url": system_url.render_as_string(hide_password=False),
            "dbos_system_schema": SYSTEM_SCHEMA,
            "application_version": application_version,
        }
    )
    try:
        await asyncio.to_thread(open_database, url, migrations=migrations)
        DBOS.launch()
        registered = await register_queues(queues)
        runtime = Runtime(version=application_version, queues=registered)
        runtime.stranded = _stranded(await _unfinished_async(), application_version)
        if runtime.stranded:
            _report(runtime.stranded, application_version)
        elif schedules:
            await DBOS.apply_schedules_async([s.as_dbos() for s in schedules])
    except BaseException:
        DBOS.destroy()
        close_database()
        raise
    _active.runtime = runtime
    return runtime


async def stop_runtime() -> None:
    """Shut DBOS down and close the store; workflows in flight resume on the next start."""
    _active.runtime = None
    DBOS.destroy()
    close_database()


def current_runtime() -> Runtime:
    """The runtime `start_runtime` set up for this process."""
    if _active.runtime is None:
        raise RuntimeError("the runtime is not started: call start_runtime() at start-up")
    return _active.runtime


def start[**P, R](
    workflow_id: str, func: Callable[P, R], /, *args: P.args, **kwargs: P.kwargs
) -> WorkflowHandle[R]:
    """Start `func` under `workflow_id`, an ID derived from the record that caused it.

    Starting the same ID again returns the existing workflow instead of
    running it twice. The first positional argument is the causing record's
    ID, which keys the workflow's external steps. Outside a workflow, a start
    while workflows of another version are stranded is refused with
    `workflow_version_mismatch`; a workflow that DBOS recovered may still
    start its children.
    """
    _check_dispatch(workflow_id, args)
    with SetWorkflowID(workflow_id):
        return DBOS.start_workflow(func, *args, **kwargs)


def enqueue[**P, R](
    queue: str, workflow_id: str, func: Callable[P, R], /, *args: P.args, **kwargs: P.kwargs
) -> WorkflowHandle[R]:
    """Put `func` on the lane or declared queue `queue`, under `workflow_id`.

    The same rules as `start`: an ID derived from the causing record, that
    record's ID as the first input, enqueuing the same ID again returns the
    existing workflow, and no new dispatch while workflows are stranded.
    """
    _check_dispatch(workflow_id, args)
    found = current_runtime().queues.get(queue)
    if found is None:
        raise ValueError(f"no lane or queue {queue!r} was registered at start-up")
    with SetWorkflowID(workflow_id):
        return found.enqueue(func, *args, **kwargs)


def _check_dispatch(workflow_id: str, args: Sequence[object]) -> None:
    _check_id(workflow_id)
    _check_record(args)
    runtime = current_runtime()
    if not runtime.dispatching and DBOS.workflow_id is None:
        runtime.stranded = _stranded(_unfinished(), runtime.version)
        _refuse_if_stranded(runtime)


def _check_id(workflow_id: str) -> None:
    if not workflow_id.strip():
        raise ValueError("a workflow is started with an ID derived from its record")


def _check_record(args: Sequence[object]) -> None:
    if not args or not isinstance(args[0], str) or not args[0].strip():
        raise ValueError("a workflow takes the ID of the record that caused it as its first input")


def _unfinished() -> list[DBOSWorkflowStatus]:
    return DBOS.list_workflows(status=_UNFINISHED, load_input=False, load_output=False)


async def _unfinished_async() -> list[DBOSWorkflowStatus]:
    return await DBOS.list_workflows_async(status=_UNFINISHED, load_input=False, load_output=False)


def _stranded(
    unfinished: Sequence[DBOSWorkflowStatus], version: str
) -> tuple[StrandedWorkflow, ...]:
    return tuple(
        StrandedWorkflow(workflow_id=w.workflow_id, name=w.name, version=w.app_version)
        for w in sorted(unfinished, key=lambda w: w.workflow_id)
        if w.app_version != version
    )


def _detail(stranded: Sequence[StrandedWorkflow], version: str) -> dict[str, JsonValue]:
    workflows: list[JsonValue] = [
        {"workflow_id": s.workflow_id, "name": s.name, "version": s.version} for s in stranded
    ]
    return {"version": version, "stranded": workflows}


def _report(stranded: Sequence[StrandedWorkflow], version: str) -> None:
    for s in stranded:
        _log.error(
            "workflow %s (%s) is pending under version %s, not %s: dispatch is stopped",
            s.workflow_id,
            s.name,
            s.version,
            version,
        )
    _log.error(
        "%d stranded workflows: drain them on the previous image, "
        "or move each with `grindstone workflows fork <id>`",
        len(stranded),
    )


def _refuse_if_stranded(runtime: Runtime) -> None:
    if runtime.stranded:
        raise StoreError(
            "workflow_version_mismatch",
            f"{len(runtime.stranded)} workflows of another version are pending; "
            "no new workflow starts until they are drained or forked",
            detail=_detail(runtime.stranded, runtime.version),
        )
