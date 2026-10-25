"""Domain layer. Items and their history: items, revisions, artifacts,
references and edges, lifecycles and rendering (ADR-08, ADR-09).
"""

from grindstone.intent.catalog import KindCatalog
from grindstone.intent.errors import IntentError
from grindstone.intent.items import (
    Materialised,
    Proposal,
    RevisionBatch,
    Step,
    allocate,
    applying,
    check_id,
    current_hash,
    derive_edges,
    edges_to,
    materialise,
    read,
    read_pinned,
    sync_lifecycle_states,
    transition,
    transition_allowed,
    unresolved_references,
    write_revisions,
)
from grindstone.intent.render import render

__all__ = [
    "IntentError",
    "KindCatalog",
    "Materialised",
    "Proposal",
    "RevisionBatch",
    "Step",
    "allocate",
    "applying",
    "check_id",
    "current_hash",
    "derive_edges",
    "edges_to",
    "materialise",
    "read",
    "read_pinned",
    "render",
    "sync_lifecycle_states",
    "transition",
    "transition_allowed",
    "unresolved_references",
    "write_revisions",
]
