"""A stand-in control plane for AC-0418-1, run as a subprocess from the repository root.

    python -m packages.grindstone.tests.decisions.continuation_child <database_url>

The first run raises a `permission` decision whose continuation records an
effect row, answers it, and with `GRINDSTONE_KILL_AT=decisions.after_answer`
dies once the answer has committed, before any dispatch. A restart answers
again with the same client key (which returns the original answer), runs
the dispatcher twice and waits for the continuation's result.
"""

import sys
import uuid

from dbos import DBOS
from packages.grindstone.tests.store.runtime_child import running

from grindstone.contracts.decisions import (
    Channel,
    DecisionScope,
    PermissionPayload,
    Recommendation,
    RecommendationSource,
)
from grindstone.contracts.ids import DecisionId, ProjectId, TaskId
from grindstone.decisions import (
    CONSUMER,
    AnswerRequest,
    Continuation,
    DecisionRequest,
    Decisions,
    read,
    register_continuation,
)
from grindstone.platform import core_registries
from grindstone.platform.events import Dispatcher
from grindstone.store import Uow, kill_point, transaction, unit_of_work, workflow

PROJECT = ProjectId(uuid.UUID("00000000-0000-7000-8000-000000000001"))
TASK = TaskId(uuid.UUID("00000000-0000-7000-8000-000000000002"))


@transaction
def record_effect(uow: Uow, decision: str, answer: str) -> None:
    uow.execute(
        "INSERT INTO scratch.continued (decision, answer) VALUES (:d, :a)",
        {"d": decision, "a": answer},
    )


@workflow("test.decisions.record")
def continue_with(decision: str, answer: str, payload: str) -> str:
    del payload
    record_effect(decision, answer)
    return decision


register_continuation("test.record", continue_with)


def _raise(uow: Uow, decisions: Decisions) -> DecisionId:
    uow.execute("CREATE SCHEMA IF NOT EXISTS scratch")
    uow.execute("CREATE TABLE IF NOT EXISTS scratch.continued (decision text, answer text)")
    row = uow.fetch_one("SELECT id FROM decisions.decisions")
    if row is not None:
        return DecisionId(row["id"])
    decision = decisions.raise_decision(
        uow,
        DecisionRequest(
            project=PROJECT,
            kind="permission",
            scope=DecisionScope(task=TASK),
            title="Write .github/",
            payload=PermissionPayload(task=TASK, action="write .github/", reason="CI change"),
            recommendation=Recommendation(
                answer={"answer": "deny"}, reason="not in scope", source=RecommendationSource.FIXED
            ),
            raised_by="work",
            continuation=Continuation("test.record", {"run": "r1"}),
        ),
    )
    return decision.id


def _answer(uow: Uow, decisions: Decisions, decision: DecisionId) -> None:
    current = read(uow, decision)
    decisions.answer(
        uow,
        AnswerRequest(
            decision=decision,
            answer={"answer": "allow_once"},
            answered_by="operator",
            channel=Channel.UI,
            context_hash_seen=current.context_hash,
            client_key="answer-1",
        ),
    )


def _answered_event(uow: Uow) -> str:
    row = uow.fetch_one("SELECT event_id FROM platform.events WHERE type = 'decision.answered'")
    if row is None:  # pragma: no cover - the answer committed before
        raise RuntimeError("no decision.answered event")
    return str(row["event_id"])


def main(database_url: str) -> int:
    with running(database_url):
        decisions = Decisions(core_registries())
        decision = unit_of_work(lambda uow: _raise(uow, decisions))
        unit_of_work(lambda uow: _answer(uow, decisions, decision))
        kill_point("decisions.after_answer")
        dispatcher = Dispatcher([CONSUMER])
        dispatcher.pass_once()
        answered = unit_of_work(_answered_event)
        DBOS.retrieve_workflow(CONSUMER.workflow_id(answered)).get_result()
        DBOS.retrieve_workflow(f"decision-{decision}").get_result()
        dispatcher.pass_once()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
