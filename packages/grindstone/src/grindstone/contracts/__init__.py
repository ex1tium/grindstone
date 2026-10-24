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
from grindstone.contracts.ids import (
    ITEM_ID_GRAMMAR,
    ChangeSetId,
    DecisionId,
    ItemId,
    RunId,
    TaskId,
    item_id_type,
    new_record_id,
)
from grindstone.contracts.provenance import AuthorKind, Provenance
from grindstone.contracts.refs import (
    BlobHash,
    BlobRef,
    BlobSetSubject,
    BlobSubject,
    GitCommitSubject,
    GitObjectName,
    ItemRef,
    ItemRevisionSubject,
    SemanticHash,
    SubjectRef,
)
from grindstone.contracts.run import RunManifest

EXPORTED: tuple[type[BaseModel], ...] = (
    ServiceHealth,
    ItemRef,
    BlobRef,
    GitCommitSubject,
    BlobSubject,
    BlobSetSubject,
    ItemRevisionSubject,
    Provenance,
    RunManifest,
)

__all__ = [
    "EXPORTED",
    "ITEM_ID_GRAMMAR",
    "AuthorKind",
    "BlobHash",
    "BlobRef",
    "BlobSetSubject",
    "BlobSubject",
    "ChangeSetId",
    "Contract",
    "DecisionId",
    "DependencyHealth",
    "GitCommitSubject",
    "GitObjectName",
    "HealthStatus",
    "ItemId",
    "ItemRef",
    "ItemRevisionSubject",
    "Provenance",
    "RunId",
    "RunManifest",
    "SemanticHash",
    "ServiceHealth",
    "SubjectRef",
    "TaskId",
    "bundle_schema",
    "item_id_type",
    "new_record_id",
]
