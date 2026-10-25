"""Operator commands on workflows: `grindstone workflows list|fork`.

They talk only to DBOS's system tables, through `DBOSClient`, so they work
whether or not the control plane is running (SPK-2).

`fork_workflow` moves a workflow stranded under another application version
onto the current one (SPEC-02, DEC-0204). DBOS's own fork gives the copy a
new ID but not the original's mailbox, so a message sent to the original
and not yet received would be lost (SPK-2, experiment 8). The command
therefore, in order:

1. forks from the first step without a checkpoint, under a deterministic ID
   `<id>@<version>`, so a repeated command finds its earlier fork;
2. copies the original's unreceived messages to the fork, each once;
3. cancels the original, so an old image that starts again cannot also run it.

Every step can be repeated, so a command interrupted part-way is run again.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from dbos import DBOSClient, SetWorkflowID
from sqlalchemy import URL, Engine, text

from grindstone.store.database import create_engine
from grindstone.store.runtime import APP_NAME, SYSTEM_SCHEMA, WORKFLOW_VERSION

_UNFINISHED = ("PENDING", "ENQUEUED")

# DBOS's schema is exempt from table ownership (REQ-0215): DBOS writes it, and
# only this command copies rows inside it. A copied message gets an ID derived
# from the original's, so copying twice inserts it once.
_COPY_MESSAGES = """
INSERT INTO dbos.notifications (destination_uuid, topic, message, serialization, message_uuid)
SELECT :fork, topic, message, serialization, message_uuid || '@' || :version
FROM dbos.notifications
WHERE destination_uuid = :original AND NOT consumed
ON CONFLICT (message_uuid) DO NOTHING
"""


@dataclass(frozen=True, slots=True)
class WorkflowSummary:
    """One unfinished workflow, as `grindstone workflows list` prints it."""

    workflow_id: str
    name: str
    status: str
    version: str | None
    stranded: bool


def fork_id(workflow_id: str, version: str) -> str:
    """The ID a workflow's fork onto `version` gets."""
    return f"{workflow_id}@{version}"


def list_workflows(url: URL | str, *, version: str = WORKFLOW_VERSION) -> list[WorkflowSummary]:
    """Every unfinished workflow, each marked stranded when its version is not `version`."""
    engine = create_engine(url)
    client = _client(engine)
    try:
        unfinished = client.list_workflows(
            status=list(_UNFINISHED), load_input=False, load_output=False
        )
    finally:
        client.destroy()
        engine.dispose()
    return [
        WorkflowSummary(
            workflow_id=w.workflow_id,
            name=w.name,
            status=w.status,
            version=w.app_version,
            stranded=w.app_version != version,
        )
        for w in sorted(unfinished, key=lambda w: w.workflow_id)
    ]


def fork_workflow(
    url: URL | str,
    workflow_id: str,
    *,
    version: str = WORKFLOW_VERSION,
    start_step: int | None = None,
) -> str:
    """Move a stranded workflow onto `version` and return its fork's ID.

    `start_step` defaults to the first step without a checkpoint, so every
    completed step is copied and none runs again. Refuses a workflow that is
    finished or already on `version`.
    """
    engine = create_engine(url)
    client = _client(engine)
    target = fork_id(workflow_id, version)
    try:
        found = client.list_workflows(
            workflow_ids=[workflow_id], load_input=False, load_output=False
        )
        if not found:
            raise LookupError(f"no workflow {workflow_id!r}")
        original = found[0]
        forked = bool(
            client.list_workflows(workflow_ids=[target], load_input=False, load_output=False)
        )
        if not forked:
            if original.status not in _UNFINISHED:
                raise ValueError(f"workflow {workflow_id!r} is {original.status}, not stranded")
            if original.app_version == version:
                raise ValueError(f"workflow {workflow_id!r} already runs on version {version}")
            if start_step is None:
                steps = client.list_workflow_steps(workflow_id, load_output=False)
                start_step = first_open_step([s["function_id"] for s in steps])
            with SetWorkflowID(target):
                client.fork_workflow(workflow_id, start_step, application_version=version)
        with engine.begin() as conn:
            conn.execute(
                text(_COPY_MESSAGES),
                {"fork": target, "original": workflow_id, "version": version},
            )
        if original.status in _UNFINISHED:
            client.cancel_workflow(workflow_id)
    finally:
        client.destroy()
        engine.dispose()
    return target


def first_open_step(checkpointed: Sequence[int]) -> int:
    """The lowest step ID, counting from 1, that has no checkpoint.

    A wait may checkpoint a later ID (its timeout) before its own, so the
    first gap, not the highest ID, is where the workflow stands.
    """
    done = set(checkpointed)
    step = 1
    while step in done:
        step += 1
    return step


def _client(engine: Engine) -> DBOSClient:
    return DBOSClient(
        system_database_engine=engine,
        dbos_system_schema=SYSTEM_SCHEMA,
        application_name=APP_NAME,
    )
