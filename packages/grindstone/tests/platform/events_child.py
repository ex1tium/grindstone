"""A stand-in control plane for AC-0314-1, run as a subprocess from the repository root.

    python -m packages.grindstone.tests.platform.events_child <database_url>

It starts the runtime, records one `factory.loaded` event (once: a restart
finds it), and runs one dispatcher pass for a consumer whose workflow records
an effect row. With `GRINDSTONE_KILL_AT=dispatch.after_start` it dies after
starting the consumer's workflow and before advancing the cursor, the first
time; the restart passes again and waits for the workflow's result.
"""

import sys

from dbos import DBOS
from packages.grindstone.tests.store.runtime_child import running

from grindstone.contracts.events import FactoryLoaded
from grindstone.platform.events import Consumer, Dispatcher, emit
from grindstone.store import Uow, transaction, unit_of_work, workflow

DIGEST = "sha256:" + "0" * 64


@transaction
def record_effect(uow: Uow, event_id: str) -> None:
    uow.execute("INSERT INTO scratch.deliveries (event_id) VALUES (:id)", {"id": event_id})


@workflow("test.events.deliver")
def deliver(event_id: str, envelope: str) -> str:
    del envelope
    record_effect(event_id)
    return event_id


CONSUMER = Consumer("probe", frozenset({"factory.loaded"}), deliver)


def _prepare(uow: Uow) -> str:
    uow.execute("CREATE SCHEMA IF NOT EXISTS scratch")
    uow.execute("CREATE TABLE IF NOT EXISTS scratch.deliveries (event_id text NOT NULL)")
    if uow.fetch_one("SELECT 1 FROM platform.events") is None:
        emit(uow, FactoryLoaded(factory="notes", version="0.1.0", manifest_hash=DIGEST))
    row = uow.fetch_one("SELECT event_id FROM platform.events ORDER BY seq LIMIT 1")
    if row is None:  # pragma: no cover - emitted just above
        raise RuntimeError("no event")
    return str(row["event_id"])


def main(database_url: str) -> int:
    with running(database_url):
        event_id = unit_of_work(_prepare)
        Dispatcher([CONSUMER]).pass_once()
        DBOS.retrieve_workflow(CONSUMER.workflow_id(event_id)).get_result()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
