"""The unit of work and workflow datasource transactions (REQ-0203).

Each conflict is a write skew forced with a barrier: both transactions read
`scratch.ledger`, wait for each other, then insert, so SERIALIZABLE must fail
one of them. Only first attempts wait at the barrier, so a retry runs through;
it may conflict again until the winner commits, so the retry count varies.
"""

import os
import subprocess
import sys
import threading
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from dbos import DBOS, SetWorkflowID
from sqlalchemy import Engine, text

from grindstone.store import Database, Uow, transaction, unit_of_work

pytestmark = pytest.mark.integration

CRASH_CHILD = Path(__file__).with_name("crash_child.py")


class _Race:
    """Shared by the two racing transactions of one test."""

    def __init__(self) -> None:
        self.barrier = threading.Barrier(2, timeout=30)
        self.attempts: Counter[str] = Counter()
        self._lock = threading.Lock()

    def first_attempt(self, who: str) -> bool:
        with self._lock:
            self.attempts[who] += 1
            return self.attempts[who] == 1


_race = _Race()


def _create_ledger(uow: Uow) -> None:
    uow.execute("CREATE SCHEMA scratch")
    uow.execute("CREATE TABLE scratch.ledger (who text NOT NULL)")


def _read_wait_insert(uow: Uow, who: str) -> str:
    """The write skew; returns the isolation level the transaction ran at."""
    isolation = uow.fetch_one("SHOW transaction_isolation")
    assert isolation is not None
    first = _race.first_attempt(who)
    uow.fetch_one("SELECT count(*) AS n FROM scratch.ledger")
    if first:
        _race.barrier.wait()
    uow.execute("INSERT INTO scratch.ledger (who) VALUES (:who)", {"who": who})
    return str(isolation["transaction_isolation"])


@transaction
def _conflicting_step(uow: Uow, who: str) -> str:
    return _read_wait_insert(uow, who)


@DBOS.workflow()
def _conflicting_workflow(who: str) -> str:
    return _conflicting_step(who)


def _ledger_rows(engine: Engine) -> list[str]:
    with engine.connect() as conn:
        return sorted(conn.execute(text("SELECT who FROM scratch.ledger")).scalars())


def _assert_one_side_retried() -> None:
    """One transaction commits first time; the other retries until it commits.

    How often it retries depends on timing: a retry that starts before the
    winner commits conflicts again, so only "at least once" is stable.
    """
    first, second = sorted(_race.attempts.values())
    assert first == 1
    assert second >= 2


def _in_parallel[R](calls: list[Callable[[], R]]) -> list[R]:
    with ThreadPoolExecutor(len(calls)) as pool:
        return [f.result() for f in [pool.submit(call) for call in calls]]


def test_unit_of_work_retries_serialization_failures(store: Database, engine: Engine) -> None:
    """AC-0203-2."""
    global _race  # noqa: PLW0603 - one race per test
    _race = _Race()
    unit_of_work(_create_ledger)

    def run(who: str) -> Callable[[], str]:
        return lambda: unit_of_work(lambda uow: _read_wait_insert(uow, who))

    assert sorted(_in_parallel([run("a"), run("b")])) == ["serializable", "serializable"]
    _assert_one_side_retried()
    assert _ledger_rows(engine) == ["a", "b"]


def test_datasource_transaction_isolation_and_retry(dbos_store: Database, engine: Engine) -> None:
    """AC-0203-3."""
    global _race  # noqa: PLW0603 - one race per test
    _race = _Race()
    unit_of_work(_create_ledger)

    def run(who: str) -> Callable[[], str]:
        def start() -> str:
            with SetWorkflowID(f"isolation-{who}"):
                handle = DBOS.start_workflow(_conflicting_workflow, who)
            return handle.get_result()

        return start

    assert _in_parallel([run("a"), run("b")]) == ["serializable", "serializable"]
    _assert_one_side_retried()
    assert _ledger_rows(engine) == ["a", "b"]
    for who in ("a", "b"):
        steps = DBOS.list_workflow_steps(f"isolation-{who}")
        names = [step["function_name"] for step in steps]
        assert names.count(_conflicting_step.__qualname__) == 1, names


@pytest.mark.parametrize(
    ("kill_at", "rows_after_kill"), [("after_commit", 1), ("before_commit", 0)]
)
def test_transaction_step_commits_with_checkpoint(
    database_url: str, engine: Engine, tmp_path: Path, kill_at: str, rows_after_kill: int
) -> None:
    """AC-0203-1: killed after commit, the step is not re-run; killed before, it left
    nothing and runs once on recovery."""
    marker = tmp_path / "killed"
    env = {
        **os.environ,
        "GRINDSTONE_TEST_KILL_AT": kill_at,
        "GRINDSTONE_TEST_KILL_MARKER": str(marker),
    }
    command = [sys.executable, str(CRASH_CHILD), database_url]

    killed = subprocess.run(
        command, check=False, env=env, capture_output=True, text=True, timeout=120
    )
    assert killed.returncode != 0, killed.stderr
    assert marker.read_text() == kill_at
    with engine.connect() as conn:
        count = text("SELECT count(*) FROM scratch.effects")
        assert conn.execute(count).scalar_one() == rows_after_kill

    restarted = subprocess.run(
        command, check=False, env=env, capture_output=True, text=True, timeout=120
    )
    assert restarted.returncode == 0, restarted.stderr
    with engine.connect() as conn:
        assert conn.execute(count).scalar_one() == 1
