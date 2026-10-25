"""SPEC-04, TKT-0403: bundle import, ChangeDrafts, walk, rules, approval and apply."""

import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
import yaml
from dbos import DBOS, SetWorkflowID
from hypothesis import given
from hypothesis import strategies as st
from pydantic import JsonValue
from sqlalchemy import Engine, text

import grindstone.change.changesets as module
from grindstone.change import (
    APPLY,
    APPROVAL_KIND,
    BundleImport,
    ChangeError,
    ChangeSets,
    DraftRequest,
    Rules,
    apply_changeset,
    install,
    latest_round,
    missing_verdicts,
    reach,
    read_changeset,
    read_draft,
)
from grindstone.contracts.change import (
    ApprovalPayload,
    ChangeSet,
    ChangeSetState,
    DraftSource,
    ProposedRevision,
    Trust,
    Verdict,
    WalkResult,
)
from grindstone.contracts.decisions import Channel, Decision, DecisionFlag, DecisionState
from grindstone.contracts.ids import ItemId, ProjectId, RevisionId
from grindstone.contracts.intent import Edge
from grindstone.contracts.platform import (
    Cardinality,
    FieldDecl,
    FieldType,
    IdDecl,
    Impact,
    KindDecl,
    Lifecycle,
)
from grindstone.contracts.provenance import AuthorKind, Provenance
from grindstone.decisions import (
    AnswerRequest,
    DecisionError,
    Decisions,
    open_decisions,
    register_continuation,
    registered_continuations,
)
from grindstone.decisions import read as read_decision
from grindstone.intent import IntentError, KindCatalog, read, sync_lifecycle_states
from grindstone.platform import core_registries
from grindstone.platform.core import CORE_KINDS
from grindstone.platform.events import events_after
from grindstone.store import Database, Uow, unit_of_work

LIFECYCLE = Lifecycle.model_validate(
    {
        "states": ["draft", "final"],
        "initial": "draft",
        "transitions": [{"from": "draft", "to": "final", "writer": "changeset"}],
    }
)

NOTE = KindDecl(
    name="notes.note",
    id=IdDecl(pattern="^N-[0-9]+$", examples=("N-1",)),
    fields={
        "body": FieldDecl(type=FieldType.TEXT),
        "links": FieldDecl(
            type=FieldType.REF,
            kinds=("notes.note",),
            edge="notes.links",
            cardinality=Cardinality.MANY,
            required=False,
        ),
        "mentions": FieldDecl(
            type=FieldType.REF,
            kinds=("notes.note",),
            edge="notes.mentions",
            cardinality=Cardinality.MANY,
            required=False,
        ),
    },
    lifecycle=LIFECYCLE,
)

CATALOG = KindCatalog.from_decls({NOTE.name: NOTE, **{k.name: k for k in CORE_KINDS}})
IMPACTS = {"notes.links": Impact.REVIEW, "notes.mentions": Impact.NOTIFY}


def _project() -> ProjectId:
    return ProjectId(uuid.uuid4())


def _note(item: str, body: str = "Proof.", **fields: JsonValue) -> dict[str, Any]:
    return {
        "kind": "notes.note",
        "id": item,
        "title": f"Note {item}",
        "fields": {"body": body, **fields},
    }


def _bundle(*items: dict[str, Any]) -> bytes:
    return yaml.safe_dump({"schema_version": 1, "items": list(items)}).encode()


@pytest.fixture
def changesets(store: Database) -> ChangeSets:
    del store
    unit_of_work(lambda uow: sync_lifecycle_states(uow, CATALOG))
    if APPLY not in registered_continuations():
        register_continuation(APPLY, apply_changeset)
    service = ChangeSets(
        Rules(CATALOG), Decisions(core_registries(), kinds=[APPROVAL_KIND]), IMPACTS
    )
    install(service)
    return service


def _import(service: ChangeSets, project: ProjectId, data: bytes, key: str) -> ChangeSet:
    request = BundleImport(project=project, data=data, author="operator", client_key=key)
    return unit_of_work(lambda uow: service.import_bundle(uow, request))


def _decision(changeset: ChangeSet) -> Decision:
    assert changeset.decision is not None
    decision = changeset.decision
    return unit_of_work(lambda uow: read_decision(uow, decision))


def _answer(
    service: ChangeSets, changeset: ChangeSet, answer: dict[str, Any], key: str = "a1"
) -> dict[str, JsonValue]:
    decision = _decision(changeset)
    request = AnswerRequest(
        decision=decision.id,
        answer=answer,
        answered_by="operator",
        channel=Channel.UI,
        context_hash_seen=decision.context_hash,
        client_key=key,
    )
    return unit_of_work(lambda uow: service.decisions.answer(uow, request)).answer


def _settle(service: ChangeSets, changeset: ChangeSet, answer: dict[str, JsonValue]) -> str:
    decision = changeset.decision
    assert decision is not None
    return unit_of_work(lambda uow: service.settle(uow, changeset.id, decision, answer))


def _approve(
    service: ChangeSets, changeset: ChangeSet, verdicts: dict[str, str] | None = None
) -> str:
    given = [{"item": item, "reason": reason} for item, reason in (verdicts or {}).items()]
    answer = _answer(service, changeset, {"answer": "approve", "verdicts": given})
    return _settle(service, changeset, answer)


def _seed(service: ChangeSets, project: ProjectId, *items: dict[str, Any]) -> None:
    """Items applied through an approved import."""
    changeset = _import(service, project, _bundle(*items), f"seed-{uuid.uuid4()}")
    assert _approve(service, changeset) == "applied"


def _body(project: ProjectId, item: str) -> JsonValue:
    revision = unit_of_work(lambda uow: read(uow, project, item))
    assert revision is not None
    return revision.semantic["body"]


def _changeset(changeset: ChangeSet) -> ChangeSet:
    return unit_of_work(lambda uow: read_changeset(uow, changeset.id))


def _payload(decision: Decision) -> ApprovalPayload:
    return ApprovalPayload.model_validate(decision.payload)


@pytest.mark.integration
def test_bundle_import(changesets: ChangeSets) -> None:
    """AC-0409-1."""
    project = _project()
    data = _bundle(_note("N-1"), _note("N-2", links=["N-1"]), _note("N-3", mentions=["N-2"]))

    first = _import(changesets, project, data, "import-1")
    again = _import(changesets, project, data, "import-1")

    assert again == first
    draft = unit_of_work(lambda uow: read_draft(uow, first.draft))
    assert draft.source is DraftSource.OPERATOR
    assert draft.trust is Trust.TRUSTED
    assert draft.client_key == "import-1"
    assert [r.item for r in draft.revisions] == ["N-1", "N-2", "N-3"]
    assert all(r.base is None for r in draft.revisions)
    assert first.state is ChangeSetState.AWAITING_APPROVAL

    invalid = _bundle(
        _note("X-1"),
        _note("N-5", links=["N-404"]),
        {"kind": "notes.note", "id": "N-6", "title": "No body"},
    )
    with pytest.raises(ChangeError) as refused:
        _import(changesets, project, invalid, "import-2")
    problems = refused.value.envelope.detail["problems"]
    assert isinstance(problems, list)
    assert {(p["item"], p["code"]) for p in problems if isinstance(p, dict)} == {
        ("X-1", "id_invalid"),
        ("N-5", "reference_unresolved"),
        ("N-6", "report_invalid"),
    }

    tagged = b"schema_version: 1\nitems: !!python/object/apply:os.getcwd []\n"
    with pytest.raises(IntentError) as unsafe:
        _import(changesets, project, tagged, "import-3")
    assert unsafe.value.code == "report_invalid"
    malformed = _bundle({"kind": "notes.note", "id": "N-7"}, {"id": "N-8", "title": "t"})
    with pytest.raises(IntentError) as schema:
        _import(changesets, project, malformed, "import-4")
    items = {p["item"] for p in schema.value.envelope.detail["problems"]}  # type: ignore[union-attr]
    assert items == {"N-7", "N-8"}

    only_core = ChangeSets(
        Rules(CATALOG, lambda uow, project: frozenset()), changesets.decisions, IMPACTS
    )
    with pytest.raises(ChangeError) as disabled:
        _import(only_core, project, _bundle(_note("N-9")), "import-5")
    assert disabled.value.code == "kind_not_enabled"


@pytest.mark.integration
def test_draft_records_source_and_trust(changesets: ChangeSets) -> None:
    """AC-0410-1."""
    project = _project()
    _seed(changesets, project, _note("N-1"))
    base = unit_of_work(lambda uow: read(uow, project, "N-1"))
    assert base is not None
    finding = ProposedRevision(
        item="FND-1",
        kind="core.finding",
        base=None,
        title="Merged outside Grindstone",
        fields={
            "type": "delivery_bypass",
            "severity": "high",
            "trust": "untrusted",
            "description": "A pull request was merged by hand.",
            "about": ["N-1"],
        },
    )
    revised = ProposedRevision(
        item="N-1", kind="notes.note", base=base.hash, title="Note N-1", fields={"body": "Again."}
    )
    cases = [
        (DraftSource.OPERATOR, Trust.TRUSTED, revised, AuthorKind.PERSON),
        (DraftSource.TASK_OUTPUT, Trust.TRUSTED, revised, AuthorKind.AGENT),
        (DraftSource.DELEGATION_RESULT, Trust.TRUSTED, revised, AuthorKind.AGENT),
        (DraftSource.REVERT, Trust.TRUSTED, revised, AuthorKind.PERSON),
        (DraftSource.INTAKE, Trust.UNTRUSTED, finding, AuthorKind.SYSTEM),
    ]
    provenance = Provenance(author_kind=AuthorKind.SYSTEM, author="test", reason="drafted")
    for source, trust, revision, author in cases:
        provenance = Provenance(author_kind=author, author=str(source), reason=f"from {source}")
        request = DraftRequest(project, source, trust, [revision], provenance, f"key-{source}")
        draft = unit_of_work(lambda uow, r=request: changesets.draft(uow, r))
        stored = unit_of_work(lambda uow, d=draft: read_draft(uow, d.id))
        assert stored == draft
        assert (stored.source, stored.trust, stored.provenance) == (source, trust, provenance)
        assert stored.revisions[0].base == revision.base

    trusted_intake = DraftRequest(
        project, DraftSource.INTAKE, Trust.TRUSTED, [finding], provenance, "intake-trusted"
    )
    with pytest.raises(ValueError, match="untrusted"):
        unit_of_work(lambda uow: changesets.draft(uow, trusted_intake))
    stale = revised.model_copy(update={"base": "sha256:" + "0" * 64})
    request = DraftRequest(project, DraftSource.TASK_OUTPUT, Trust.TRUSTED, [stale], provenance)
    with pytest.raises(ChangeError) as moved:
        unit_of_work(lambda uow: changesets.draft(uow, request))
    assert moved.value.code == "context_changed"


_ITEMS = [f"N-{n}" for n in range(1, 7)]
_EDGES = st.lists(
    st.tuples(
        st.sampled_from(_ITEMS),
        st.sampled_from(["notes.links", "notes.mentions", "x.unknown"]),
        st.sampled_from(_ITEMS),
    ),
    max_size=20,
)


@given(
    edges=_EDGES,
    changed=st.sets(st.sampled_from(_ITEMS), max_size=4),
    extra=st.sets(st.sampled_from(_ITEMS), max_size=2),
    reasons=st.booleans(),
)
def test_walk_lists_review_dependents(
    edges: list[tuple[str, str, str]], changed: set[str], extra: set[str], reasons: bool
) -> None:
    """AC-0411-1."""
    in_changeset = changed | extra
    graph = [
        Edge(revision=RevisionId(uuid.uuid4()), source=s, type=t, target=g) for s, t, g in edges
    ]

    def into(item: ItemId) -> list[Edge]:
        return [e for e in graph if e.target == item]

    reached, informed = reach(sorted(changed), into, IMPACTS, in_changeset)

    review = {Impact.REVIEW}
    expected = {
        (s, t, g)
        for s, t, g in edges
        if g in changed and s not in in_changeset and IMPACTS.get(t, Impact.REVIEW) in review
    }
    assert {(r.item, r.via_edge, r.to) for r in reached} == expected
    assert all(r.via_edge != "notes.mentions" for r in reached)
    assert {(r.item, r.via_edge, r.to) for r in informed} == {
        (s, t, g)
        for s, t, g in edges
        if g in changed and s not in in_changeset and t == "notes.mentions"
    }
    result = WalkResult(round=1, bases=(), changed=tuple(sorted(changed)), reached=reached)
    verdicts = [Verdict(item=r.item, reason="checked" if reasons else " ") for r in reached]
    assert (missing_verdicts(result, verdicts) == []) == (reasons or not reached)


@pytest.mark.integration
def test_import_raises_approval(changesets: ChangeSets) -> None:
    """AC-0412-1."""
    project = _project()
    _seed(
        changesets,
        project,
        _note("N-1"),
        _note("N-2", links=["N-1"]),
        _note("N-3", mentions=["N-1"]),
    )

    changeset = _import(changesets, project, _bundle(_note("N-1", "Changed."), _note("N-4")), "k")

    (decision,) = unit_of_work(lambda uow: open_decisions(uow, project))
    assert decision.id == changeset.decision
    assert decision.kind == "approval"
    assert decision.flags == ()
    payload = _payload(decision)
    assert payload.changeset == changeset.id
    assert [(r.item, r.changed_fields) for r in payload.revisions] == [
        ("N-1", ("body",)),
        ("N-4", ("body", "links", "mentions", "title")),
    ]
    assert payload.revisions[0].before is not None
    assert payload.revisions[0].before["body"] == "Proof."
    assert [(r.item, r.via_edge, r.to) for r in payload.reached] == [("N-2", "notes.links", "N-1")]
    assert [(r.item, r.via_edge) for r in payload.informed] == [("N-3", "notes.mentions")]

    finding = ProposedRevision(
        item="FND-1",
        kind="core.finding",
        base=None,
        title="Merged outside Grindstone",
        fields={
            "type": "delivery_bypass",
            "severity": "high",
            "trust": "untrusted",
            "description": "A pull request was merged by hand.",
            "about": ["N-1"],
        },
    )
    provenance = Provenance(author_kind=AuthorKind.SYSTEM, author="delivery", reason="bypass")
    request = DraftRequest(
        project, DraftSource.INTAKE, Trust.UNTRUSTED, [finding], provenance, "bypass-1"
    )
    intake = unit_of_work(lambda uow: changesets.submit(uow, changesets.draft(uow, request)))
    assert _decision(intake).flags == (DecisionFlag.UNTRUSTED,)
    assert _payload(_decision(intake)).trust is Trust.UNTRUSTED


@pytest.mark.integration
def test_approval_answers_need_verdicts(changesets: ChangeSets, engine: Engine) -> None:
    """AC-0413-1."""
    project = _project()
    _seed(changesets, project, _note("N-1"), _note("N-2", links=["N-1"]))
    changeset = _import(changesets, project, _bundle(_note("N-1", "Changed.")), "k")

    for verdicts in ([], [{"item": "N-2", "reason": "  "}], [{"item": "N-9", "reason": "x"}]):
        with pytest.raises(DecisionError) as refused:
            _answer(changesets, changeset, {"answer": "approve", "verdicts": verdicts})
        assert refused.value.code == "verdict_missing"
        assert refused.value.envelope.detail["items"] == ["N-2"]

    answer = _answer(changesets, changeset, {"answer": "reject", "notes": "N-2 is affected"})
    assert _settle(changesets, changeset, answer) == "rejected"
    assert _changeset(changeset).state is ChangeSetState.REJECTED
    assert _body(project, "N-1") == "Proof."
    with engine.connect() as conn:
        written = conn.execute(
            text("SELECT count(*) FROM intent.item_revisions WHERE changeset = :c"),
            {"c": changeset.id},
        ).scalar_one()
    assert written == 0


@pytest.mark.integration
def test_apply_is_atomic(
    changesets: ChangeSets, monkeypatch: pytest.MonkeyPatch, dbos_store: Database
) -> None:
    """AC-0414-1."""
    del dbos_store
    project = _project()
    data = _bundle(_note("N-1"), _note("N-2", links=["N-1"]))
    changeset = _import(changesets, project, data, "k")
    answer = _answer(changesets, changeset, {"answer": "approve", "verdicts": []})
    before = unit_of_work(lambda uow: events_after(uow, project, 0))

    real = module.transition_changeset

    def fault(uow: Uow, changeset: ChangeSet, to: ChangeSetState, writer: str, **kw: Any) -> None:
        if to is ChangeSetState.APPLIED:
            raise RuntimeError("fault injected before commit")
        real(uow, changeset, to, writer, **kw)

    monkeypatch.setattr(module, "transition_changeset", fault)
    with pytest.raises(RuntimeError, match="fault injected"):
        _settle(changesets, changeset, answer)
    assert unit_of_work(lambda uow: read(uow, project, "N-1")) is None
    assert unit_of_work(lambda uow: events_after(uow, project, 0)) == before
    assert _changeset(changeset).state is ChangeSetState.AWAITING_APPROVAL
    monkeypatch.setattr(module, "transition_changeset", real)

    # The continuation as the dispatcher starts it: one datasource transaction.
    decision = changeset.decision
    assert decision is not None
    payload = json.dumps({"changeset": str(changeset.id)})
    with SetWorkflowID(f"decision-{decision}"):
        handle = DBOS.start_workflow(apply_changeset, str(decision), json.dumps(answer), payload)
    assert handle.get_result() == "applied"

    assert _changeset(changeset).state is ChangeSetState.APPLIED
    n1 = unit_of_work(lambda uow: read(uow, project, "N-1"))
    n2 = unit_of_work(lambda uow: read(uow, project, "N-2"))
    assert n1 is not None
    assert n2 is not None
    assert n2.provenance.changeset == changeset.id
    assert n2.provenance.decision == decision
    after = unit_of_work(lambda uow: events_after(uow, project, len(before)))
    types = [e.type for e in after]
    assert types.count("item.revised") == 2
    assert types.count("item.transitioned") == 2
    assert types[-1] == "changeset.applied"
    assert after[-1].payload["revisions"] == [str(n1.id), str(n2.id)]


@pytest.mark.integration
def test_apply_serialized_per_project(changesets: ChangeSets) -> None:
    """AC-0414-2."""
    project = _project()
    _seed(changesets, project, _note("N-1"))
    first = _import(changesets, project, _bundle(_note("N-1", "First.")), "a")
    second = _import(changesets, project, _bundle(_note("N-1", "Second.")), "b")
    answers = [
        (cs, _answer(changesets, cs, {"answer": "approve", "verdicts": []}, f"k-{n}"))
        for n, cs in enumerate((first, second))
    ]
    barrier = threading.Barrier(2)

    def settle(pair: tuple[ChangeSet, dict[str, JsonValue]]) -> str:
        barrier.wait()
        return _settle(changesets, *pair)

    with ThreadPoolExecutor(2) as pool:
        outcomes = list(pool.map(settle, answers))

    assert sorted(outcomes) == ["applied", "rewalked"]
    winner, loser = (first, second) if outcomes[0] == "applied" else (second, first)
    assert _changeset(winner).state is ChangeSetState.APPLIED
    rewalked = _changeset(loser)
    assert rewalked.state is ChangeSetState.AWAITING_APPROVAL
    assert rewalked.decision != loser.decision
    assert unit_of_work(lambda uow: latest_round(uow, loser.id)).round == 2
    assert _body(project, "N-1") == ("First." if winner is first else "Second.")


@pytest.mark.integration
def test_moved_base_asks_again(changesets: ChangeSets) -> None:
    """AC-0415-1."""
    project = _project()
    _seed(changesets, project, _note("N-1", "One."))
    moving = _import(changesets, project, _bundle(_note("N-1", "Two.")), "a")
    waiting = _import(changesets, project, _bundle(_note("N-1", "Three.")), "b")
    old = _decision(waiting)

    assert _approve(changesets, moving) == "applied"

    # The waiting ChangeSet's approval was superseded in the same transaction.
    assert unit_of_work(lambda uow: read_decision(uow, old.id)).state is DecisionState.SUPERSEDED
    with pytest.raises(DecisionError) as superseded:
        _answer(changesets, waiting, {"answer": "approve", "verdicts": []}, "late")
    assert superseded.value.code == "decision_superseded"

    again = _changeset(waiting)
    assert again.state is ChangeSetState.AWAITING_APPROVAL
    second = _payload(_decision(again))
    assert second.round == 2
    (diff,) = second.revisions
    # The card shows applying it now would reverse the other ChangeSet's change.
    assert diff.before is not None
    assert diff.before["body"] == "Two."
    assert diff.after["body"] == "Three."
    current = unit_of_work(lambda uow: read(uow, project, "N-1"))
    assert current is not None
    assert diff.base == current.hash

    # A base that moves again asks again.
    third = _import(changesets, project, _bundle(_note("N-1", "Four.")), "c")
    assert _approve(changesets, third) == "applied"
    latest = _changeset(waiting)
    assert latest.decision not in (old.id, again.decision)
    assert _payload(_decision(latest)).round == 3

    assert _approve(changesets, latest) == "applied"
    assert _body(project, "N-1") == "Three."
    assert unit_of_work(lambda uow: open_decisions(uow, project)) == []
