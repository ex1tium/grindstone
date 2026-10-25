"""SPEC-04, TKT-0401: items, revisions, edges, lifecycles, ID allocation and rendering."""

import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import JsonValue
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from grindstone.contracts.ids import ChangeSetId, ProjectId, RevisionId, new_record_id
from grindstone.contracts.intent import ItemRevision
from grindstone.contracts.platform import (
    Cardinality,
    FieldDecl,
    FieldType,
    IdDecl,
    KindDecl,
    Lifecycle,
)
from grindstone.contracts.provenance import AuthorKind, Provenance
from grindstone.intent import (
    IntentError,
    KindCatalog,
    Proposal,
    RevisionBatch,
    Step,
    allocate,
    applying,
    check_id,
    edges_to,
    materialise,
    read,
    render,
    sync_lifecycle_states,
    transition,
    transition_allowed,
    unresolved_references,
    write_revisions,
)
from grindstone.platform.core import CORE_KINDS
from grindstone.store import Database, Uow, unit_of_work

LIFECYCLE = Lifecycle.model_validate(
    {
        "states": ["draft", "final"],
        "initial": "draft",
        "transitions": [
            {"from": "draft", "to": "final", "writer": "changeset"},
            {"from": "final", "to": "draft", "writer": "task"},
        ],
    }
)

NOTE = KindDecl(
    name="notes.note",
    id=IdDecl(pattern="^N-[0-9]+$", examples=("N-1",)),
    fields={
        "body": FieldDecl(type=FieldType.TEXT),
        "summary": FieldDecl(type=FieldType.TEXT, presentation=True, required=False),
        "links": FieldDecl(
            type=FieldType.REF,
            kinds=("notes.note",),
            edge="notes.links",
            cardinality=Cardinality.MANY,
            required=False,
        ),
        "parent": FieldDecl(
            type=FieldType.REF, kinds=("notes.note",), edge="notes.child_of", required=False
        ),
    },
    lifecycle=LIFECYCLE,
)

CATALOG = KindCatalog.from_decls({NOTE.name: NOTE, **{k.name: k for k in CORE_KINDS}})
PROVENANCE = Provenance(author_kind=AuthorKind.PERSON, author="operator", reason="import")


def _note(item: str, body: str = "Proof.", **fields: JsonValue) -> Proposal:
    return Proposal(item, "notes.note", f"Note {item}", {"body": body, **fields})


def _apply(project: ProjectId, *proposals: Proposal) -> list[ItemRevision]:
    changeset = ChangeSetId(new_record_id())

    def work(uow: Uow) -> list[ItemRevision]:
        with applying(changeset):
            return write_revisions(
                uow, CATALOG, RevisionBatch(project, changeset, PROVENANCE, proposals)
            )

    return unit_of_work(work)


def _project() -> ProjectId:
    return ProjectId(new_record_id())


@pytest.fixture
def intent(store: Database) -> Database:
    unit_of_work(lambda uow: sync_lifecycle_states(uow, CATALOG))
    return store


def test_revisions_are_immutable_with_provenance(intent: Database, engine: Engine) -> None:
    project = _project()
    revision, _ = _apply(project, _note("N-1"), _note("N-2", links=["N-1"]))
    assert revision.provenance.reason == "import"
    for statement in (
        "UPDATE intent.item_revisions SET title = 'changed'",
        "DELETE FROM intent.item_revisions",
        "UPDATE intent.edges SET target = 'N-9'",
    ):
        with pytest.raises(DBAPIError, match="insert-only"), engine.begin() as conn:
            conn.execute(text(statement))
    with pytest.raises(DBAPIError, match="provenance"), engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO intent.item_revisions (id, project, item, kind, title, semantic,"
                " presentation, hash, provenance, changeset) VALUES (:id, :p, 'N-2', 'notes.note',"
                ' \'t\', \'{}\', \'{}\', :h, \'{"author_kind": "person", "author": "x",'
                ' "reason": ""}\', :c)'
            ),
            {"id": uuid.uuid4(), "p": project, "h": "sha256:" + "0" * 64, "c": uuid.uuid4()},
        )
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT provenance FROM intent.item_revisions")).scalars().all()
    assert all(p["author_kind"] and p["author"] and p["reason"] for p in rows)


def test_only_apply_writes_revisions(intent: Database) -> None:
    # FF-08's static check of the SQL (TKT-0405) covers the rest of AC-0402-1.
    project = _project()
    changeset = ChangeSetId(new_record_id())
    batch = RevisionBatch(project, changeset, PROVENANCE, (_note("N-1"),))
    for scope in (None, ChangeSetId(new_record_id())):

        def work(uow: Uow, scope: ChangeSetId | None = scope) -> None:
            if scope is None:
                write_revisions(uow, CATALOG, batch)
            else:
                with applying(scope):
                    write_revisions(uow, CATALOG, batch)

        with pytest.raises(IntentError) as caught:
            unit_of_work(work)
        assert caught.value.code == "invariant_violated"
    assert unit_of_work(lambda uow: read(uow, project, "N-1")) is None


def test_edges_derived_from_references(intent: Database) -> None:
    m = materialise(CATALOG, _note("N-3", links=["N-1", "N-2", "N-1"], parent="N-1"))
    assert m.edges == (("notes.links", "N-1"), ("notes.links", "N-2"), ("notes.child_of", "N-1"))

    project = _project()
    _apply(project, _note("N-1"), _note("N-2"))
    [first] = _apply(project, _note("N-3", links=["N-1"], parent="N-2"))
    [second] = _apply(project, _note("N-3", links=["N-2"], parent="N-2"))

    def edges(revision: RevisionId) -> set[tuple[str, str]]:
        def work(uow: Uow) -> set[tuple[str, str]]:
            rows = uow.fetch_all(
                "SELECT type, target FROM intent.edges WHERE revision = :r", {"r": revision}
            )
            return {(r["type"], r["target"]) for r in rows}

        return unit_of_work(work)

    assert edges(first.id) == {("notes.links", "N-1"), ("notes.child_of", "N-2")}
    assert edges(second.id) == {("notes.links", "N-2"), ("notes.child_of", "N-2")}
    current = unit_of_work(lambda uow: edges_to(uow, project, "N-1"))
    assert current == []  # N-3's current revision no longer links N-1


def test_unresolved_reference_refused() -> None:
    def exists_in_project(item: str) -> bool:
        return item == "N-1"

    citing = materialise(CATALOG, _note("N-3", links=["N-1", "N-9"]))
    [problem] = unresolved_references([citing], exists_in_project)
    assert problem.code == "reference_unresolved"
    assert problem.envelope.detail == {"item": "N-3", "edge": "notes.links", "target": "N-9"}
    created = materialise(CATALOG, _note("N-9"))
    assert unresolved_references([citing, created], exists_in_project) == []


STATES = st.sampled_from([None, "draft", "final", "archived"])
WRITERS = st.sampled_from(["changeset", "task", "evidence", "delivery"])


@given(STATES, STATES.filter(lambda s: s is not None), WRITERS)
def test_lifecycle_transitions_guarded(current: str | None, to: str | None, writer: str) -> None:
    assert to is not None
    listed = {("draft", "final", "changeset"), ("final", "draft", "task")}
    expected = (
        (to == "draft" and writer == "changeset")
        if current is None
        else (current, to, writer) in listed
    )
    assert transition_allowed(LIFECYCLE, current, to, writer) is expected


def test_transitions_are_recorded_and_never_hashed(intent: Database, engine: Engine) -> None:
    project = _project()
    [revision] = _apply(project, _note("N-1"))
    cause = str(uuid.uuid4())

    def step(to: str, writer: str) -> Callable[[Uow], object]:
        return lambda uow: transition(uow, CATALOG, Step(project, "N-1", to, writer, cause))

    unit_of_work(step("final", "changeset"))
    for to, writer in (("final", "changeset"), ("draft", "changeset"), ("draft", "evidence")):
        with pytest.raises(IntentError) as caught:
            unit_of_work(step(to, writer))
        assert caught.value.code == "transition_illegal"
    unit_of_work(step("draft", "task"))
    current = unit_of_work(lambda uow: read(uow, project, "N-1"))
    assert current is not None
    assert current.hash == revision.hash
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT from_state, to_state, writer, cause FROM intent.lifecycle_transitions"
                " WHERE project = :p ORDER BY id"
            ),
            {"p": project},
        ).all()
    assert [tuple(r) for r in rows] == [
        (None, "draft", "changeset", rows[0].cause),
        ("draft", "final", "changeset", cause),
        ("final", "draft", "task", cause),
    ]


def test_initial_state_on_apply(intent: Database, engine: Engine) -> None:
    project = _project()
    _apply(project, _note("N-1"), _note("N-2"))
    with engine.connect() as conn:
        states = conn.execute(
            text("SELECT id, lifecycle_state FROM intent.items WHERE project = :p ORDER BY id"),
            {"p": project},
        ).all()
    assert [tuple(r) for r in states] == [("N-1", "draft"), ("N-2", "draft")]


def test_id_allocation_and_validation(intent: Database) -> None:
    project = _project()

    def one(_: int) -> str:
        return unit_of_work(lambda uow: allocate(uow, CATALOG, project, "core.finding"))

    with ThreadPoolExecutor(4) as pool:
        ids = list(pool.map(one, range(8)))
    numbers = sorted(int(i.removeprefix("FND-")) for i in ids)
    assert numbers == list(range(1, 9))

    with pytest.raises(IntentError) as caught:
        unit_of_work(lambda uow: check_id(uow, CATALOG, project, "core.finding", "FND-x"))
    assert caught.value.code == "id_invalid"
    _apply(project, _note("N-1"))
    with pytest.raises(IntentError) as caught:
        unit_of_work(lambda uow: check_id(uow, CATALOG, project, "core.principle", "N-1"))
    assert caught.value.code in {"id_invalid", "id_taken"}

    imported = _project()
    finding = Proposal(
        "FND-7",
        "core.finding",
        "Imported",
        {
            "type": "gap",
            "severity": "low",
            "trust": "trusted",
            "description": "From a bundle.",
            "about": [],
        },
    )
    _apply(imported, finding)
    allocated = [
        unit_of_work(lambda uow: allocate(uow, CATALOG, imported, "core.finding")) for _ in range(8)
    ]
    assert "FND-7" not in allocated
    assert allocated == [f"FND-{n}" for n in (1, 2, 3, 4, 5, 6, 8, 9)]


def test_id_taken_by_another_kind(intent: Database) -> None:
    project = _project()
    taken = KindDecl(
        name="notes.memo", id=IdDecl(pattern="^N-[0-9]+$", examples=("N-1",)), fields={}
    )
    catalog = KindCatalog.from_decls({NOTE.name: NOTE, taken.name: taken})
    _apply(project, _note("N-1"))
    with pytest.raises(IntentError) as caught:
        unit_of_work(lambda uow: check_id(uow, catalog, project, "notes.memo", "N-1"))
    assert caught.value.code == "id_taken"


def test_render_item_markdown() -> None:
    m = materialise(CATALOG, _note("N-3", "Grindstone proves work.", links=["N-1", "N-2"]))
    revision = ItemRevision(
        id=RevisionId(new_record_id()),
        project=_project(),
        item="N-3",
        kind="notes.note",
        title="Opening paragraph",
        semantic=m.semantic,
        presentation=m.presentation,
        hash=m.hash,
        parent=None,
        provenance=PROVENANCE,
        changeset=ChangeSetId(new_record_id()),
    )
    markdown = render(revision, CATALOG)
    assert "Generated from the ledger, which is the source of truth" in markdown
    assert "# N-3 — Opening paragraph" in markdown
    assert "Grindstone proves work." in markdown
    assert "[[N-1]] [[N-2]]" in markdown
