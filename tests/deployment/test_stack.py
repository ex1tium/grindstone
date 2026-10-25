"""SPEC-05, TKT-0501: security tests against the running Compose stack (`make smoke`).

They run only with `GRINDSTONE_COMPOSE_STACK=1`, which `make smoke` sets once
the stack is healthy, on the host that runs it (they read `secrets/`). A
user is impersonated the way the agent host will start agents: a root
`docker compose exec` followed by `setpriv` to that user with no
capabilities. No secret value is ever printed; contents are compared by
SHA-256.

`test_secret_originals_keep_host_owner_and_mode` answers OQ-0501 on the host
it runs on: whether Docker presents 0600 secret files to containers with
their owner and mode, so that only the entrypoint's DAC_READ_SEARCH reads
them.
"""

import hashlib
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
SECRETS_DIR = Path(os.environ.get("GRINDSTONE_SECRETS_DIR", ROOT / "secrets"))
PROJECT = os.environ.get("GRINDSTONE_COMPOSE_PROJECT", "grindstone")

pytestmark = pytest.mark.skipif(
    os.environ.get("GRINDSTONE_COMPOSE_STACK") != "1",
    reason="needs the running stack: make smoke sets GRINDSTONE_COMPOSE_STACK=1",
)

SERVICE_USER = {"grindstone": "grindstone", "agent-host": "gs-host", "runner": "gs-runner"}
COPY_DIR = {"grindstone": "/run/gs", "agent-host": "/run/gs-host"}
AGENT_USERS = tuple(f"gs-agent-{n}" for n in range(1, 9))
OTHER_USERS = {"grindstone": ("nobody",), "agent-host": AGENT_USERS}
"""Users in each container that must read no secret: the agent pool, or anyone else."""

SECRET_TABLE: dict[str, tuple[str, ...]] = {
    "postgres_password": ("grindstone",),
    "mcp_token_key": ("grindstone",),
    "host_control_key": ("grindstone", "agent-host"),
    "host_event_key": ("grindstone", "agent-host"),
    "session_key": ("grindstone",),
    "operator_password_hash": ("grindstone",),
    "github_app_key": ("grindstone",),
    "claude_oauth_token": ("agent-host",),
}
"""SPEC-05's secret table without `postgres`, whose official entrypoint reads its own."""

CAP_SETUID_SETGID = 0xC0
CAP_FIELDS = ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb")


def _exec(service: str, *command: str, user: str | None = None) -> subprocess.CompletedProcess[str]:
    as_user = ("-u", user) if user else ()
    return subprocess.run(
        ["docker", "compose", "-p", PROJECT, "exec", "-T", *as_user, service, *command],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def _as(service: str, user: str, *command: str) -> subprocess.CompletedProcess[str]:
    """`command` as `user` with every capability set empty, as the host starts an agent."""
    if service == "runner":  # no capability to switch users; exec as its user directly
        return _exec(service, *command, user=user)
    setpriv = (
        "setpriv",
        f"--reuid={user}",
        f"--regid={user}",
        "--init-groups",
        "--inh-caps=-all",
        "--ambient-caps=-all",
        "--bounding-set=-all",
        "--",
    )
    return _exec(service, *setpriv, *command)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _secrets_of(service: str) -> list[str]:
    return [name for name, services in SECRET_TABLE.items() if service in services]


def _caps(status: str) -> dict[str, int]:
    fields = dict(line.split(":\t", 1) for line in status.splitlines() if ":\t" in line)
    return {name: int(fields[name], 16) for name in CAP_FIELDS}


@pytest.mark.parametrize("service", ["grindstone", "agent-host"])
def test_secret_originals_keep_host_owner_and_mode(service: str) -> None:
    """OQ-0501: each mounted original shows the host file's owner and mode 0600."""
    for name in _secrets_of(service):
        host = (SECRETS_DIR / name).stat()
        shown = _exec(service, "stat", "-c", "%a %u", f"/run/secrets/{name}")
        assert shown.returncode == 0, shown.stderr
        assert shown.stdout.split() == ["600", str(host.st_uid)], name


@pytest.mark.parametrize("service", ["grindstone", "agent-host"])
def test_secrets_readable_only_by_their_user(service: str) -> None:
    """AC-0502-1, for the containers that hold secrets."""
    user, copies = SERVICE_USER[service], COPY_DIR[service]
    directory = _exec(service, "stat", "-c", "%U %a", copies)
    assert directory.stdout.split() == [user, "700"]
    for name in _secrets_of(service):
        original, copy = f"/run/secrets/{name}", f"{copies}/{name}"
        assert _as(service, user, "cat", original).returncode != 0, original
        shown = _exec(service, "stat", "-c", "%U %a", copy)
        assert shown.stdout.split() == [user, "600"], copy
        read = _as(service, user, "sha256sum", copy)
        assert read.returncode == 0, copy
        assert read.stdout.split()[0] == _digest(SECRETS_DIR / name), copy
        for other in OTHER_USERS[service]:
            assert _as(service, other, "cat", copy).returncode != 0, (other, copy)
            assert _as(service, other, "cat", original).returncode != 0, (other, original)


def test_runner_has_only_loopback() -> None:
    """AC-0502-1, for the runner: no network interface but loopback, and no secret."""
    interfaces = _exec("runner", "ls", "/sys/class/net")
    assert interfaces.returncode == 0, interfaces.stderr
    assert interfaces.stdout.split() == ["lo"]
    assert _exec("runner", "ls", "/run/secrets").returncode != 0


def test_process_capabilities() -> None:
    """AC-0504-1: services hold no capability; the host exactly CAP_SETUID and CAP_SETGID.

    Agents are started here as TKT-0502's helper will start them; that ticket
    checks them again through the helper itself.
    """
    for service in ("grindstone", "runner"):
        status = _exec(service, "cat", "/proc/1/status")
        assert status.returncode == 0, status.stderr
        assert f"Uid:\t{_uid(service)}\t" in status.stdout, service
        assert _caps(status.stdout) == dict.fromkeys(CAP_FIELDS, 0), service

    listing = _exec("agent-host", "sh", "-c", "echo /proc/[0-9]*/status")
    statuses = [_exec("agent-host", "cat", path).stdout for path in listing.stdout.split()]
    host = [status for status in statuses if f"\nUid:\t{_uid('agent-host')}\t" in status]
    assert host, "no host process running as gs-host"
    for status in host:
        assert _caps(status) == dict.fromkeys(CAP_FIELDS, CAP_SETUID_SETGID)

    for agent in AGENT_USERS[:2]:
        own = _as("agent-host", agent, "cat", "/proc/self/status")
        assert own.returncode == 0, own.stderr
        assert _caps(own.stdout) == dict.fromkeys(CAP_FIELDS, 0), agent


def _uid(service: str) -> int:
    return {"grindstone": 10001, "agent-host": 10002, "runner": 10003}[service]


def _http_status(service: str, url: str) -> int | str:
    """The HTTP status of a GET from inside `service`, or the connection error's name."""
    script = (
        f"fetch({json.dumps(url)}).then(r => console.log(r.status),"
        " e => console.log(e.cause?.code ?? e.name))"
    )
    result = _exec(service, "node", "-e", script, user=SERVICE_USER[service])
    out = result.stdout.strip()
    return int(out) if out.isdigit() else out


def _host_status(path: str) -> int:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:8080{path}", timeout=5) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code


def test_listeners_are_separated() -> None:
    """AC-0512-1."""
    # The operator listener refuses the stations' network, and serves the operator.
    assert _http_status("agent-host", "http://grindstone:8080/readyz") == 403
    assert _host_status("/readyz") == 200
    # The station endpoints are not served on the operator listener.
    assert _host_status("/kernel/mcp") == 404
    assert _host_status("/stations/host/events") == 404
    # REST is not served on the station listener, which the stations reach.
    assert _http_status("agent-host", "http://grindstone:8081/readyz") == 404
    assert _http_status("agent-host", "http://grindstone:8081/healthz") == 404
    # The station listener is never published.
    with pytest.raises(OSError):  # noqa: PT011 - refused, reset or timed out
        urllib.request.urlopen("http://127.0.0.1:8081/healthz", timeout=3)
