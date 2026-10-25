"""Composition root: wires the kernel modules into the control-plane process.

This is the only place that knows every module; the modules themselves
follow the dependency rules of the module map (FF-01).
"""

import asyncio
import logging
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager

from fastapi import FastAPI

from grindstone import __version__, decisions
from grindstone.contracts.platform import InstanceConfig
from grindstone.intent import KindCatalog, sync_lifecycle_states
from grindstone.platform import CORE_ORIGIN, Category, Registries, core_registries
from grindstone.platform.configuration import Platform, startup_instance_config
from grindstone.platform.events import Consumer, Dispatcher, DispatcherThread
from grindstone.platform.loader import LoadReport, discover, load_factories, record_loads
from grindstone.stations import kernel_resolvers
from grindstone.store import (
    DatabaseSettings,
    Schedule,
    ping,
    start_runtime,
    stop_runtime,
    unit_of_work,
)
from grindstone.surface import health_router

_log = logging.getLogger(__name__)

# Scheduled workflows the modules declare (REQ-0214); M1's arrive with their owners.
SCHEDULES: tuple[Schedule, ...] = ()

# Event consumers the modules declare (REQ-0314).
CONSUMERS: tuple[Consumer, ...] = (decisions.CONSUMER,)


def load_platform() -> tuple[Registries, LoadReport, KindCatalog]:
    """The registries with the `core` names and every installed factory that passes.

    A refused factory is reported and recorded; the kernel and every other
    factory still start (SPEC-03, REQ-0304). The kinds are compiled once into
    a catalog, and the lifecycle states the database admits are rewritten
    from it (SPEC-04, DEC-0405).
    """
    registries = core_registries()
    for subject_kind, resolver in kernel_resolvers().items():
        registries.register(Category.SUBJECT_RESOLVER, subject_kind, resolver, CORE_ORIGIN)
    report = load_factories(registries, discover())
    for line in report.lines():
        (_log.warning if line.startswith("refused") else _log.info)("factory %s", line)
    unit_of_work(lambda uow: record_loads(uow, report))
    catalog = KindCatalog.from_registries(registries)
    unit_of_work(lambda uow: sync_lifecycle_states(uow, catalog))
    return registries, report, catalog


def report_projects(platform: Platform) -> None:
    """Log and announce every project paused by a missing or invalid configuration (REQ-0312).

    Pause is derived, never stored (FF-09): this only reports it, as a log
    line and a `config.invalid` event.
    """
    for status in unit_of_work(platform.announce_paused):
        for problem in status.problems:
            _log.warning("project %s paused: %s", status.slug, problem)


def create_app(
    database: DatabaseSettings | None = None,
    *,
    schedules: Sequence[Schedule] = SCHEDULES,
    consumers: Sequence[Consumer] = CONSUMERS,
) -> FastAPI:
    """Build the control-plane ASGI application.

    Its lifespan opens the store and launches DBOS before the first request,
    loads the factories into frozen registries, starts the event dispatcher,
    and stops both after the last request (SPEC-02, REQ-0201; SPEC-03). An
    invalid instance configuration stops start-up before anything opens
    (REQ-0310).
    """
    db = database or DatabaseSettings.from_env()
    dispatcher = Dispatcher(consumers)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        instance: InstanceConfig = startup_instance_config()
        app.state.runtime = await start_runtime(db.url(), schedules=schedules)
        try:
            loaded = await asyncio.to_thread(load_platform)
            app.state.registries, app.state.factories, app.state.kinds = loaded
            app.state.platform = Platform(instance, app.state.factories)
            app.state.decisions = decisions.Decisions(app.state.registries)
            await asyncio.to_thread(report_projects, app.state.platform)
            dispatching = DispatcherThread(dispatcher, db.conninfo())
            dispatching.start()
            try:
                yield
            finally:
                await asyncio.to_thread(dispatching.stop)
        finally:
            await stop_runtime()

    app = FastAPI(
        title="Grindstone",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.include_router(health_router(lambda: (ping(db),)))
    return app
