"""The control plane's two listeners (SPEC-05, REQ-0512).

One process serves operators and stations on separate ports. The operator
listener serves REST, the event stream and the UI, and refuses any peer in
the stations' or the database's network; the station listener, never
published, serves only the kernel MCP surface and the host event endpoint.
`separate_listeners` wraps the application and routes each connection by
the local port it arrived on, so one lifespan serves both.
"""

import ipaddress
import json
from collections.abc import Awaitable, Callable, MutableMapping, Sequence
from dataclasses import dataclass
from typing import Any

type Scope = MutableMapping[str, Any]
type Message = MutableMapping[str, Any]
type Receive = Callable[[], Awaitable[Message]]
type Send = Callable[[Message], Awaitable[None]]
type ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]
type Network = ipaddress.IPv4Network | ipaddress.IPv6Network

STATION_PATHS = ("/kernel/mcp", "/stations/host/events")
"""What the station listener serves (SPEC-07 and SPEC-06 mount them)."""


def parse_networks(text: str) -> tuple[Network, ...]:
    """Comma-separated CIDR blocks, as `GRINDSTONE_OPERATOR_REFUSED_NETWORKS` holds them."""
    return tuple(ipaddress.ip_network(part.strip()) for part in text.split(",") if part.strip())


def is_station_path(path: str) -> bool:
    """A path the station listener serves: one of `STATION_PATHS` or below it."""
    return any(path == p or path.startswith(f"{p}/") for p in STATION_PATHS)


@dataclass(frozen=True, slots=True)
class Listeners:
    """The two ports and the peers the operator listener refuses."""

    operator_port: int
    station_port: int
    refused: tuple[Network, ...] = ()

    def refuses_peer(self, host: str | None) -> bool:
        """Whether a peer address lies in a refused network; an unparsable one is refused."""
        if host is None:
            return True
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return True
        return any(address in network for network in self.refused)


def separate_listeners(app: ASGIApp, listeners: Listeners) -> ASGIApp:
    """`app` behind the listener rules: each connection is judged by its local port.

    Lifespan events pass through. A connection on neither port is refused,
    so a third socket cannot open a way around the rules.
    """

    async def gate(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await app(scope, receive, send)
            return
        server: Sequence[Any] | None = scope.get("server")
        port = server[1] if server is not None else None
        path: str = scope.get("path", "")
        client: Sequence[Any] | None = scope.get("client")
        peer = str(client[0]) if client is not None else None
        if port == listeners.station_port:
            if is_station_path(path):
                await app(scope, receive, send)
            else:
                await _refuse(scope, send, 404, "Not Found")
        elif port == listeners.operator_port:
            if listeners.refuses_peer(peer):
                await _refuse(scope, send, 403, "Forbidden")
            elif is_station_path(path):
                await _refuse(scope, send, 404, "Not Found")
            else:
                await app(scope, receive, send)
        else:
            await _refuse(scope, send, 404, "Not Found")

    return gate


async def _refuse(scope: Scope, send: Send, status: int, detail: str) -> None:
    if scope["type"] == "websocket":
        await send({"type": "websocket.close", "code": 1008})
        return
    body = json.dumps({"detail": detail}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
