"""Composition root: wires the kernel modules into the control-plane process.

This is the only place that knows every module; the modules themselves
follow the dependency rules of the module map (FF-01).
"""

import asyncio
import logging
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager

from fastapi import FastAPI

from grindstone import __version__
from grindstone.platform import Registries, core_registries
from grindstone.platform.loader import LoadReport, discover, load_factories, record_loads
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


def load_platform() -> tuple[Registries, LoadReport]:
    """The registries with the `core` names and every installed factory that passes.

    A refused factory is reported and recorded; the kernel and every other
    factory still start (SPEC-03, REQ-0304).
    """
    registries = core_registries()
    report = load_factories(registries, discover())
    for line in report.lines():
        (_log.warning if line.startswith("refused") else _log.info)("factory %s", line)
    unit_of_work(lambda uow: record_loads(uow, report))
    return registries, report


def create_app(
    database: DatabaseSettings | None = None, *, schedules: Sequence[Schedule] = SCHEDULES
) -> FastAPI:
    """Build the control-plane ASGI application.

    Its lifespan opens the store and launches DBOS before the first request,
    loads the factories into frozen registries, and shuts DBOS down after the
    last request (SPEC-02, REQ-0201; SPEC-03).
    """
    db = database or DatabaseSettings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        app.state.runtime = await start_runtime(db.url(), schedules=schedules)
        try:
            app.state.registries, app.state.factories = await asyncio.to_thread(load_platform)
            yield
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
