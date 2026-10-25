"""SPEC-09, TKT-0901: the `sdlc` kinds in the kernel's ledger (integration, PostgreSQL).

The testbed's fixture intent (REQ-0101, AC-0101-1, TKT-0001) is written here
through the kernel's apply path for revisions (SPEC-04). The bundle file and
its import are TKT-0905's and TKT-0403's; template runs, check plans and
evidence freshness are TKT-0601's and TKT-0801's. Until those land, these
tests read the template's declared inputs and check targets, and the edges'
check dependencies, against the ledger with the helpers in `support`.
"""

from collections.abc import Iterable
from typing import cast

import pytest
from factories.sdlc.tests.support import refused, selection, step_inputs, task_step
from pydantic import JsonValue
from sqlalchemy import Engine, text

from grindstone.contracts.ids import ChangeSetId, ItemId, ProjectId, new_record_id
from grindstone.contracts.intent import ItemRevision
from grindstone.contracts.platform import CapabilityDecl, EdgeDecl, OfferMode, TaskMode
from grindstone.contracts.provenance import AuthorKind, Provenance
from grindstone.contracts.refs import SemanticHash
from grindstone.intent import (
    KindCatalog,
    Proposal,
    RevisionBatch,
    applying,
    read,
    sync_lifecycle_states,
    write_revisions,
)
from grindstone.platform import Category, Registries
from grindstone.platform.loader import LoadedFactory
from grindstone.store import Database, Uow, unit_of_work

pytestmark = pytest.mark.integration

type Loaded = tuple[Registries, LoadedFactory]

PROVENANCE = Provenance(author_kind=AuthorKind.PERSON, author="operator", reason="import")

SLUGS = (
    "`testbed.text.slugify(title)` returns a URL slug: lowercase ASCII letters and digits,"
    " words joined by single hyphens, no leading or trailing hyphen."
)


def _requirement(statement: str = SLUGS) -> Proposal:
    return Proposal(
        "REQ-0101",
        "sdlc.requirement",
        "Slugs for titles",
        {"statement": statement, "priority": "must"},
    )


def _criterion(item: str = "AC-0101-1", method: str = "test") -> Proposal:
    condition = (
        'slugify("Grindstone: Proof, Not Promises!") returns "grindstone-proof-not-promises"'
    )
    return Proposal(
        item,
        "sdlc.criterion",
        "Slugify examples",
        {"condition": condition, "method": method, "verifies": "REQ-0101"},
    )


def _ticket(goal: str = "Add slugify to testbed.text so that AC-0101-1 holds.") -> Proposal:
    return Proposal(
        "TKT-0001",
        "sdlc.ticket",
        "Implement slugify",
        {
            "goal": goal,
            "declared_paths": ["src/testbed/text.py", "tests/test_text.py"],
            "estimate": "small",
            "implements": ["REQ-0101"],
        },
    )


def _bundle() -> tuple[Proposal, ...]:
    """The testbed's fixture intent, as SPEC-09 lists it for `TKT-0001.bundle.yaml`."""
    return (_requirement(), _criterion(), _ticket())


@pytest.fixture
def ledger(store: Database, loaded: Loaded) -> KindCatalog:
    """The store with the `sdlc` kinds' lifecycle states synchronised."""
    registries, _ = loaded
    catalog = KindCatalog.from_registries(registries)
    unit_of_work(lambda uow: sync_lifecycle_states(uow, catalog))
    return catalog


def _project() -> ProjectId:
    return ProjectId(new_record_id())


def _apply(catalog: KindCatalog, project: ProjectId, *proposals: Proposal) -> list[ItemRevision]:
    changeset = ChangeSetId(new_record_id())

    def work(uow: Uow) -> list[ItemRevision]:
        with applying(changeset):
            batch = RevisionBatch(project, changeset, PROVENANCE, proposals)
            return write_revisions(uow, catalog, batch)

    return unit_of_work(work)


def _edges(
    uow: Uow, project: ProjectId, edge: str, ends: Iterable[ItemId], *, inverted: bool
) -> set[ItemId]:
    """The items one edge type reaches from `ends`, among current revisions."""
    near, far = ("target", "source") if inverted else ("source", "target")
    rows = uow.fetch_all(
        f"SELECT e.{far} AS item FROM intent.edges e"  # noqa: S608 - fixed column names
        " JOIN intent.items i ON i.current_revision = e.revision"
        f" WHERE e.project = :project AND e.type = :type AND e.{near} = ANY(:ends)",
        {"project": project, "type": edge, "ends": sorted(ends)},
    )
    return {cast(ItemId, r["item"]) for r in rows}


def _pinned_inputs(
    factory: LoadedFactory, project: ProjectId, ticket: str
) -> dict[str, ItemRevision]:
    """The `implement` step's input closure from `ticket`, each at its current revision."""
    inputs = step_inputs(task_step(factory, "sdlc.implement", "implement"))
    assert inputs.start == "args.ticket"

    def work(uow: Uow) -> dict[str, ItemRevision]:
        reached: set[ItemId] = {ticket}
        frontier: set[ItemId] = {ticket}
        for edge, inverted in inputs.follow:
            frontier = _edges(uow, project, edge, frontier, inverted=inverted)
            reached |= frontier
        revisions = {item: read(uow, project, item) for item in sorted(reached)}
        return {item: r for item, r in revisions.items() if r is not None}

    return unit_of_work(work)


def _check_inputs(
    registries: Registries, project: ProjectId, target: ItemId
) -> dict[ItemId, SemanticHash]:
    """SPEC-08's evidence inputs for a check target (REQ-0802): its hash and the hashes of
    the items its check-dependency edges reach in one hop."""
    dependencies = {
        name
        for name in registries.names(Category.EDGE)
        if cast(EdgeDecl, registries.require(Category.EDGE, name).value).check_dependency
    }

    def work(uow: Uow) -> dict[ItemId, SemanticHash]:
        items: set[ItemId] = {target}
        for edge in dependencies:
            items |= _edges(uow, project, edge, {target}, inverted=False)
        found = {item: read(uow, project, item) for item in items}
        return {item: r.hash for item, r in found.items() if r is not None}

    return unit_of_work(work)


def test_initial_sdlc_states(ledger: KindCatalog, engine: Engine) -> None:
    """AC-0903-1: applying the testbed bundle leaves REQ-0101 `approved` and TKT-0001 `ready`."""
    project = _project()
    _apply(ledger, project, *_bundle())
    with engine.connect() as conn:
        states = conn.execute(
            text("SELECT id, lifecycle_state FROM intent.items WHERE project = :p ORDER BY id"),
            {"p": project},
        ).all()
        writers = conn.execute(
            text("SELECT DISTINCT writer FROM intent.lifecycle_transitions WHERE project = :p"),
            {"p": project},
        ).all()
    assert [tuple(r) for r in states] == [
        ("AC-0101-1", None),
        ("REQ-0101", "approved"),
        ("TKT-0001", "ready"),
    ]
    assert [tuple(r) for r in writers] == [("changeset",)]


def test_requirement_change_stales_criterion_evidence(ledger: KindCatalog, loaded: Loaded) -> None:
    """AC-0902-1: after a ChangeSet changes REQ-0101's statement, the evidence inputs captured
    for AC-0101-1 no longer match, naming REQ-0101; a ticket edit changes none of them."""
    registries, _ = loaded
    project = _project()
    _apply(ledger, project, *_bundle())
    captured = _check_inputs(registries, project, "AC-0101-1")
    assert set(captured) == {"AC-0101-1", "REQ-0101"}

    _apply(ledger, project, _ticket("Add slugify, reworded."))
    assert _check_inputs(registries, project, "AC-0101-1") == captured  # DEC-0907

    _apply(ledger, project, _requirement(SLUGS + " Diacritics map to their base letter."))
    current = _check_inputs(registries, project, "AC-0101-1")
    stale = sorted(item for item, value in captured.items() if current.get(item) != value)
    assert stale == ["REQ-0101"]


def test_implement_pins_ticket_closure(ledger: KindCatalog, loaded: Loaded) -> None:
    """AC-0904-1: `/implement TKT-0001` pins TKT-0001, REQ-0101 and AC-0101-1 at their
    current hashes, for one task with need `sdlc.implement`."""
    _, factory = loaded
    project = _project()
    written = {r.item: r for r in _apply(ledger, project, *_bundle())}
    # An unrelated criterion of another requirement stays out of the closure.
    _apply(
        ledger,
        project,
        Proposal(
            "REQ-0102", "sdlc.requirement", "Word count", {"statement": "s", "priority": "must"}
        ),
        Proposal(
            "AC-0102-1",
            "sdlc.criterion",
            "Word count examples",
            {"condition": "c", "method": "test", "verifies": "REQ-0102"},
        ),
    )
    template = next(t for t in factory.manifest.templates if t.name == "sdlc.implement")
    tasks = [s for s in template.steps if s.type == "task"]
    assert [(s.need, s.mode) for s in tasks] == [("sdlc.implement", TaskMode.WORK)]

    pinned = _pinned_inputs(factory, project, "TKT-0001")
    refs = {(r.item, r.hash) for r in pinned.values()}
    assert refs == {(i, written[i].hash) for i in ("TKT-0001", "REQ-0101", "AC-0101-1")}
    fields: dict[str, tuple[str, dict[str, JsonValue]]] = {
        item: (r.kind, dict(r.semantic)) for item, r in pinned.items()
    }
    assert refused(step_inputs(tasks[0]), fields) == []


def test_implement_check_plan(ledger: KindCatalog, loaded: Loaded) -> None:
    """AC-0905-1: the plan has a required `sdlc.ci_suite` check targeting AC-0101-1 and a
    required review by `sdlc.review.tests` targeting it, resolved to `sdlc.test_reviewer`."""
    registries, factory = loaded
    project = _project()
    _apply(ledger, project, *_bundle(), _criterion("AC-0101-2", method="review"))
    pinned = _pinned_inputs(factory, project, "TKT-0001")
    step = task_step(factory, "sdlc.implement", "implement")

    def targets(spec: tuple[str, ...]) -> list[str]:
        chosen = [selection(s) for s in spec]
        return sorted(
            item for item, r in pinned.items() if any(s.matches(r.kind, r.semantic) for s in chosen)
        )

    ci, review = step.checks
    assert (ci.method, ci.by, ci.required) == ("sdlc.ci_suite", "station", True)
    assert targets(ci.targets) == ["AC-0101-1"]
    assert (review.method, review.required) == ("sdlc.review", True)
    assert targets(review.targets) == ["AC-0101-1", "AC-0101-2"]

    # Matching (SPEC-06 part 2, REQ-0603): the capabilities offering the need in check mode.
    provers = [
        name
        for name in registries.names(Category.CAPABILITY)
        if any(
            o.need == review.by and OfferMode.CHECK in o.modes
            for o in cast(
                CapabilityDecl, registries.require(Category.CAPABILITY, name).value
            ).offers
        )
    ]
    assert provers == ["sdlc.test_reviewer"]
