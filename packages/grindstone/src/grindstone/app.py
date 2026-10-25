"""Composition root: wires the kernel modules into the control-plane process.

This is the only place that knows every module; the modules themselves
follow the dependency rules of the module map (FF-01).
"""

from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager

from fastapi import FastAPI

from grindstone import __version__
from grindstone.store import DatabaseSettings, Schedule, ping, start_runtime, stop_runtime
from grindstone.surface import health_router

# Scheduled workflows the modules declare (REQ-0214); M1's arrive with their owners.
SCHEDULES: tuple[Schedule, ...] = ()


def create_app(
    database: DatabaseSettings | None = None, *, schedules: Sequence[Schedule] = SCHEDULES
) -> FastAPI:
    """Build the control-plane ASGI application.

    Its lifespan opens the store and launches DBOS before the first request,
    and shuts DBOS down after the last (SPEC-02, REQ-0201).
    """
    db = database or DatabaseSettings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        app.state.runtime = await start_runtime(db.url(), schedules=schedules)
        try:
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
