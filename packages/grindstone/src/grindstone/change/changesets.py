"""ChangeSets: draft, walk, approval, apply (SPEC-04, REQ-0409 to REQ-0415, ADR-10).

1. `draft` records a ChangeDraft once its revisions pass the M1 rules
   (`grindstone.change.rules`); a repeated client key in the project returns
   the recorded draft. `import_bundle` drafts an operator's item bundle.
2. `submit` makes the draft a ChangeSet, walks it (round 1, against the
   draft's bases), checks the rules again and raises one `approval`
   decision, flagged `untrusted` for an untrusted draft. Its payload lists
   every proposed revision with its diff against its base, and every item
   the walk reached, so the decision's context hash covers them all.
3. The answer's continuation, `change.apply`, runs `settle` in one datasource
   transaction, serialized per project by an advisory lock:
   - `reject` ends the ChangeSet with nothing applied;
   - `approve` (whose verdicts the `approval` kind has already checked,
     `verdict_missing`) applies every revision, edge, current pointer and
     initial lifecycle state if every effective base is still current, and
     emits `item.revised` per item and `changeset.applied`;
   - otherwise it applies nothing and walks the ChangeSet again as a new
     round, against the items' current hashes, raising a new approval whose
     diffs show what applying it now would change (REQ-0415).
4. An apply that moves the base of another ChangeSet awaiting approval
   supersedes that ChangeSet's open approval with a new one in the same
   transaction, so no approval is answered over a change its approver did
   not see. An approval already answered cannot be superseded (its
   lifecycle allows only `open → superseded`); its continuation finds the
   moved base and asks again, as in step 3.

Only `transition_changeset` writes a ChangeSet's `state` and `decision`
(REQ-0420).
"""

import json
import logging
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, cast

from pydantic import JsonValue

from grindstone.change.errors import ChangeError
from grindstone.change.rules import Rules
from grindstone.change.walk import Impacts, RoundSpec, walk
from grindstone.contracts.change import (
    ApprovalPayload,
    ChangeDraft,
    ChangeSet,
    ChangeSetApplied,
    ChangeSetDrafted,
    ChangeSetRejected,
    ChangeSetState,
    ChangeSetWalked,
    DraftSource,
    ItemBase,
    ProposedRevision,
    Reached,
    RevisionDiff,
    Trust,
    WalkResult,
)
from grindstone.contracts.decisions import (
    Approve,
    DecisionFlag,
    DecisionScope,
    DecisionState,
    Recommendation,
    RecommendationSource,
)
from grindstone.contracts.ids import (
    ChangeSetId,
    DecisionId,
    ItemId,
    ProjectId,
    new_record_id,
)
from grindstone.contracts.platform import EdgeDecl, Impact
from grindstone.contracts.provenance import AuthorKind, Provenance
from grindstone.contracts.refs import ItemRef, SemanticHash
from grindstone.decisions import (
    KERNEL_DECISION_KINDS,
    Continuation,
    DecisionError,
    DecisionKind,
    DecisionRequest,
    Decisions,
)
from grindstone.decisions import read as read_decision
from grindstone.intent import (
    KindCatalog,
    Materialised,
    Proposal,
    RevisionBatch,
    applying,
    current_hash,
    parse_bundle,
    read_pinned,
    write_revisions,
)
from grindstone.platform import Category, Registries
from grindstone.platform.events import emit
from grindstone.store import Uow, transaction, workflow

_log = logging.getLogger(__name__)

RAISED_BY = "change"
APPLY = "change.apply"

type Json = dict[str, JsonValue]
type Outcome = Literal["applied", "rejected", "rewalked", "stale"]


def _check_verdicts(payload: Json, answer: Json) -> None:
    """An approval applies only with an `unaffected` verdict and a reason per reached item."""
    if answer.get("answer") != "approve":
        return
    reached = {str(cast(Json, r)["item"]) for r in cast(list[JsonValue], payload["reached"])}
    given = {
        str(v["item"]): str(v.get("reason", ""))
        for v in cast(list[Json], answer.get("verdicts", []))
    }
    missing = sorted(item for item in reached if not given.get(item, "").strip())
    if missing:
        raise DecisionError(
            "verdict_missing",
            f"approving needs an `unaffected` verdict with a reason for {', '.join(missing)}",
            items=list[JsonValue](missing),
        )


APPROVAL_KIND: DecisionKind = KERNEL_DECISION_KINDS["approval"].refined(
    payload=ApprovalPayload, check=_check_verdicts
)
"""The `approval` kind as `change` raises it; the composition root gives it to `Decisions`."""

# The ChangeSet lifecycle: (from, to) → its one writer (REQ-0420).
_TRANSITIONS: Mapping[tuple[ChangeSetState, ChangeSetState], str] = {
    (ChangeSetState.DRAFTED, ChangeSetState.WALKED): "walk",
    (ChangeSetState.WALKED, ChangeSetState.AWAITING_APPROVAL): "walk",
    (ChangeSetState.AWAITING_APPROVAL, ChangeSetState.APPLIED): "apply",
    (ChangeSetState.AWAITING_APPROVAL, ChangeSetState.WALKED): "apply",
    (ChangeSetState.AWAITING_APPROVAL, ChangeSetState.REJECTED): "answer",
}

_AUTHOR_KINDS: Mapping[DraftSource, AuthorKind] = {
    DraftSource.OPERATOR: AuthorKind.PERSON,
    DraftSource.TASK_OUTPUT: AuthorKind.AGENT,
    DraftSource.DELEGATION_RESULT: AuthorKind.AGENT,
    DraftSource.INTAKE: AuthorKind.SYSTEM,
    DraftSource.REVERT: AuthorKind.PERSON,
}


def author_kind(source: DraftSource) -> AuthorKind:
    """The provenance author kind a draft's revisions carry, from where it came."""
    return _AUTHOR_KINDS[source]


@dataclass(frozen=True, slots=True)
class BundleImport:
    """An operator's item bundle to import, with the request's client key."""

    project: ProjectId
    data: bytes
    author: str
    client_key: str
    reason: str = "imported from an item bundle"


@dataclass(frozen=True, slots=True)
class DraftRequest:
    """A draft to record: where it came from, its trust, its revisions and their provenance."""

    project: ProjectId
    source: DraftSource
    trust: Trust
    revisions: Sequence[ProposedRevision]
    provenance: Provenance
    client_key: str | None = None


def impacts_of(registries: Registries) -> dict[str, Impact]:
    """Each registered edge type's impact, for the walk."""
    return {
        name: cast(EdgeDecl, registries.require(Category.EDGE, name).value).impact
        for name in registries.names(Category.EDGE)
    }


class ChangeSets:
    """The ChangeSet service, over the kinds, the decision service and the edge impacts."""

    def __init__(self, rules: Rules, decisions: Decisions, impacts: Impacts) -> None:
        self.rules = rules
        self.catalog: KindCatalog = rules.catalog
        self.decisions = decisions
        self.impacts = impacts

    # Drafting.

    def draft(self, uow: Uow, request: DraftRequest) -> ChangeDraft:
        """Record a draft that passes the M1 rules, or refuse it with every problem.

        A draft from intake is always untrusted (I-07). A client key already
        used in the project returns the draft recorded under it.
        """
        if request.source is DraftSource.INTAKE and request.trust is not Trust.UNTRUSTED:
            raise ValueError("a draft from intake is untrusted (I-07)")
        if request.client_key is not None:
            recorded = _draft_by_key(uow, request.project, request.client_key)
            if recorded is not None:
                return recorded
        bases = {r.item: r.base for r in request.revisions}
        self.rules.check(uow, request.project, request.revisions, bases)
        draft = ChangeDraft(
            id=new_record_id(),
            project=request.project,
            source=request.source,
            trust=request.trust,
            revisions=tuple(request.revisions),
            provenance=request.provenance,
            client_key=request.client_key,
        )
        uow.execute(
            "INSERT INTO change.drafts"
            " (id, project, source, trust, revisions, provenance, client_key)"
            " VALUES (:id, :project, :source, :trust, CAST(:revisions AS jsonb),"
            " CAST(:provenance AS jsonb), :client_key)",
            {
                "id": draft.id,
                "project": draft.project,
                "source": str(draft.source),
                "trust": str(draft.trust),
                "revisions": json.dumps([r.model_dump(mode="json") for r in draft.revisions]),
                "provenance": draft.provenance.model_dump_json(),
                "client_key": draft.client_key,
            },
        )
        return draft

    def import_bundle(self, uow: Uow, request: BundleImport) -> ChangeSet:
        """Draft and submit an operator's item bundle (REQ-0409).

        An existing ID is revised against its current hash; a new ID is
        created. Importing again with the same client key returns the
        ChangeSet of the first import.
        """
        project, client_key = request.project, request.client_key
        recorded = _draft_by_key(uow, project, client_key)
        if recorded is not None:
            return self.submit(uow, recorded)
        bundle = parse_bundle(request.data)
        revisions = [
            ProposedRevision(
                item=item.id,
                kind=item.kind,
                base=current_hash(uow, project, item.id),
                title=item.title,
                fields=item.fields,
            )
            for item in bundle.items
        ]
        draft = self.draft(
            uow,
            DraftRequest(
                project=project,
                source=DraftSource.OPERATOR,
                trust=Trust.TRUSTED,
                revisions=revisions,
                provenance=Provenance(
                    author_kind=AuthorKind.PERSON, author=request.author, reason=request.reason
                ),
                client_key=client_key,
            ),
        )
        return self.submit(uow, draft)

    # Submission and approval.

    def submit(self, uow: Uow, draft: ChangeDraft) -> ChangeSet:
        """Make a draft a ChangeSet, walk it and raise its approval; once per draft."""
        existing = uow.fetch_one(_SELECT + " WHERE draft = :draft", {"draft": draft.id})
        if existing is not None:
            return ChangeSet.model_validate(dict(existing))
        changeset = ChangeSetId(new_record_id())
        uow.execute(
            "INSERT INTO change.changesets (id, project, draft) VALUES (:id, :project, :draft)",
            {"id": changeset, "project": draft.project, "draft": draft.id},
        )
        emit(
            uow,
            ChangeSetDrafted(
                changeset=changeset, draft=draft.id, source=draft.source, trust=draft.trust
            ),
            draft.project,
        )
        bases = {r.item: r.base for r in draft.revisions}
        spec = RoundSpec(1, self._check(uow, draft, bases), bases)
        self._walk_and_ask(uow, read_changeset(uow, changeset), draft, spec)
        return read_changeset(uow, changeset)

    def _check(
        self, uow: Uow, draft: ChangeDraft, bases: Mapping[ItemId, SemanticHash | None]
    ) -> list[Materialised]:
        return self.rules.check(uow, draft.project, draft.revisions, bases)

    def _walk_and_ask(
        self, uow: Uow, changeset: ChangeSet, draft: ChangeDraft, spec: RoundSpec
    ) -> DecisionId:
        """Record a walk round, then raise its approval and await the answer."""
        materialised, bases = spec.materialised, spec.bases
        result = walk(uow, self.impacts, draft.project, spec)
        uow.execute(
            "INSERT INTO change.walk_rounds (changeset, round, bases, changed, reached, informed)"
            " VALUES (:changeset, :round, CAST(:bases AS jsonb), CAST(:changed AS jsonb),"
            " CAST(:reached AS jsonb), CAST(:informed AS jsonb))",
            {
                "changeset": changeset.id,
                "round": result.round,
                "bases": _dumps(result.bases),
                "changed": json.dumps(list(result.changed)),
                "reached": _dumps(result.reached),
                "informed": _dumps(result.informed),
            },
        )
        if changeset.state is ChangeSetState.DRAFTED:
            transition_changeset(uow, changeset, ChangeSetState.WALKED, "walk")
            changeset = read_changeset(uow, changeset.id)
        emit(
            uow,
            ChangeSetWalked(
                changeset=changeset.id,
                round=result.round,
                reached=tuple(dict.fromkeys(r.item for r in result.reached)),
            ),
            draft.project,
        )
        payload = ApprovalPayload(
            changeset=changeset.id,
            round=result.round,
            trust=draft.trust,
            revisions=_diffs(uow, draft.project, materialised, bases),
            reached=result.reached,
            informed=result.informed,
        )
        decision = self.decisions.raise_decision(
            uow,
            DecisionRequest(
                project=draft.project,
                kind="approval",
                scope=DecisionScope(changeset=changeset.id),
                title=_title(draft, result),
                payload=payload,
                recommendation=Recommendation(
                    answer=Approve().model_dump(mode="json"),
                    reason=(
                        "rules pass; every reached item needs your verdict"
                        if result.reached
                        else "rules pass; nothing else is affected"
                    ),
                    source=RecommendationSource.FIXED,
                ),
                raised_by=RAISED_BY,
                flags=(DecisionFlag.UNTRUSTED,) if draft.trust is Trust.UNTRUSTED else (),
                continuation=Continuation(APPLY, {"changeset": str(changeset.id)}),
            ),
        )
        transition_changeset(
            uow, changeset, ChangeSetState.AWAITING_APPROVAL, "walk", decision=decision.id
        )
        return decision.id

    # Settling an answered approval.

    def settle(
        self, uow: Uow, changeset_id: ChangeSetId, decision: DecisionId, answer: Json
    ) -> Outcome:
        """Apply, reject or re-walk the ChangeSet an approval was answered for.

        Runs in one transaction; a ChangeSet no longer awaiting this decision
        is left as it is (`stale`).
        """
        # The project lock first, then the row: two settles never wait on each other crosswise.
        uow.lock(f"change.apply:{read_changeset(uow, changeset_id).project}")
        changeset = _locked(uow, changeset_id)
        if (
            changeset.state is not ChangeSetState.AWAITING_APPROVAL
            or changeset.decision != decision
        ):
            return "stale"
        if answer.get("answer") == "reject":
            transition_changeset(uow, changeset, ChangeSetState.REJECTED, "answer")
            emit(
                uow, ChangeSetRejected(changeset=changeset.id, decision=decision), changeset.project
            )
            return "rejected"
        draft = read_draft(uow, changeset.draft)
        latest = latest_round(uow, changeset.id)
        bases = {b.item: b.base for b in latest.bases}
        if _moved(uow, changeset.project, bases):
            self._rewalk(uow, changeset, draft, latest)
            return "rewalked"
        approve = Approve.model_validate(answer)
        reached = {r.item for r in latest.reached}
        for verdict in approve.verdicts:
            if verdict.item in reached:
                uow.execute(
                    "INSERT INTO change.verdicts"
                    " (changeset, round, item, verdict, reason, decision)"
                    " VALUES (:changeset, :round, :item, :verdict, :reason, :decision)",
                    {
                        "changeset": changeset.id,
                        "round": latest.round,
                        "item": verdict.item,
                        "verdict": verdict.verdict,
                        "reason": verdict.reason,
                        "decision": decision,
                    },
                )
        provenance = draft.provenance.model_copy(
            update={"changeset": changeset.id, "decision": decision}
        )
        proposals = [Proposal(r.item, r.kind, r.title, r.fields) for r in draft.revisions]
        with applying(changeset.id):
            written = write_revisions(
                uow,
                self.catalog,
                RevisionBatch(changeset.project, changeset.id, provenance, proposals),
            )
        transition_changeset(uow, changeset, ChangeSetState.APPLIED, "apply")
        emit(
            uow,
            ChangeSetApplied(
                changeset=changeset.id, decision=decision, revisions=tuple(r.id for r in written)
            ),
            changeset.project,
        )
        self._ask_again_where_moved(uow, changeset, {r.item for r in written})
        return "applied"

    def _rewalk(
        self, uow: Uow, changeset: ChangeSet, draft: ChangeDraft, latest: WalkResult
    ) -> DecisionId:
        """Walk again against the current hashes and raise a new approval (REQ-0415).

        The rules run first, so a refusal leaves nothing written.
        """
        bases = {b.item: current_hash(uow, draft.project, b.item) for b in latest.bases}
        spec = RoundSpec(latest.round + 1, self._check(uow, draft, bases), bases)
        transition_changeset(uow, changeset, ChangeSetState.WALKED, "apply")
        return self._walk_and_ask(uow, read_changeset(uow, changeset.id), draft, spec)

    def _ask_again_where_moved(self, uow: Uow, applied: ChangeSet, items: Iterable[ItemId]) -> None:
        """Supersede the open approvals of other ChangeSets whose bases this apply moved."""
        touched = set(items)
        rows = uow.fetch_all(
            _SELECT + " WHERE project = :project AND state = 'awaiting_approval' AND id <> :id"
            " ORDER BY created_at, id FOR UPDATE",
            {"project": applied.project, "id": applied.id},
        )
        for row in rows:
            other = ChangeSet.model_validate(dict(row))
            latest = latest_round(uow, other.id)
            bases = {b.item: b.base for b in latest.bases if b.item in touched}
            if other.decision is None or not _moved(uow, other.project, bases):
                continue
            if read_decision(uow, other.decision).state is not DecisionState.OPEN:
                # Already answered: its own continuation finds the moved base.
                continue
            previous = other.decision
            try:
                replacement = self._rewalk(uow, other, read_draft(uow, other.draft), latest)
            except ChangeError as exc:
                # Its rules fail over the new base; its approval stays, and its own
                # answer will find the moved base and be refused the same way.
                _log.warning("ChangeSet %s cannot be walked again: %s", other.id, exc)
                continue
            self.decisions.supersede(uow, previous, replacement, RAISED_BY)


def transition_changeset(
    uow: Uow,
    changeset: ChangeSet,
    to: ChangeSetState,
    writer: str,
    *,
    decision: DecisionId | None = None,
) -> None:
    """The one writer of a ChangeSet's `state` and `decision` (REQ-0420)."""
    if _TRANSITIONS.get((changeset.state, to)) != writer:
        raise ChangeError.single(
            changeset.id,
            "transition_illegal",
            f"ChangeSet {changeset.id}: {changeset.state} → {to} by {writer} is not allowed",
        )
    uow.execute(
        "UPDATE change.changesets SET state = :to, decision = coalesce(:decision, decision)"
        " WHERE id = :id",
        {"id": changeset.id, "to": str(to), "decision": decision},
    )


_SELECT = "SELECT id, project, draft, state, decision FROM change.changesets"


def read_changeset(uow: Uow, changeset: ChangeSetId) -> ChangeSet:
    row = uow.fetch_one(_SELECT + " WHERE id = :id", {"id": changeset})
    if row is None:
        raise KeyError(f"no ChangeSet {changeset}")
    return ChangeSet.model_validate(dict(row))


def read_draft(uow: Uow, draft: uuid.UUID) -> ChangeDraft:
    row = uow.fetch_one(
        "SELECT id, project, source, trust, revisions, provenance, client_key"
        " FROM change.drafts WHERE id = :id",
        {"id": draft},
    )
    if row is None:
        raise KeyError(f"no draft {draft}")
    return ChangeDraft.model_validate(dict(row))


def latest_round(uow: Uow, changeset: ChangeSetId) -> WalkResult:
    """The ChangeSet's latest walk round, whose bases are its effective bases (DEC-0407)."""
    row = uow.fetch_one(
        "SELECT round, bases, changed, reached, informed FROM change.walk_rounds"
        " WHERE changeset = :changeset ORDER BY round DESC LIMIT 1",
        {"changeset": changeset},
    )
    if row is None:
        raise KeyError(f"ChangeSet {changeset} has not been walked")
    return WalkResult.model_validate(dict(row))


def _draft_by_key(uow: Uow, project: ProjectId, client_key: str) -> ChangeDraft | None:
    row = uow.fetch_one(
        "SELECT id FROM change.drafts WHERE project = :project AND client_key = :key",
        {"project": project, "key": client_key},
    )
    return None if row is None else read_draft(uow, row["id"])


def _locked(uow: Uow, changeset: ChangeSetId) -> ChangeSet:
    row = uow.fetch_one(_SELECT + " WHERE id = :id FOR UPDATE", {"id": changeset})
    if row is None:
        raise KeyError(f"no ChangeSet {changeset}")
    return ChangeSet.model_validate(dict(row))


def _moved(uow: Uow, project: ProjectId, bases: Mapping[ItemId, SemanticHash | None]) -> bool:
    return any(current_hash(uow, project, item) != base for item, base in bases.items())


def _diffs(
    uow: Uow,
    project: ProjectId,
    materialised: Sequence[Materialised],
    bases: Mapping[ItemId, SemanticHash | None],
) -> tuple[RevisionDiff, ...]:
    """Each proposed revision against its base: title and semantic fields before and after."""
    diffs: list[RevisionDiff] = []
    for m in materialised:
        item = m.proposal.item
        base = bases.get(item)
        before: Json | None = None
        if base is not None:
            revision = read_pinned(uow, project, ItemRef(id=item, hash=base))
            if revision is not None:
                before = {"title": revision.title, **revision.semantic}
        after: Json = {"title": m.proposal.title, **m.semantic}
        names = sorted(set(after) | set(before or {}))
        changed = tuple(n for n in names if before is None or before.get(n) != after.get(n))
        diffs.append(
            RevisionDiff(
                item=item,
                kind=m.proposal.kind,
                base=base,
                proposed=m.hash,
                before=before,
                after=after,
                changed_fields=changed,
            )
        )
    return tuple(diffs)


def _title(draft: ChangeDraft, result: WalkResult) -> str:
    n = len(draft.revisions)
    items = ", ".join(r.item for r in draft.revisions[:3]) + (", …" if n > 3 else "")
    reached = f"; {len(result.reached)} reached" if result.reached else ""
    return f"Approve {n} revision{'s' if n != 1 else ''} ({items}){reached}"


def _dumps(models: Iterable[ItemBase] | Iterable[Reached]) -> str:
    return json.dumps([m.model_dump(mode="json") for m in models])


# The `change.apply` continuation, registered at the composition root.


class _Installed:
    changesets: ChangeSets | None = None


_installed = _Installed()


def install(changesets: ChangeSets) -> None:
    """Give the `change.apply` continuation the process's ChangeSet service."""
    _installed.changesets = changesets


def installed() -> ChangeSets:
    if _installed.changesets is None:
        raise RuntimeError(
            "the ChangeSet service is not installed: call change.install() at start-up"
        )
    return _installed.changesets


@transaction
def _settle(uow: Uow, decision: str, answer: str, payload: str) -> str:
    changeset = ChangeSetId(uuid.UUID(json.loads(payload)["changeset"]))
    return installed().settle(uow, changeset, DecisionId(uuid.UUID(decision)), json.loads(answer))


@workflow("change.apply")  # the name is APPLY; the version check reads it literally
def apply_changeset(decision: str, answer: str, payload: str) -> str:
    """Settle an answered approval in one transaction (REQ-0413 to REQ-0415)."""
    return _settle(decision, answer, payload)
