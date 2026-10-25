"""SPEC-05, REQ-0512: the operator and station listeners, judged by local port and peer.

The stack test `tests/deployment/test_stack.py::test_listeners_are_separated`
(AC-0512-1) checks the same rules on the running deployment.
"""

import asyncio
from typing import Any

import pytest

from grindstone.surface import Listeners, parse_networks, separate_listeners
from grindstone.surface.listeners import Message, Receive, Scope, Send

LISTENERS = Listeners(
    operator_port=8080,
    station_port=8081,
    refused=parse_networks("10.89.1.0/24, 10.89.2.0/24"),
)


async def _ok(scope: Scope, receive: Receive, send: Send) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": scope["path"].encode()})


def _status(port: int, path: str, peer: str = "10.89.3.1", kind: str = "http") -> Any:
    sent: list[Message] = []

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent.append(message)

    scope: Scope = {
        "type": kind,
        "path": path,
        "server": ("10.89.2.10", port),
        "client": (peer, 40000),
    }
    asyncio.run(separate_listeners(_ok, LISTENERS)(scope, receive, send))
    if kind == "websocket":
        return sent[0]["type"]
    return sent[0]["status"]


def test_operator_listener_serves_rest_and_refuses_station_networks() -> None:
    assert _status(8080, "/readyz") == 200
    assert _status(8080, "/readyz", peer="127.0.0.1") == 200
    assert _status(8080, "/readyz", peer="10.89.2.7") == 403
    assert _status(8080, "/readyz", peer="10.89.1.7") == 403
    assert _status(8080, "/readyz", peer="not-an-address") == 403
    assert _status(8080, "/stream", peer="10.89.2.7", kind="websocket") == "websocket.close"


@pytest.mark.parametrize("path", ["/kernel/mcp", "/kernel/mcp/x", "/stations/host/events"])
def test_station_paths_only_on_the_station_listener(path: str) -> None:
    assert _status(8080, path) == 404
    assert _status(8081, path, peer="10.89.2.7") == 200


def test_station_listener_serves_nothing_else() -> None:
    assert _status(8081, "/readyz", peer="10.89.2.7") == 404
    assert _status(8081, "/kernel/mcpx", peer="10.89.2.7") == 404
    assert _status(8081, "/stations/host/events-other", peer="10.89.2.7") == 404


def test_a_third_port_serves_nothing() -> None:
    assert _status(9000, "/readyz") == 404


def test_lifespan_passes_through() -> None:
    seen: list[str] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        seen.append(scope["type"])

    async def receive() -> Message:
        return {"type": "lifespan.startup"}

    async def send(message: Message) -> None:
        pass

    asyncio.run(separate_listeners(app, LISTENERS)({"type": "lifespan"}, receive, send))
    assert seen == ["lifespan"]
