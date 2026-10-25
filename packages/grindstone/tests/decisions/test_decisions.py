"""SPEC-04, TKT-0402: decision records, kinds, answers and continuations."""

import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text

from grindstone.contracts.decisions import (
    Channel,
    Decision,
    DecisionFlag,
    DecisionScope,
    DecisionState,
    PermissionPayload,
    QuestionPayload,
    Recommendation,
    RecommendationSource,
)
from grindstone.contracts.ids import DecisionId, ProjectId, RunId, TaskId
from grindstone.decisions import (
    AnswerRequest,
    DecisionError,
    DecisionRequest,
    Decisions,
    open_decisions,
    read,
)
from grindstone.platform import core_registries
from grindstone.platform.events import events_after
from grindstone.store import KILL_AT_ENV, KILL_MARKER_ENV, Database, Uow, unit_of_work

REPO = Path(__file__).resolve().parents[4]
CHILD_MODULE = "packages.grindstone.tests.decisions.continuation_child"
TASK = TaskId(uuid.uuid4())


def _recommend(answer: str = "deny") -> Recommendation:
    return Recommendation(
        answer={"answer": answer}, reason="outside the ticket", source=RecommendationSource.FIXED
    )


def _permission(project: ProjectId, **changes: Any) -> DecisionRequest:
    fields: dict[str, Any] = {
        "project": project,
        "kind": "permission",
        "scope": DecisionScope(task=TASK),
        "title": "Write .github/",
        "payload": PermissionPayload(task=TASK, action="write .github/", reason="CI change"),
        "recommendation": _recommend(),
        "raised_by": "work",
    }
    fields.update(changes)
    return DecisionRequest(**fields)


def _answer(
    decision: Decision, answer: str = "allow_once", key: str = "k1", seen: str | None = None
) -> AnswerRequest:
    return AnswerRequest(
        decision=decision.id,
        answer={"answer": answer},
        answered_by="operator",
        channel=Channel.UI,
        context_hash_seen=seen or decision.context_hash,
        client_key=key,
    )


@pytest.fixture
def decisions() -> Decisions:
    return Decisions(core_registries())


def _raise(decisions: Decisions, request: DecisionRequest) -> Decision:
    return unit_of_work(lambda uow: decisions.raise_decision(uow, request))


def test_decision_needs_recommendation(store: Database, decisions: Decisions) -> None:
    project = ProjectId(uuid.uuid4())
    with pytest.raises(DecisionError) as missing:
        _raise(decisions, _permission(project, recommendation=None))
    assert missing.value.code == "recommendation_missing"
    smuggled = {"task": str(TASK), "action": "a", "reason": "r", "flags": ["untrusted"]}
    with pytest.raises(ValueError, match="flags are set by the kernel"):
        _raise(decisions, _permission(project, payload=smuggled))
    with pytest.raises(ValueError, match="not registered"):
        _raise(decisions, _permission(project, kind="sdlc.unknown"))
    with pytest.raises(DecisionError) as bad:
        _raise(decisions, _permission(project, recommendation=_recommend("perhaps")))
    assert bad.value.code == "answer_invalid"

    flagged = _raise(
        decisions,
        _permission(project, flags=(DecisionFlag.UNTRUSTED, DecisionFlag.SCOPE_EXPANSION)),
    )
    assert flagged.state is DecisionState.OPEN
    assert flagged.flags == (DecisionFlag.SCOPE_EXPANSION, DecisionFlag.UNTRUSTED)
    assert flagged.recommendation.source is RecommendationSource.FIXED
    assert unit_of_work(lambda uow: open_decisions(uow, project)) == [flagged]
    stream = unit_of_work(lambda uow: events_after(uow, project, 0))
    assert [(e.type, e.payload["decision"]) for e in stream] == [
        ("decision.raised", str(flagged.id))
    ]


def test_context_hash_covers_what_is_shown(store: Database, decisions: Decisions) -> None:
    project = ProjectId(uuid.uuid4())
    one = _raise(decisions, _permission(project))
    same = _raise(decisions, _permission(project, title="Another title"))
    other = _raise(
        decisions,
        _permission(project, payload=PermissionPayload(task=TASK, action="b", reason="r")),
    )
    assert one.context_hash == same.context_hash != other.context_hash


def test_answer_guards(store: Database, decisions: Decisions) -> None:
    project = ProjectId(uuid.uuid4())
    first = _raise(decisions, _permission(project))
    second = _raise(decisions, _permission(project, title="Asked again"))
    unit_of_work(lambda uow: decisions.supersede(uow, first.id, second.id, "work"))

    def refused(request: AnswerRequest) -> str:
        with pytest.raises(DecisionError) as raised:
            unit_of_work(lambda uow: decisions.answer(uow, request))
        return raised.value.code

    assert refused(_answer(first)) == "decision_superseded"
    assert refused(_answer(second, seen="sha256:" + "f" * 64)) == "context_changed"
    assert refused(_answer(second, answer="perhaps")) == "answer_invalid"

    accepted = unit_of_work(lambda uow: decisions.answer(uow, _answer(second)))
    assert (accepted.answered_by, accepted.channel) == ("operator", Channel.UI)
    assert accepted.answer == {"answer": "allow_once"}
    assert accepted.at is not None
    assert unit_of_work(lambda uow: read(uow, second.id)).state is DecisionState.ANSWERED
    assert unit_of_work(lambda uow: decisions.answer(uow, _answer(second))) == accepted
    assert refused(_answer(second, answer="deny", key="k2")) == "decision_closed"
    types = [e.type for e in unit_of_work(lambda uow: events_after(uow, project, 0))]
    assert types == ["decision.raised"] * 2 + ["decision.superseded", "decision.answered"]

    asked = _raise(
        decisions,
        DecisionRequest(
            project=project,
            kind="question",
            scope=DecisionScope(task=TASK),
            title="Which port?",
            payload=QuestionPayload(
                task=TASK,
                run=RunId(uuid.uuid4()),
                question="Which port should the service listen on?",
                answer_schema={"type": "integer", "minimum": 1024},
            ),
            recommendation=Recommendation(
                answer={"answer": 8080}, reason="the default", source=RecommendationSource.AGENT
            ),
            raised_by="work",
        ),
    )
    low = AnswerRequest(
        decision=asked.id,
        answer={"answer": 80},
        answered_by="operator",
        channel=Channel.API,
        context_hash_seen=asked.context_hash,
        client_key="q1",
    )
    assert refused(low) == "answer_invalid"


def test_only_raiser_supersedes(store: Database, decisions: Decisions) -> None:
    project = ProjectId(uuid.uuid4())
    old = _raise(decisions, _permission(project))
    new = _raise(decisions, _permission(project, title="Asked again"))
    with pytest.raises(PermissionError):
        unit_of_work(lambda uow: decisions.supersede(uow, old.id, new.id, "change"))
    unit_of_work(lambda uow: decisions.supersede(uow, old.id, new.id, "work"))

    def both(uow: Uow) -> tuple[Decision, Decision]:
        return read(uow, old.id), read(uow, new.id)

    superseded, replacement = unit_of_work(both)
    assert (superseded.state, superseded.superseded_by) == (DecisionState.SUPERSEDED, new.id)
    assert replacement.state is DecisionState.OPEN
    with pytest.raises(DecisionError) as again:
        unit_of_work(lambda uow: decisions.supersede(uow, old.id, new.id, "work"))
    assert again.value.code == "decision_closed"
    with pytest.raises(KeyError):
        unit_of_work(lambda uow: read(uow, DecisionId(uuid.uuid4())))


def test_answers_are_insert_only(store: Database, decisions: Decisions) -> None:
    decision = _raise(decisions, _permission(ProjectId(uuid.uuid4())))
    unit_of_work(lambda uow: decisions.answer(uow, _answer(decision)))
    with pytest.raises(Exception, match="insert-only"):
        unit_of_work(lambda uow: uow.execute("UPDATE decisions.answers SET answered_by = 'x'"))


def _child(database_url: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", CHILD_MODULE, database_url],
        cwd=REPO,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_continuation_exactly_once(database_url: str, engine: Engine, tmp_path: Path) -> None:
    """Killed after the answer commits, the restarted process runs the continuation once."""
    marker = tmp_path / "killed"
    env = {**os.environ, KILL_AT_ENV: "decisions.after_answer", KILL_MARKER_ENV: str(marker)}

    first = _child(database_url, env)
    assert first.returncode != 0, first.stderr
    assert marker.exists()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM decisions.answers")).scalar_one() == 1
        assert conn.execute(text("SELECT count(*) FROM scratch.continued")).scalar_one() == 0

    second = _child(database_url, env)
    assert second.returncode == 0, second.stderr
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT answer FROM scratch.continued")).scalars().all()
        assert conn.execute(text("SELECT count(*) FROM decisions.answers")).scalar_one() == 1
    assert len(rows) == 1
    assert '"allow_once"' in rows[0]
