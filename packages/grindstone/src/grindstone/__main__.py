"""Run the control plane: `python -m grindstone`.

`python -m grindstone workflows list` prints every unfinished workflow and
marks those stranded under another version; `python -m grindstone workflows
fork <id>` moves a stranded one onto this version (SPEC-02, REQ-0207).
"""

import argparse
import os
import sys
from collections.abc import Sequence

import uvicorn

from grindstone.app import create_app
from grindstone.store import WORKFLOW_VERSION, DatabaseSettings, fork_workflow, list_workflows


def main(argv: Sequence[str] | None = None) -> int:
    """Run a command, or serve on `GRINDSTONE_HTTP_HOST`:`GRINDSTONE_HTTP_PORT`."""
    args = _parser().parse_args(argv)
    if args.command == "workflows":
        return _workflows(args)
    uvicorn.run(
        create_app(),
        host=os.environ.get("GRINDSTONE_HTTP_HOST", "127.0.0.1"),
        port=int(os.environ.get("GRINDSTONE_HTTP_PORT", "8080")),
        log_config=None,
        server_header=False,
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="grindstone")
    commands = parser.add_subparsers(dest="command")
    workflows = commands.add_parser("workflows", help="inspect and move durable workflows")
    actions = workflows.add_subparsers(dest="action", required=True)
    listing = actions.add_parser("list", help="unfinished workflows, marking stranded ones")
    fork = actions.add_parser("fork", help="move a stranded workflow onto this version")
    fork.add_argument("workflow_id")
    fork.add_argument(
        "--step", type=int, default=None, help="step to fork from (default: first open)"
    )
    for action in (listing, fork):
        action.add_argument(
            "--version", default=WORKFLOW_VERSION, help="the current workflow version"
        )
    return parser


def _workflows(args: argparse.Namespace) -> int:
    url = DatabaseSettings.from_env().url()
    version: str = args.version
    if args.action == "list":
        for w in list_workflows(url, version=version):
            mark = "  stranded" if w.stranded else ""
            sys.stdout.write(f"{w.workflow_id}\t{w.name}\t{w.status}\tv{w.version}{mark}\n")
        return 0
    forked = fork_workflow(url, args.workflow_id, version=version, start_step=args.step)
    sys.stdout.write(f"forked {args.workflow_id} onto version {version} as {forked}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
