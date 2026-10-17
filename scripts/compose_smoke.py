"""M0-01 smoke test against a running stack (`make smoke`).

Checks that the four services are healthy; that each container mounts
exactly the volumes ADR-01 allows and nothing else (no host paths beyond its
secrets, never the Docker socket); that the control plane is ready; and that
the networks isolate the stations: neither station can reach PostgreSQL, the
runner cannot reach the control plane, and the agent host can.
"""

import json
import subprocess
import sys
import urllib.request
from typing import Any, NamedTuple

PROJECT = "grindstone"
ALLOWED_VOLUMES: dict[str, set[str]] = {
    "postgres": {"pgdata"},
    "grindstone": {"blobs", "repos", "workspaces", "runs"},
    "agent-host": {"workspaces"},
    "runner": {"runs"},
}
SECRET_TARGETS: dict[str, set[str]] = {
    "postgres": {"/run/secrets/postgres_password"},
    "grindstone": {"/run/secrets/postgres_password"},
    "agent-host": set(),
    "runner": set(),
}


class Probe(NamedTuple):
    """A TCP connection attempt from inside one service."""

    service: str
    host: str
    port: int
    should_reach: bool

    def command(self) -> list[str]:
        if self.service == "agent-host":
            js = (
                f"require('net').connect({self.port},'{self.host}')"
                ".on('connect',()=>process.exit(0)).on('error',()=>process.exit(1))"
            )
            return ["node", "-e", js]
        py = f"import socket; socket.create_connection(('{self.host}', {self.port}), 3)"
        return ["python", "-c", py]


PROBES = [
    Probe("agent-host", "postgres", 5432, should_reach=False),
    Probe("agent-host", "grindstone", 8080, should_reach=True),
    Probe("runner", "postgres", 5432, should_reach=False),
    Probe("runner", "grindstone", 8080, should_reach=False),
]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=False, timeout=60)


def _containers() -> dict[str, dict[str, Any]]:
    ids = _run("docker", "compose", "-p", PROJECT, "ps", "-q").stdout.split()
    inspected: list[dict[str, Any]] = (
        json.loads(_run("docker", "inspect", *ids).stdout) if ids else []
    )
    return {c["Config"]["Labels"]["com.docker.compose.service"]: c for c in inspected}


def _container_problems(service: str, container: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    health = container["State"].get("Health", {}).get("Status")
    if health != "healthy":
        problems.append(f"{service}: health is {health!r}")
    volumes: set[str] = set()
    mounts: list[dict[str, str]] = container["Mounts"]
    for mount in mounts:
        if "docker.sock" in mount.get("Source", "") + mount.get("Destination", ""):
            problems.append(f"{service}: mounts the Docker socket")
        if mount["Type"] == "volume":
            volumes.add(mount["Name"].removeprefix(f"{PROJECT}_"))
        elif mount["Type"] == "bind" and mount["Destination"] not in SECRET_TARGETS[service]:
            problems.append(f"{service}: unexpected bind mount {mount['Destination']}")
    if volumes != ALLOWED_VOLUMES[service]:
        problems.append(
            f"{service}: volumes {sorted(volumes)} != {sorted(ALLOWED_VOLUMES[service])}"
        )
    return problems


def check() -> list[str]:
    problems: list[str] = []
    containers = _containers()
    for service in ALLOWED_VOLUMES:
        if service not in containers:
            problems.append(f"{service}: not running")
        else:
            problems.extend(_container_problems(service, containers[service]))

    try:
        with urllib.request.urlopen("http://127.0.0.1:8080/readyz", timeout=5) as resp:
            body: dict[str, Any] = json.load(resp)
        if body.get("status") != "ok":
            problems.append(f"grindstone: readyz reports {body}")
    except OSError as exc:
        problems.append(f"grindstone: readyz unreachable from the host ({exc})")

    for probe in PROBES:
        exec_args = ("docker", "compose", "-p", PROJECT, "exec", "-T", probe.service)
        reached = _run(*exec_args, *probe.command()).returncode == 0
        if reached != probe.should_reach:
            verb = "cannot reach" if probe.should_reach else "can reach"
            problems.append(f"{probe.service}: {verb} {probe.host}:{probe.port}")
    return problems


def main() -> int:
    problems = check()
    for p in problems:
        print(f"M0-01 {p}")
    print(f"M0-01 compose smoke: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
