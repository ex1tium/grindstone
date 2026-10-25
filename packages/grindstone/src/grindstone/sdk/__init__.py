"""SDK layer. The only package a factory imports: a curated, semantically
versioned subset of `contracts` and the `platform` registries (Components
tab, Kernel SDK).

SDK 0.1.0 holds no logic of its own; it re-exports the names in SPEC-03's
export table. A name added is a minor version, a name changed or removed a
major one (ADR-05). The port protocols and their models join with the
specifications that own them: SPEC-06 part 1 (`WorkspaceProvider`,
`SubjectResolver`, `RunContext`, `Materialization`, `CollectOutcome`) and
SPEC-08 (`CheckMethod`, `DeliveryAdapter` and their models).
"""

from grindstone.contracts.errors import ErrorEnvelope
from grindstone.contracts.hashing import semantic_hash
from grindstone.contracts.ids import item_id_type
from grindstone.contracts.platform import (
    CapabilityDecl,
    CheckMethodDecl,
    EdgeDecl,
    FactoryManifest,
    FieldDecl,
    KindDecl,
    TemplateDecl,
)
from grindstone.contracts.ports import BlobReader, Context, FactoryStorage, ItemReader, SecretReader
from grindstone.contracts.refs import BlobRef, ItemRef, SemanticHash, SubjectRef
from grindstone.platform.registries import SDK_VERSION, register_error_code

__version__ = SDK_VERSION

__all__ = [
    "BlobReader",
    "BlobRef",
    "CapabilityDecl",
    "CheckMethodDecl",
    "Context",
    "EdgeDecl",
    "ErrorEnvelope",
    "FactoryManifest",
    "FactoryStorage",
    "FieldDecl",
    "ItemReader",
    "ItemRef",
    "KindDecl",
    "SecretReader",
    "SemanticHash",
    "SubjectRef",
    "TemplateDecl",
    "item_id_type",
    "register_error_code",
    "semantic_hash",
]
