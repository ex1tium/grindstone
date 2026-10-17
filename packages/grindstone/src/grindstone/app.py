"""Composition root: wires the kernel modules into the control-plane process.

This is the only place that knows every module; the modules themselves
follow the dependency rules of the module map (FF-01).
"""

from fastapi import FastAPI

from grindstone import __version__
from grindstone.store import DatabaseSettings, ping
from grindstone.surface import health_router


def create_app(database: DatabaseSettings | None = None) -> FastAPI:
    """Build the control-plane ASGI application."""
    db = database or DatabaseSettings.from_env()
    app = FastAPI(title="Grindstone", version=__version__, docs_url=None, redoc_url=None)
    app.include_router(health_router(lambda: (ping(db),)))
    return app
