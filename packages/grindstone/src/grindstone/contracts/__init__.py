"""Foundation layer. The single source of types: Pydantic models for every
kernel record, typed IDs, hashing and canonical JSON. Everything else is
generated from these models (ADR-05).

`EXPORTED` lists every model whose JSON Schema and TypeScript type are
generated into `packages/contracts-ts`; the generated files are checked for
drift in CI (FF-02).
"""

from pydantic import BaseModel

from grindstone.contracts.base import MAX_SAFE_INTEGER, Contract, Presentation, bundle_schema
from grindstone.contracts.change import (
    ApprovalPayload,
    ChangeDraft,
    ChangeSet,
    ChangeSetApplied,
    ChangeSetDrafted,
    ChangeSetRejected,
    ChangeSetWalked,
    WalkResult,
)
from grindstone.contracts.decisions import (
    Answer,
    Decision,
    DecisionAnswered,
    DecisionRaised,
    DecisionSuperseded,
)
from grindstone.contracts.errors import (
    KERNEL_ERROR_CODES,
    ErrorClass,
    ErrorEnvelope,
    error_class_of,
    register_error_codes,
)
from grindstone.contracts.events import (
    INSTANCE_STREAM,
    ConfigInvalid,
    EventEnvelope,
    FactoryLoaded,
    FactoryRefused,
    KernelEvent,
    ProjectConfigured,
)
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
from grindstone.contracts.intent import ItemRevised, ItemTransitioned
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
    ErrorEnvelope,
    EventEnvelope,
    FactoryLoaded,
    FactoryRefused,
    ProjectConfigured,
    ConfigInvalid,
    Decision,
    Answer,
    DecisionRaised,
    DecisionAnswered,
    DecisionSuperseded,
    ItemRevised,
    ItemTransitioned,
    ChangeDraft,
    WalkResult,
    ChangeSet,
    ApprovalPayload,
    ChangeSetDrafted,
    ChangeSetWalked,
    ChangeSetApplied,
    ChangeSetRejected,
)

__all__ = [
    "EXPORTED",
    "INSTANCE_STREAM",
    "ITEM_ID_GRAMMAR",
    "KERNEL_ERROR_CODES",
    "MAX_SAFE_INTEGER",
    "Answer",
    "ApprovalPayload",
    "AuthorKind",
    "BlobHash",
    "BlobRef",
    "BlobSetSubject",
    "BlobSubject",
    "ChangeDraft",
    "ChangeSet",
    "ChangeSetApplied",
    "ChangeSetDrafted",
    "ChangeSetId",
    "ChangeSetRejected",
    "ChangeSetWalked",
    "ConfigInvalid",
    "Contract",
    "Decision",
    "DecisionAnswered",
    "DecisionId",
    "DecisionRaised",
    "DecisionSuperseded",
    "DependencyHealth",
    "ErrorClass",
    "ErrorEnvelope",
    "EventEnvelope",
    "FactoryLoaded",
    "FactoryRefused",
    "GitCommitSubject",
    "GitObjectName",
    "HealthStatus",
    "ItemId",
    "ItemRef",
    "ItemRevised",
    "ItemRevisionSubject",
    "ItemTransitioned",
    "KernelEvent",
    "Presentation",
    "ProjectConfigured",
    "Provenance",
    "RunId",
    "RunManifest",
    "SemanticHash",
    "ServiceHealth",
    "SubjectRef",
    "TaskId",
    "WalkResult",
    "bundle_schema",
    "error_class_of",
    "item_id_type",
    "new_record_id",
    "register_error_codes",
]
