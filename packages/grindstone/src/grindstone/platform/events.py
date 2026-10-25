"""The event outbox and its dispatcher (SPEC-03, REQ-0313, REQ-0314, REQ-0319).

- `emit(uow, event, project)` records an event in the caller's unit of work:
  the next sequence number of the project's stream comes from an upsert on
  `platform.event_seq`, so numbers are gapless and serialized with the change
  the event describes, and a rolled-back unit of work leaves no event and no
  gap. `pg_notify` is transactional, so `platform_events` is signalled only
  at commit.
- The `Dispatcher` holds the consumers the composition root registers. Each
  pass reads the events after each consumer's cursor and, for each event of
  the consumer's types, starts the workflow `evt-<consumer>-<event_id>` and
  then advances the cursor. A crash between the two repeats a start, which
  the store ignores for an existing ID (SPEC-02), so each consumer receives
  each event exactly once (DEC-0305).
- Two events for one consumer can run concurrently, so a consumer reads
  current state through its owner's interface and does nothing when the
  state has moved on (REQ-0319).
"""

import logging
import threading
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import psycopg
from pydantic import TypeAdapter

from grindstone.contracts.base import Contract
from grindstone.contracts.events import (
    INSTANCE_STREAM,
    KERNEL_EVENT_MODELS,
    EventEnvelope,
    KernelEvent,
)
from grindstone.contracts.ids import new_record_id
from grindstone.store import StoreError, Uow, kill_point, start, unit_of_work

_log = logging.getLogger(__name__)

CHANNEL = "platform_events"
"""The notification channel signalled at the commit of every unit of work that emits."""

_BATCH = 500
_ENVELOPE_FIELDS = frozenset({"type", "schema_version"})
_EVENT_TYPES: Mapping[str, type[Contract]] = MappingProxyType(
    {model.model_fields["type"].default: model for model in KERNEL_EVENT_MODELS}
)
_kernel_event: TypeAdapter[KernelEvent] = TypeAdapter(KernelEvent)

type ConsumerWorkflow = Callable[[str, str], Any]
"""A registered workflow taking the event ID (its record) and the envelope as JSON."""


def emit(uow: Uow, event: Contract, project: uuid.UUID = INSTANCE_STREAM) -> EventEnvelope:
    """Record `event` in `project`'s stream, in the caller's unit of work (REQ-0313).

    `event` must be one of the kernel's event models. Without a project the
    event goes to the instance's own stream.
    """
    event_type = _event_type(event)
    seq = uow.fetch_one(
        "INSERT INTO platform.event_seq (project, last_seq) VALUES (:project, 1)"
        " ON CONFLICT (project) DO UPDATE SET last_seq = platform.event_seq.last_seq + 1"
        " RETURNING last_seq",
        {"project": project},
    )
    if seq is None:  # pragma: no cover - the upsert always returns a row
        raise RuntimeError(f"no sequence number for {project}")
    row = uow.fetch_one(
        "INSERT INTO platform.events"
        " (project, seq, event_id, type, schema_version, payload)"
        " VALUES (:project, :seq, :event_id, :type, :schema_version, CAST(:payload AS jsonb))"
        " RETURNING event_id, project, seq, type, schema_version AS event_version,"
        " occurred_at, payload",
        {
            "project": project,
            "seq": seq["last_seq"],
            "event_id": new_record_id(),
            "type": event_type,
            "schema_version": getattr(event, "schema_version", 1),
            "payload": event.model_dump_json(exclude=set(_ENVELOPE_FIELDS)),
        },
    )
    if row is None:  # pragma: no cover - the insert always returns a row
        raise RuntimeError(f"event {project}:{seq['last_seq']} not recorded")
    uow.execute(
        "SELECT pg_notify(:channel, :project)", {"channel": CHANNEL, "project": str(project)}
    )
    return EventEnvelope.model_validate(dict(row))


def events_after(
    uow: Uow, project: uuid.UUID, seq: int, *, limit: int = _BATCH
) -> list[EventEnvelope]:
    """`project`'s events after sequence number `seq`, in order."""
    rows = uow.fetch_all(
        "SELECT event_id, project, seq, type, schema_version AS event_version,"
        " occurred_at, payload FROM platform.events WHERE project = :project AND seq > :seq"
        " ORDER BY seq LIMIT :limit",
        {"project": project, "seq": seq, "limit": limit},
    )
    return [EventEnvelope.model_validate(dict(row)) for row in rows]


def decode(envelope: EventEnvelope) -> KernelEvent:
    """The event model an envelope carries."""
    return _kernel_event.validate_python(
        {**envelope.payload, "type": envelope.type, "schema_version": envelope.event_version}
    )


@dataclass(frozen=True, slots=True)
class Consumer:
    """A module's consumer: the event types it receives and the workflow each starts."""

    name: str
    types: frozenset[str]
    workflow: ConsumerWorkflow

    def workflow_id(self, event_id: uuid.UUID | str) -> str:
        return f"evt-{self.name}-{event_id}"


class Dispatcher:
    """The consumers registered at the composition root, and the passes that feed them."""

    def __init__(self, consumers: Iterable[Consumer] = ()) -> None:
        self._consumers: dict[str, Consumer] = {}
        for consumer in consumers:
            self.consume(consumer.name, consumer.types, consumer.workflow)

    @property
    def consumers(self) -> Sequence[Consumer]:
        return tuple(self._consumers.values())

    def consume(self, name: str, types: Iterable[str], workflow: ConsumerWorkflow) -> None:
        """Register consumer `name` for the event types `types` (`platform.consume`)."""
        wanted = frozenset(types)
        if not name or "-" in name:
            raise ValueError(f"consumer name {name!r} must be non-empty and contain no '-'")
        if name in self._consumers:
            raise ValueError(f"consumer {name!r} is already registered")
        unknown = sorted(wanted - _EVENT_TYPES.keys())
        if unknown:
            raise ValueError(f"consumer {name!r} names unknown event types {unknown}")
        self._consumers[name] = Consumer(name, wanted, workflow)

    def pass_once(self) -> int:
        """Dispatch every event after each consumer's cursor; return how many started."""
        started = 0
        for project in unit_of_work(_streams):
            for consumer in self._consumers.values():
                started += self._dispatch(consumer, project)
        return started

    def _dispatch(self, consumer: Consumer, project: uuid.UUID) -> int:
        started = 0
        while True:
            batch = unit_of_work(lambda uow: _pending(uow, consumer.name, project))
            if not batch:
                return started
            for envelope in batch:
                if envelope.type not in consumer.types:
                    continue
                start(
                    consumer.workflow_id(envelope.event_id),
                    consumer.workflow,
                    str(envelope.event_id),
                    envelope.model_dump_json(),
                )
                started += 1
                kill_point("dispatch.after_start")
                _advance(consumer.name, project, envelope.seq)
            _advance(consumer.name, project, batch[-1].seq)

    def run(self, conninfo: str, stop: threading.Event, *, poll_seconds: float = 1.0) -> None:
        """Pass until `stop` is set, woken by `platform_events` or every `poll_seconds`.

        Runs in a thread of its own: the store's starts are synchronous calls,
        which DBOS refuses on the event loop. A failed pass or a lost
        connection is logged and retried after `poll_seconds`.
        """
        while not stop.is_set():
            try:
                with psycopg.connect(conninfo, autocommit=True) as conn:
                    conn.execute(f"LISTEN {CHANNEL}")
                    while not stop.is_set():
                        self._pass_logged()
                        for _ in conn.notifies(timeout=poll_seconds, stop_after=1):
                            pass
            except psycopg.OperationalError as exc:
                # The class name is enough to diagnose; the message may carry connection details.
                _log.warning("event dispatcher lost its connection (%s)", type(exc).__name__)
                stop.wait(poll_seconds)

    def _pass_logged(self) -> None:
        try:
            self.pass_once()
        except StoreError as exc:
            _log.warning("event dispatch paused: %s", exc.code)
        except Exception:  # noqa: BLE001 - a failed pass is retried; the loop must survive it
            _log.exception("event dispatch pass failed")


class DispatcherThread:
    """The dispatcher's thread, started and stopped by the lifespan."""

    def __init__(self, dispatcher: Dispatcher, conninfo: str, *, poll_seconds: float = 1.0) -> None:
        self._conninfo = conninfo
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=dispatcher.run,
            args=(conninfo, self._stop),
            kwargs={"poll_seconds": poll_seconds},
            name="event-dispatcher",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        """Stop after the pass in progress; a notification wakes a waiting listener."""
        self._stop.set()
        try:
            with psycopg.connect(self._conninfo, autocommit=True) as conn:
                conn.execute(f"NOTIFY {CHANNEL}")
        except psycopg.OperationalError:
            pass  # the listener wakes at its next poll instead
        self._thread.join(timeout)


def _event_type(event: Contract) -> str:
    event_type = getattr(event, "type", None)
    if not isinstance(event_type, str) or _EVENT_TYPES.get(event_type) is not type(event):
        raise TypeError(f"{type(event).__name__} is not a registered event model")
    return event_type


def _streams(uow: Uow) -> list[uuid.UUID]:
    return [row["project"] for row in uow.fetch_all("SELECT project FROM platform.event_seq")]


def _pending(uow: Uow, consumer: str, project: uuid.UUID) -> list[EventEnvelope]:
    """The next batch of `project`'s events after `consumer`'s cursor."""
    return events_after(uow, project, _cursor(uow, consumer, project))


def _cursor(uow: Uow, consumer: str, project: uuid.UUID) -> int:
    row = uow.fetch_one(
        "SELECT seq FROM platform.event_cursors WHERE consumer = :consumer AND project = :project",
        {"consumer": consumer, "project": project},
    )
    return 0 if row is None else int(row["seq"])


def _advance(consumer: str, project: uuid.UUID, seq: int) -> None:
    unit_of_work(
        lambda uow: uow.execute(
            "INSERT INTO platform.event_cursors (consumer, project, seq)"
            " VALUES (:consumer, :project, :seq)"
            " ON CONFLICT (consumer, project)"
            " DO UPDATE SET seq = GREATEST(platform.event_cursors.seq, EXCLUDED.seq)",
            {"consumer": consumer, "project": project, "seq": seq},
        )
    )
