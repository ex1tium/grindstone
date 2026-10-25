"""Composition root: wires the kernel modules into the control-plane process.

This is the only place that knows every module; the modules themselves
follow the dependency rules of the module map (FF-01).
"""

import asyncio
import logging
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager

from fastapi import FastAPI

from grindstone import __version__, change, decisions
from grindstone.contracts.ids import ProjectId
from grindstone.contracts.platform import InstanceConfig
from grindstone.intent import KindCatalog, sync_lifecycle_states
from grindstone.platform import CORE_ORIGIN, Category, Registries, core_registries
from grindstone.platform.configuration import (
    Platform,
    project_config,
    startup_instance_config,
)
from grindstone.platform.events import Consumer, Dispatcher, DispatcherThread
from grindstone.platform.loader import LoadReport, discover, load_factories, record_loads
from grindstone.stations import kernel_resolvers
from grindstone.store import (
    DatabaseSettings,
    QueueSpec,
    Schedule,
    Uow,
    close_blob_store,
    open_blob_store,
    ping,
    start_runtime,
    stop_runtime,
    unit_of_work,
)
from grindstone.surface import health_router

_log = logging.getLogger(__name__)

# Scheduled workflows the modules declare (REQ-0214); M1's arrive with their owners.
SCHEDULES: tuple[Schedule, ...] = ()

# Lanes and the modules' other queues (REQ-0206). Station lanes come from
# `[stations]` once SPEC-06 part 1 types it (TKT-0602); SPEC-08 adds `delivery.gate`.
QUEUES: tuple[QueueSpec, ...] = ()

# Continuations answered decisions run, by name (SPEC-04, DEC-0403).
decisions.register_continuation(change.APPLY, change.apply_changeset)

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


def enabled_factories(platform: Platform) -> change.EnabledFactories:
    """The factories a project's current configuration enables; `core` is always enabled.

    A project without a valid configuration enables none.
    """

    def enabled(uow: Uow, project: ProjectId) -> frozenset[str]:
        current = project_config(uow, project)
        config = None if current is None else platform.validate(current.toml)[0]
        return frozenset() if config is None else frozenset(config.factories)

    return enabled


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
    queues: Sequence[QueueSpec] = QUEUES,
    consumers: Sequence[Consumer] = CONSUMERS,
) -> FastAPI:
    """Build the control-plane ASGI application.

    Its lifespan opens the store and launches DBOS before the first request,
    sets up the blob store from `[store]`, loads the factories into frozen
    registries, starts the event dispatcher, and stops both after the last
    request (SPEC-02, REQ-0201; SPEC-03). An
    invalid instance configuration stops start-up before anything opens
    (REQ-0310).
    """
    db = database or DatabaseSettings.from_env()
    dispatcher = Dispatcher(consumers)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        instance: InstanceConfig = startup_instance_config()
        app.state.runtime = await start_runtime(db.url(), schedules=schedules, queues=queues)
        app.state.blobs = open_blob_store(instance.store)
        try:
            loaded = await asyncio.to_thread(load_platform)
            app.state.registries, app.state.factories, app.state.kinds = loaded
            app.state.platform = Platform(instance, app.state.factories)
            app.state.decisions = decisions.Decisions(
                app.state.registries, kinds=[change.APPROVAL_KIND]
            )
            app.state.changesets = change.ChangeSets(
                change.Rules(app.state.kinds, enabled_factories(app.state.platform)),
                app.state.decisions,
                change.impacts_of(app.state.registries),
            )
            change.install(app.state.changesets)
            await asyncio.to_thread(report_projects, app.state.platform)
            dispatching = DispatcherThread(dispatcher, db.conninfo())
            dispatching.start()
            try:
                yield
            finally:
                await asyncio.to_thread(dispatching.stop)
        finally:
            close_blob_store()
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
