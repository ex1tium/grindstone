"""Items, immutable revisions, derived edges, lifecycles and ID allocation (SPEC-04).

Only ChangeSet apply writes revisions (I-01, REQ-0402): `write_revisions`
refuses unless the caller holds `applying(changeset)` for the ChangeSet it
writes. Edges are derived from typed reference fields as each revision is
written (REQ-0403). Lifecycle state lives beside the item and changes only
through `transition`, which records every change with its writer and cause
(REQ-0405); state never enters a revision, so it never changes a hash.
"""

import json
import re
from collections.abc import Callable, Generator, Iterable, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, cast

from pydantic import JsonValue, TypeAdapter, ValidationError

from grindstone.contracts.base import Contract, Presentation
from grindstone.contracts.hashing import semantic_hash
from grindstone.contracts.ids import (
    ChangeSetId,
    ItemId,
    ProjectId,
    RevisionId,
    item_id_type,
    new_record_id,
)
from grindstone.contracts.intent import Edge, ItemRevision, LifecycleTransition
from grindstone.contracts.platform import Cardinality, Lifecycle
from grindstone.contracts.provenance import Provenance
from grindstone.contracts.refs import ItemRef, SemanticHash
from grindstone.intent.catalog import KindCatalog
from grindstone.intent.errors import IntentError
from grindstone.store import Uow

type Writer = str
"""A lifecycle writer: `changeset`, `task`, `evidence` or `delivery` (SPEC-04)."""


@dataclass(frozen=True, slots=True)
class Proposal:
    """A revision as a ChangeSet proposes it: the item's kind, ID, title and fields."""

    item: ItemId
    kind: str
    title: str
    fields: Mapping[str, JsonValue]


@dataclass(frozen=True, slots=True)
class Materialised:
    """A proposal validated against its kind and split into what is hashed and what is not."""

    proposal: Proposal
    semantic: dict[str, JsonValue]
    presentation: dict[str, JsonValue]
    hash: SemanticHash
    edges: tuple[tuple[str, ItemId], ...]
    """(edge type, target) pairs derived from the reference fields."""


def materialise(catalog: KindCatalog, proposal: Proposal) -> Materialised:
    """Validate a proposal against its compiled kind; raises pydantic's `ValidationError`."""
    model = catalog.model(proposal.kind)
    instance = model.model_validate({**proposal.fields, "title": proposal.title})
    dumped = cast(dict[str, JsonValue], instance.model_dump(mode="json"))
    presentation_names = {
        name
        for name, field in model.model_fields.items()
        if any(m is Presentation for m in field.metadata)
    }
    return Materialised(
        proposal=proposal,
        semantic={k: v for k, v in dumped.items() if k not in presentation_names},
        presentation={k: v for k, v in dumped.items() if k in presentation_names},
        hash=semantic_hash(instance),
        edges=derive_edges(catalog, proposal.kind, instance),
    )


def derive_edges(
    catalog: KindCatalog, kind: str, instance: Contract
) -> tuple[tuple[str, ItemId], ...]:
    """One edge per referenced ID, typed by its field's edge, in field then value order."""
    edges: list[tuple[str, ItemId]] = []
    for name, field in catalog.ref_fields(kind):
        value: object = getattr(instance, name)
        if value is None or field.edge is None:
            continue
        many = isinstance(value, tuple) or field.cardinality is Cardinality.MANY
        targets = cast(tuple[ItemId, ...], value) if many else (cast(ItemId, value),)
        edges.extend((field.edge, target) for target in targets)
    return tuple(dict.fromkeys(edges))


def unresolved_references(
    materialised: Iterable[Materialised], exists: Callable[[ItemId], bool]
) -> list[IntentError]:
    """Each reference to an item neither in the project nor created alongside (REQ-0404)."""
    batch = list(materialised)
    created = {m.proposal.item for m in batch}
    problems: list[IntentError] = []
    for m in batch:
        for edge, target in m.edges:
            if target not in created and not exists(target):
                problems.append(
                    IntentError(
                        "reference_unresolved",
                        f"{m.proposal.item}: {target!r} ({edge}) is not in the project or batch",
                        item=m.proposal.item,
                        edge=edge,
                        target=target,
                    )
                )
    return problems


@dataclass(frozen=True, slots=True)
class RevisionBatch:
    """What one ChangeSet's apply writes: its proposals, under one provenance."""

    project: ProjectId
    changeset: ChangeSetId
    provenance: Provenance
    proposals: Sequence[Proposal]


@dataclass(frozen=True, slots=True)
class Step:
    """A requested lifecycle step: an item, the state to enter, its writer and cause."""

    project: ProjectId
    item: ItemId
    to: str
    writer: Writer
    cause: str
    """The ChangeSet, task, evidence or delivery ID behind the step."""


_applying: ContextVar[ChangeSetId | None] = ContextVar("applying", default=None)


@contextmanager
def applying(changeset: ChangeSetId) -> Generator[None]:
    """Mark the apply of one ChangeSet; only inside it may revisions be written (REQ-0402)."""
    token = _applying.set(changeset)
    try:
        yield
    finally:
        _applying.reset(token)


def write_revisions(uow: Uow, catalog: KindCatalog, batch: RevisionBatch) -> list[ItemRevision]:
    """Write one revision per proposal, its edges and the item's current pointer.

    New items enter their kind's initial lifecycle state (REQ-0406). The
    caller has fixed every ID and checked every base; references must resolve
    within the project or the batch.
    """
    project, changeset, provenance = batch.project, batch.changeset, batch.provenance
    if _applying.get() != changeset:
        raise IntentError(
            "invariant_violated",
            "revisions are written only inside the apply of their ChangeSet (I-01)",
            changeset=str(changeset),
        )
    materialised = [materialise(catalog, p) for p in batch.proposals]
    unresolved = unresolved_references(materialised, lambda item: _exists(uow, project, item))
    if unresolved:
        raise unresolved[0]
    revisions: list[ItemRevision] = []
    for m in materialised:
        p = m.proposal
        current = uow.fetch_one(
            "SELECT kind, current_revision FROM intent.items WHERE project = :project AND id = :id",
            {"project": project, "id": p.item},
        )
        if current is not None and current["kind"] != p.kind:
            raise IntentError(
                "id_taken", f"{p.item} is a {current['kind']}, not a {p.kind}", item=p.item
            )
        revision = ItemRevision(
            id=RevisionId(new_record_id()),
            project=project,
            item=p.item,
            kind=p.kind,
            title=p.title,
            semantic=m.semantic,
            presentation=m.presentation,
            hash=m.hash,
            parent=None if current is None else current["current_revision"],
            provenance=provenance,
            changeset=changeset,
        )
        uow.execute(
            "INSERT INTO intent.item_revisions"
            " (id, project, item, kind, title, semantic, presentation, hash, parent,"
            " provenance, changeset)"
            " VALUES (:id, :project, :item, :kind, :title, CAST(:semantic AS jsonb),"
            " CAST(:presentation AS jsonb), :hash, :parent, CAST(:provenance AS jsonb),"
            " :changeset)",
            {
                "id": revision.id,
                "project": project,
                "item": p.item,
                "kind": p.kind,
                "title": p.title,
                "semantic": json.dumps(m.semantic),
                "presentation": json.dumps(m.presentation),
                "hash": m.hash,
                "parent": revision.parent,
                "provenance": provenance.model_dump_json(),
                "changeset": changeset,
            },
        )
        for edge_type, target in m.edges:
            uow.execute(
                "INSERT INTO intent.edges (revision, project, source, type, target)"
                " VALUES (:revision, :project, :source, :type, :target)",
                {
                    "revision": revision.id,
                    "project": project,
                    "source": p.item,
                    "type": edge_type,
                    "target": target,
                },
            )
        if current is None:
            uow.execute(
                "INSERT INTO intent.items (project, id, kind, current_revision)"
                " VALUES (:project, :id, :kind, :revision)",
                {"project": project, "id": p.item, "kind": p.kind, "revision": revision.id},
            )
            lifecycle = catalog.decl(p.kind).lifecycle
            if lifecycle is not None:
                step = Step(project, p.item, lifecycle.initial, "changeset", str(changeset))
                transition(uow, catalog, step)
        else:
            uow.execute(
                "UPDATE intent.items SET current_revision = :revision"
                " WHERE project = :project AND id = :id",
                {"project": project, "id": p.item, "revision": revision.id},
            )
        revisions.append(revision)
    return revisions


def _exists(uow: Uow, project: ProjectId, item: ItemId) -> bool:
    return (
        uow.fetch_one(
            "SELECT 1 FROM intent.items WHERE project = :project AND id = :id",
            {"project": project, "id": item},
        )
        is not None
    )


def _revision(row: Mapping[Any, Any]) -> ItemRevision:
    return ItemRevision.model_validate(dict(row))


_REVISION_COLUMNS = (
    "r.id, r.project, r.item, r.kind, r.title, r.semantic, r.presentation, r.hash, r.parent,"
    " r.provenance, r.changeset"
)


def read(uow: Uow, project: ProjectId, item: ItemId) -> ItemRevision | None:
    """An item's current revision, or None if the project has no such item."""
    row = uow.fetch_one(
        f"SELECT {_REVISION_COLUMNS} FROM intent.items i"  # noqa: S608 - fixed column list
        " JOIN intent.item_revisions r ON r.id = i.current_revision"
        " WHERE i.project = :project AND i.id = :id",
        {"project": project, "id": item},
    )
    return None if row is None else _revision(row)


def read_pinned(uow: Uow, project: ProjectId, ref: ItemRef) -> ItemRevision | None:
    """The revision of `ref.id` whose hash is `ref.hash`, current or not.

    Takes a project because equal content hashes equally in two projects;
    a context binds its project, so the port that wraps this is unchanged.
    """
    row = uow.fetch_one(
        f"SELECT {_REVISION_COLUMNS} FROM intent.item_revisions r"  # noqa: S608 - fixed column list
        " WHERE r.project = :project AND r.item = :id AND r.hash = :hash"
        " ORDER BY r.created_at DESC LIMIT 1",
        {"project": project, "id": ref.id, "hash": ref.hash},
    )
    return None if row is None else _revision(row)


def current_hash(uow: Uow, project: ProjectId, item: ItemId) -> SemanticHash | None:
    revision = read(uow, project, item)
    return None if revision is None else revision.hash


def edges_to(uow: Uow, project: ProjectId, target: ItemId) -> list[Edge]:
    """The edges of current revisions that point at `target`."""
    rows = uow.fetch_all(
        "SELECT e.revision, e.source, e.type, e.target FROM intent.edges e"
        " JOIN intent.items i ON i.current_revision = e.revision"
        " WHERE e.project = :project AND e.target = :target ORDER BY e.source, e.type",
        {"project": project, "target": target},
    )
    return [Edge.model_validate(dict(r)) for r in rows]


def check_id(uow: Uow, catalog: KindCatalog, project: ProjectId, kind: str, item: str) -> None:
    """Refuse an ID not matching its kind (`id_invalid`) or held by another kind (`id_taken`)."""
    decl = catalog.decl(kind)
    try:
        TypeAdapter(item_id_type(kind, decl.id.pattern, ())).validate_python(item)
    except ValidationError:
        raise IntentError(
            "id_invalid", f"{item!r} does not match {kind}'s pattern {decl.id.pattern}", item=item
        ) from None
    row = uow.fetch_one(
        "SELECT kind FROM intent.items WHERE project = :project AND id = :id",
        {"project": project, "id": item},
    )
    if row is not None and row["kind"] != kind:
        raise IntentError("id_taken", f"{item} is already a {row['kind']}", item=item)


_ALLOCATION = re.compile(r"^(?P<prefix>[A-Z][A-Z0-9]*-)\{n\}$")


def allocate(uow: Uow, catalog: KindCatalog, project: ProjectId, kind: str) -> ItemId:
    """The next unused ID for a kind that declares an allocation format (REQ-0407).

    Numbers are never reused and numbers already taken in the project,
    imported ones included, are skipped.
    """
    decl = catalog.decl(kind)
    match = _ALLOCATION.match(decl.id.allocate or "")
    if match is None:
        raise IntentError("id_invalid", f"{kind} does not allocate IDs", kind=kind)
    prefix = match["prefix"]
    row = uow.fetch_one(
        "INSERT INTO intent.id_counters (project, prefix, next) VALUES (:project, :prefix, 1)"
        " ON CONFLICT (project, prefix) DO UPDATE SET next = intent.id_counters.next"
        " RETURNING next",
        {"project": project, "prefix": prefix},
    )
    number = int(row["next"]) if row is not None else 1
    while _exists(uow, project, f"{prefix}{number}"):
        number += 1
    uow.execute(
        "UPDATE intent.id_counters SET next = :next WHERE project = :project AND prefix = :prefix",
        {"project": project, "prefix": prefix, "next": number + 1},
    )
    return f"{prefix}{number}"


def transition(uow: Uow, catalog: KindCatalog, step: Step) -> LifecycleTransition:
    """Move an item to `to`, if its kind's table lists that step for this writer (REQ-0405).

    The one writer of `intent.items.lifecycle_state`. From no state, only the
    kind's initial state may be entered, by `changeset` (REQ-0406).
    """
    project, item, to, writer = step.project, step.item, step.to, step.writer
    row = uow.fetch_one(
        "SELECT kind, lifecycle_state FROM intent.items"
        " WHERE project = :project AND id = :id FOR UPDATE",
        {"project": project, "id": item},
    )
    if row is None:
        raise IntentError("reference_unresolved", f"{item} does not exist", item=item)
    kind = str(row["kind"])
    current = cast(str | None, row["lifecycle_state"])
    lifecycle = catalog.decl(kind).lifecycle
    if lifecycle is None or not transition_allowed(lifecycle, current, to, writer):
        raise IntentError(
            "transition_illegal",
            f"{item}: {current or 'no state'} → {to} by {writer} is not in {kind}'s lifecycle",
            item=item,
            to=to,
            writer=writer,
        )
    uow.execute(
        "UPDATE intent.items SET lifecycle_state = :to WHERE project = :project AND id = :id",
        {"project": project, "id": item, "to": to},
    )
    recorded = uow.fetch_one(
        "INSERT INTO intent.lifecycle_transitions"
        " (project, item, kind, from_state, to_state, writer, cause)"
        " VALUES (:project, :item, :kind, :from, :to, :writer, :cause) RETURNING at",
        {
            "project": project,
            "item": item,
            "kind": kind,
            "from": current,
            "to": to,
            "writer": writer,
            "cause": step.cause,
        },
    )
    return LifecycleTransition.model_validate(
        {
            "project": project,
            "item": item,
            "kind": kind,
            "from_state": current,
            "to_state": to,
            "writer": writer,
            "cause": step.cause,
            "at": recorded["at"] if recorded is not None else None,
        }
    )


def transition_allowed(lifecycle: Lifecycle, current: str | None, to: str, writer: Writer) -> bool:
    """Whether a kind's lifecycle table admits this step by this writer."""
    if current is None:
        return to == lifecycle.initial and writer == "changeset"
    return any(
        t.source == current and t.to == to and t.writer == writer for t in lifecycle.transitions
    )


def sync_lifecycle_states(uow: Uow, catalog: KindCatalog) -> None:
    """Rewrite `intent.lifecycle_states` from the registries at start-up (DEC-0405).

    A state that items still hold but no loaded kind declares any longer is
    refused, naming the state and how many items hold it.
    """
    declared = {
        (kind, state)
        for kind, decl in catalog.decls.items()
        if decl.lifecycle is not None
        for state in decl.lifecycle.states
    }
    held = uow.fetch_all(
        "SELECT kind, lifecycle_state AS state, count(*) AS n FROM intent.items"
        " WHERE lifecycle_state IS NOT NULL GROUP BY kind, lifecycle_state"
    )
    for row in held:
        if (row["kind"], row["state"]) not in declared:
            raise IntentError(
                "manifest_invalid",
                f"{row['kind']} no longer declares {row['state']!r}, which {row['n']} items hold",
                kind=str(row["kind"]),
                state=str(row["state"]),
            )
    existing = {
        (r["kind"], r["state"])
        for r in uow.fetch_all("SELECT kind, state FROM intent.lifecycle_states")
    }
    for kind, state in sorted(declared - existing):
        uow.execute(
            "INSERT INTO intent.lifecycle_states (kind, state) VALUES (:kind, :state)",
            {"kind": kind, "state": state},
        )
    for kind, state in sorted(existing - declared):
        uow.execute(
            "DELETE FROM intent.lifecycle_states WHERE kind = :kind AND state = :state",
            {"kind": kind, "state": state},
        )
