"""Health payloads shared by every Grindstone process.

The control plane, the agent host and the runner report their health in this
shape, so operators and the compose health checks read one format.
"""

from enum import StrEnum
from typing import Literal

from pydantic import Field

from grindstone.contracts.base import Contract


class HealthStatus(StrEnum):
    """Overall state of a service or one of its dependencies."""

    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"


class DependencyHealth(Contract):
    """The state of one thing a service needs, such as its database."""

    name: str = Field(min_length=1, description="Stable name of the dependency, e.g. `postgres`.")
    status: HealthStatus
    detail: str | None = Field(
        default=None,
        description="Short reason for a non-ok status, safe to show to the operator.",
    )


class ServiceHealth(Contract):
    """Readiness report of one Grindstone service."""

    schema_version: Literal[1] = 1
    service: Literal["grindstone", "agent-host", "runner"]
    version: str = Field(min_length=1)
    status: HealthStatus
    dependencies: tuple[DependencyHealth, ...] = ()

    @classmethod
    def from_dependencies(
        cls,
        service: Literal["grindstone", "agent-host", "runner"],
        version: str,
        dependencies: tuple[DependencyHealth, ...],
    ) -> ServiceHealth:
        """Derive the overall status: down if any dependency is down, else the worst one."""
        statuses = {d.status for d in dependencies}
        if HealthStatus.DOWN in statuses:
            status = HealthStatus.DOWN
        elif HealthStatus.DEGRADED in statuses:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.OK
        return cls(service=service, version=version, status=status, dependencies=dependencies)
