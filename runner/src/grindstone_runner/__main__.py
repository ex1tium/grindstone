"""Runner process: `python -m grindstone_runner [serve|healthcheck]`.

M0 scope: the process stays up, writes a heartbeat file, and exits cleanly
on SIGTERM. Picking up and executing job directories arrives with SPEC-08.
The runner exposes no network port; its health is the heartbeat's age.
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import threading
import time
from pathlib import Path
from types import FrameType

HEARTBEAT_INTERVAL_S = 5.0
HEARTBEAT_MAX_AGE_S = 30.0


def _default_heartbeat() -> Path:
    return Path(os.environ.get("GRINDSTONE_RUNNER_HEARTBEAT", "/tmp/grindstone-runner.heartbeat"))  # noqa: S108


def serve(runs_dir: Path, heartbeat: Path, stop: threading.Event) -> int:
    """Write a heartbeat until `stop` is set. Returns the process exit code."""
    if not runs_dir.is_dir():
        print(f"runs directory {runs_dir} does not exist", file=sys.stderr)  # noqa: T201
        return 2
    while not stop.is_set():
        tmp = heartbeat.with_suffix(".tmp")
        tmp.write_text(f"{time.time():.3f}\n")
        tmp.replace(heartbeat)  # atomic, so a reader never sees a partial file
        stop.wait(HEARTBEAT_INTERVAL_S)
    return 0


def healthcheck(heartbeat: Path, now: float | None = None) -> int:
    """Exit 0 when the heartbeat is fresher than `HEARTBEAT_MAX_AGE_S`."""
    try:
        written = float(heartbeat.read_text().strip())
    except (OSError, ValueError):
        return 1
    age = (time.time() if now is None else now) - written
    return 0 if 0 <= age <= HEARTBEAT_MAX_AGE_S else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="grindstone-runner")
    parser.add_argument("command", choices=["serve", "healthcheck"], nargs="?", default="serve")
    parser.add_argument(
        "--runs-dir", type=Path, default=Path(os.environ.get("GRINDSTONE_RUNS_DIR", "/runs"))
    )
    parser.add_argument("--heartbeat", type=Path, default=_default_heartbeat())
    args = parser.parse_args(argv)

    if args.command == "healthcheck":
        return healthcheck(args.heartbeat)

    stop = threading.Event()

    def _stop(_signum: int, _frame: FrameType | None) -> None:
        stop.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, _stop)
    return serve(args.runs_dir, args.heartbeat, stop)


if __name__ == "__main__":
    sys.exit(main())
