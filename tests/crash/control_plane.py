"""The control plane as the crash harness runs it, in a subprocess.

It starts the runtime as the lifespan does, imports the crash scenarios (so
it registers the same steps and workflows as the test process), starts the
scenario's workflow for its record unless it already exists, and waits for it.
After a kill, the restart finds the workflow pending and DBOS's recovery runs
it. Run from the repository root:

    python -m tests.crash.control_plane <database_url> <step> <version> [<wait>]

With <wait>, it starts nothing and waits for that workflow instead (a fork).
"""

import asyncio
import sys

from dbos import DBOS

from grindstone.store import registered_workflows, start, start_runtime, stop_runtime
from tests.crash.harness import load_scenarios


def main(argv: list[str]) -> int:
    database_url, step, version = argv[1:4]
    wait = argv[4] if len(argv) > 4 else None
    scenario = load_scenarios()[step]
    # DBOS makes its executor the loop's default one, so the loop outlives the runtime.
    with asyncio.Runner() as runner:
        runner.run(start_runtime(database_url, application_version=version))
        try:
            workflow_id = wait or scenario.workflow_id
            if wait is None and DBOS.get_workflow_status(workflow_id) is None:
                assert scenario.workflow in registered_workflows().values()
                start(workflow_id, scenario.workflow, scenario.record, *scenario.args)
            DBOS.retrieve_workflow(workflow_id).get_result()
        finally:
            runner.run(stop_runtime())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
