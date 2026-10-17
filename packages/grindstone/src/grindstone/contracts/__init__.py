"""Foundation layer. The single source of types: Pydantic models for every
kernel record, typed IDs, hashing and canonical JSON. Everything else is
generated from these models (ADR-05).

`EXPORTED` lists every model whose JSON Schema and TypeScript type are
generated into `packages/contracts-ts`; the generated files are checked for
drift in CI (FF-02).
"""

from pydantic import BaseModel

from grindstone.contracts.base import Contract, bundle_schema
from grindstone.contracts.health import DependencyHealth, HealthStatus, ServiceHealth

EXPORTED: tuple[type[BaseModel], ...] = (ServiceHealth,)

__all__ = [
    "EXPORTED",
    "Contract",
    "DependencyHealth",
    "HealthStatus",
    "ServiceHealth",
    "bundle_schema",
]
