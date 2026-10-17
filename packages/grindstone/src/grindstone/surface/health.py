"""Liveness and readiness endpoints.

`/healthz` answers while the process runs; `/readyz` answers 200 only when
every dependency is ok, and is what the compose health check uses.
"""

from collections.abc import Callable

from fastapi import APIRouter, Response, status

from grindstone import __version__
from grindstone.contracts import DependencyHealth, HealthStatus, ServiceHealth


def health_router(probes: Callable[[], tuple[DependencyHealth, ...]]) -> APIRouter:
    """Build the health routes around a callable that probes every dependency."""
    router = APIRouter(tags=["health"])

    @router.get("/healthz")
    def healthz() -> ServiceHealth:
        return ServiceHealth(service="grindstone", version=__version__, status=HealthStatus.OK)

    @router.get("/readyz")
    def readyz(response: Response) -> ServiceHealth:
        report = ServiceHealth.from_dependencies("grindstone", __version__, probes())
        if report.status is not HealthStatus.OK:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return report

    return router
