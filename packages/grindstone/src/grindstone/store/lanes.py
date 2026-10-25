"""Lanes: one DBOS queue per station lane, and the other queues modules declare (REQ-0206).

A lane is the queue `lane.<station>.<lane>` with the global concurrency its
`LaneSpec` gives: writing work on a station runs one at a time by default,
read-only work in a small bounded number, checks one at a time (ADR-03).
Modules may declare further named queues with a concurrency (SPEC-08's
`delivery.gate`, concurrency 1); names beginning `lane.` are the lanes'.

The composition root combines both lists with `queue_specs` and passes the
result to `start_runtime`, which registers every queue after DBOS launches
and before anything is dispatched. The instance file is the authority on
concurrency, so a restart with a changed value updates the queue's stored
configuration.

A writing parent never waits on a child on its own lane: with concurrency 1
the child can never start while the parent holds the lane. It ends its turn
instead (ADR-14; SPK-2, experiment 7). SPEC-06 enforces this; the lane test
keeps the deadlock as a regression case.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from dbos import DBOS, Queue

from grindstone.contracts.store import LaneKind, LaneSpec

LANE_PREFIX = "lane."
LANE_SEEDS: Mapping[LaneKind, int] = MappingProxyType({"writing": 1, "readonly": 4, "check": 1})
"""The seed concurrency of each lane kind, matching the capacity envelope."""

QUEUE_POLLING_SECONDS = 1.0
"""How often DBOS looks for runnable workflows on each queue."""


@dataclass(frozen=True, slots=True)
class QueueSpec:
    """A queue to register: its name, its global concurrency, and how often DBOS polls it."""

    name: str
    concurrency: int
    polling_seconds: float = QUEUE_POLLING_SECONDS

    def __post_init__(self) -> None:
        if not self.name.strip() or self.name != self.name.strip():
            raise ValueError(f"queue name {self.name!r} is empty or padded")
        if self.concurrency < 1:
            raise ValueError(f"queue {self.name!r} needs a concurrency of at least 1")
        if self.polling_seconds <= 0:
            raise ValueError(f"queue {self.name!r} needs a positive polling interval")


def queue_specs(
    lanes: Sequence[LaneSpec],
    queues: Sequence[QueueSpec] = (),
    *,
    polling_seconds: float = QUEUE_POLLING_SECONDS,
) -> tuple[QueueSpec, ...]:
    """Every queue to register: the lanes under their names, then the modules' queues.

    Refuses a name given twice, and a module queue that takes a lane's prefix.
    """
    for queue in queues:
        if queue.name.startswith(LANE_PREFIX):
            raise ValueError(f"queue {queue.name!r}: names beginning {LANE_PREFIX!r} are lanes")
    specs = [QueueSpec(lane.queue_name, lane.concurrency, polling_seconds) for lane in lanes]
    specs += queues
    seen: set[str] = set()
    for spec in specs:
        if spec.name in seen:
            raise ValueError(f"queue {spec.name!r} is declared twice")
        seen.add(spec.name)
    return tuple(specs)


async def register_queues(specs: Sequence[QueueSpec]) -> Mapping[str, Queue]:
    """Register each queue with DBOS, from the event loop; returns them by name.

    Refuses a name given twice. The instance file is the authority on
    concurrency, so each registration overwrites the stored configuration.
    """
    if len({spec.name for spec in specs}) != len(specs):
        raise ValueError("a queue is declared twice")
    registered: dict[str, Queue] = {}
    for spec in specs:
        registered[spec.name] = await DBOS.register_queue_async(
            spec.name,
            global_concurrency=spec.concurrency,
            polling_interval_sec=spec.polling_seconds,
            on_conflict="always_update",
        )
    return MappingProxyType(registered)
