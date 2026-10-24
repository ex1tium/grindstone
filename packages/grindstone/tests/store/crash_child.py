"""A stand-in control plane for AC-0203-1, run as a subprocess.

It opens the store, launches DBOS and runs one workflow whose only database
step is a `@transaction` that records an effect row. With
`GRINDSTONE_TEST_KILL_AT` set to `before_commit` or `after_commit`, it kills
itself there the first time, leaving a marker file so the restart runs
through. On restart DBOS recovers the pending workflow and the child waits
for its result.

Usage: python crash_child.py <database_url>
"""

import os
import signal
import sys
from pathlib import Path

from dbos import DBOS, SetWorkflowID

from grindstone.store import Uow, open_database, transaction, unit_of_work

WORKFLOW_ID = "crash-transaction-1"
KILL_AT_ENV = "GRINDSTONE_TEST_KILL_AT"
MARKER_ENV = "GRINDSTONE_TEST_KILL_MARKER"


def _kill_point(name: str) -> None:
    """Die abruptly at `name`, once: no cleanup, no commit, no checkpoint."""
    marker = Path(os.environ[MARKER_ENV])
    if os.environ.get(KILL_AT_ENV) != name or marker.exists():
        return
    marker.write_text(name)
    if sys.platform != "win32":
        os.kill(os.getpid(), signal.SIGKILL)
    os._exit(137)


@transaction
def record_effect(uow: Uow, workflow_id: str) -> int:
    uow.execute("INSERT INTO scratch.effects (workflow_id) VALUES (:id)", {"id": workflow_id})
    _kill_point("before_commit")
    return 1


@DBOS.workflow()
def effect_workflow(workflow_id: str) -> int:
    recorded = record_effect(workflow_id)
    _kill_point("after_commit")
    return recorded


def _create_scratch(uow: Uow) -> None:
    uow.execute("CREATE SCHEMA IF NOT EXISTS scratch")
    uow.execute("CREATE TABLE IF NOT EXISTS scratch.effects (workflow_id text NOT NULL)")


def main(database_url: str) -> int:
    open_database(database_url)
    unit_of_work(_create_scratch)
    DBOS(
        config={
            "name": "grindstone-test",
            "system_database_url": database_url,
            "dbos_system_schema": "dbos",
            "application_version": "test",
        }
    )
    DBOS.launch()
    try:
        # On restart the workflow already exists and DBOS's recovery runs it.
        if DBOS.get_workflow_status(WORKFLOW_ID) is None:
            with SetWorkflowID(WORKFLOW_ID):
                DBOS.start_workflow(effect_workflow, WORKFLOW_ID)
        DBOS.retrieve_workflow(WORKFLOW_ID).get_result()
    finally:
        DBOS.destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
