"""Items as the ledger holds them: revisions, edges, bundles, lifecycle transitions (SPEC-04).

A revision is immutable and carries its semantic and presentation fields
separately, its semantic hash, its parent and its provenance (I-02). Edges are
derived from a revision's typed reference fields when it is written, never
edited on their own (ADR-09). Lifecycle state lives beside the item and is
never part of a revision or its hash.
"""

from datetime import datetime
from typing import Literal

from pydantic import Field, JsonValue

from grindstone.contracts.base import Contract
from grindstone.contracts.ids import ChangeSetId, ItemId, ProjectId, RevisionId
from grindstone.contracts.provenance import Provenance
from grindstone.contracts.refs import SemanticHash


class ItemRevision(Contract):
    """One immutable revision of an item."""

    schema_version: Literal[1] = 1
    id: RevisionId
    project: ProjectId
    item: ItemId
    kind: str
    title: str
    semantic: dict[str, JsonValue]
    presentation: dict[str, JsonValue]
    hash: SemanticHash
    parent: RevisionId | None
    provenance: Provenance
    changeset: ChangeSetId


class Edge(Contract):
    """A typed link from one revision's item to another item, derived from a reference field."""

    schema_version: Literal[1] = 1
    revision: RevisionId
    source: ItemId
    type: str
    target: ItemId


class BundleItem(Contract):
    kind: str
    id: ItemId
    title: str
    fields: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])


class ItemBundle(Contract):
    """Hand-written items imported as one ChangeDraft (DEC-0401)."""

    schema_version: Literal[1] = 1
    items: tuple[BundleItem, ...]


class LifecycleTransition(Contract):
    """One recorded change of an item's lifecycle state, with its writer and cause."""

    schema_version: Literal[1] = 1
    project: ProjectId
    item: ItemId
    kind: str
    from_state: str | None
    to_state: str
    writer: Literal["changeset", "task", "evidence", "delivery"]
    cause: str
    """The ChangeSet, task, evidence or delivery ID that caused it."""
    at: datetime


# Events.


class ItemRevised(Contract):
    """A ChangeSet's apply wrote a new revision of an item."""

    schema_version: Literal[1] = 1
    type: Literal["item.revised"] = "item.revised"
    item: ItemId
    kind: str
    revision: RevisionId
    hash: SemanticHash
    changeset: ChangeSetId


class ItemTransitioned(Contract):
    """An item's lifecycle state changed."""

    schema_version: Literal[1] = 1
    type: Literal["item.transitioned"] = "item.transitioned"
    item: ItemId
    kind: str
    from_state: str | None
    to_state: str
    writer: Literal["changeset", "task", "evidence", "delivery"]
    cause: str
