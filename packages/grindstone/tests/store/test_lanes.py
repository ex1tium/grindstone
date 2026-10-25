"""SPEC-02, TKT-0204: lanes as DBOS queues (REQ-0206), on real PostgreSQL and DBOS."""

import threading
import time
import uuid
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import pytest
from dbos import DBOS, WorkflowHandle
from packages.grindstone.tests.store.runtime_child import running
from pydantic import ValidationError

from grindstone.contracts.store import LaneSpec
from grindstone.store import LANE_SEEDS, QueueSpec, enqueue, queue_specs, workflow

WRITING = "lane.s1.writing"
READONLY = "lane.s1.readonly"
FAST_POLL = 0.05


class _Tracker:
    """How many lane workflows run at once, per lane, and the most seen."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.running: Counter[str] = Counter()
        self.peak: Counter[str] = Counter()
        self.projects: dict[str, set[str]] = {}

    def enter(self, lane: str, record: str) -> None:
        with self._lock:
            self.running[lane] += 1
            self.peak[lane] = max(self.peak[lane], self.running[lane])
            self.projects.setdefault(lane, set()).add(record.split("-", maxsplit=1)[0])

    def leave(self, lane: str) -> None:
        with self._lock:
            self.running[lane] -= 1


_tracker = _Tracker()


@workflow("test.lanes.work")
def lane_work(record: str, lane: str) -> str:
    _tracker.enter(lane, record)
    time.sleep(0.02)
    _tracker.leave(lane)
    return record


@workflow("test.lanes.waiting_parent")
def waiting_parent(record: str) -> str:
    """Holds the writing lane while it waits on a child on the same lane: the deadlock."""
    child = enqueue(WRITING, f"{record}.child", lane_work, f"{record}.child", "child")
    return child.get_result()


@workflow("test.lanes.ending_parent")
def ending_parent(record: str) -> str:
    """Enqueues its child and ends its turn, as SPEC-06 requires."""
    enqueue(WRITING, f"{record}.child", lane_work, f"{record}.child", "child")
    return f"{record}.child"


def _lanes(writing: int = 1, readonly: int = 3) -> tuple[QueueSpec, ...]:
    return queue_specs(
        [
            LaneSpec(station="s1", lane="writing", concurrency=writing),
            LaneSpec(station="s1", lane="readonly", concurrency=readonly),
        ],
        polling_seconds=FAST_POLL,
    )


def _status(workflow_id: str) -> str | None:
    status = DBOS.get_workflow_status(workflow_id)
    return status.status if status is not None else None


def _wait_until(probe: Callable[[], bool], timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if probe():
            return True
        time.sleep(0.05)
    return probe()


@pytest.mark.integration
def test_lanes_bound_concurrency(database_url: str) -> None:
    """AC-0206-1."""
    projects = [uuid.uuid4().hex[:8], uuid.uuid4().hex[:8]]
    jobs = [(WRITING, "writing", f"{projects[n % 2]}-w{n}") for n in range(50)]
    jobs += [(READONLY, "readonly", f"{projects[n % 2]}-r{n}") for n in range(20)]

    with running(database_url, queues=_lanes()) as runtime:
        assert set(runtime.queues) == {WRITING, READONLY}
        assert runtime.queues[WRITING].global_concurrency == 1

        def put(job: tuple[str, str, str]) -> WorkflowHandle[str]:
            queue, lane, record = job
            return enqueue(queue, record, lane_work, record, lane)

        with ThreadPoolExecutor(8) as pool:
            handles = list(pool.map(put, jobs))
        results = [handle.get_result() for handle in handles]

    assert sorted(results) == sorted(job[2] for job in jobs)
    assert _tracker.peak["writing"] == 1
    assert 1 <= _tracker.peak["readonly"] <= 3
    assert _tracker.projects["writing"] == set(projects)


@pytest.mark.integration
def test_writing_parent_must_not_wait_on_its_lane(database_url: str) -> None:
    """AC-0206-2."""
    with running(database_url, queues=_lanes()):
        enqueue(WRITING, "deadlock-1", waiting_parent, "deadlock-1")
        child = "deadlock-1.child"
        _wait_until(lambda: _status(child) is not None, timeout=10)
        # The parent holds the only writing slot, so its child never starts.
        assert not _wait_until(lambda: _status("deadlock-1") != "PENDING", timeout=3)
        assert _status(child) == "ENQUEUED"
        DBOS.cancel_workflow(child)
        DBOS.cancel_workflow("deadlock-1")

        handle = enqueue(WRITING, "turn-1", ending_parent, "turn-1")
        child_id = handle.get_result()
        assert DBOS.retrieve_workflow(child_id).get_result() == "turn-1.child"


@pytest.mark.integration
def test_lane_concurrency_follows_the_configuration(database_url: str) -> None:
    with running(database_url, queues=_lanes(writing=1)) as runtime:
        assert runtime.queues[WRITING].global_concurrency == 1
    with running(database_url, queues=_lanes(writing=2)) as runtime:
        assert runtime.queues[WRITING].global_concurrency == 2
        assert DBOS.retrieve_queue(WRITING) is not None
        with pytest.raises(ValueError, match="no lane or queue"):
            enqueue("lane.s2.writing", "w-1", lane_work, "w-1", "writing")


def test_lane_names_and_declarations() -> None:
    lane = LaneSpec(station="agent-host", lane="readonly", concurrency=LANE_SEEDS["readonly"])
    assert lane.queue_name == "lane.agent-host.readonly"
    assert dict(LANE_SEEDS) == {"writing": 1, "readonly": 4, "check": 1}
    gate = QueueSpec("delivery.gate", 1)
    assert [q.name for q in queue_specs([lane], [gate])] == ["lane.agent-host.readonly", gate.name]

    for station in ("", "Agent", "a.b", "a b"):
        with pytest.raises(ValidationError):
            LaneSpec(station=station, lane="writing", concurrency=1)
    with pytest.raises(ValidationError):
        LaneSpec(station="s1", lane="writing", concurrency=0)
    with pytest.raises(ValueError, match="are lanes"):
        queue_specs([], [QueueSpec("lane.s1.writing", 1)])
    with pytest.raises(ValueError, match="declared twice"):
        queue_specs([lane, lane])
    with pytest.raises(ValueError, match="declared twice"):
        queue_specs([], [gate, gate])
    for bad in (("", 1), (" q", 1), ("q", 0)):
        with pytest.raises(ValueError, match=r"empty or padded|at least 1"):
            QueueSpec(*bad)
    with pytest.raises(ValueError, match="positive polling"):
        QueueSpec("q", 1, 0)
