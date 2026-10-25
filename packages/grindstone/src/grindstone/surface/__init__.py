"""Edge layer. Every way in: the REST API and event stream, the kernel MCP
server, operator authentication and the AHP attach proxy (ADR-06, ADR-16).
"""

from grindstone.surface.health import health_router
from grindstone.surface.listeners import Listeners, parse_networks, separate_listeners

__all__ = ["Listeners", "health_router", "parse_networks", "separate_listeners"]
