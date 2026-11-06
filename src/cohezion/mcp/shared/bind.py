"""Where an MCP server is allowed to listen.

Every Cohezion MCP server used to bind ``0.0.0.0``. About half of them have no
authentication, so any host that could reach the machine could call their tools
(read files, spawn subprocesses, spend Kaggle submissions). This module is the one
place that decides the bind address:

* The default is loopback (``127.0.0.1``). Local agents and SSH/Cloudflare tunnels
  reach loopback, so nothing that runs on the same machine loses access. Loopback
  stops exposure to the network, not to a tunnel: a server you publish through a
  tunnel still needs its own API key.
* ``MCP_HOST`` overrides it, for example ``0.0.0.0`` inside a container.
* A non-loopback address is refused unless the server enforces an API key. The
  check fails closed: an unauthenticated server cannot be exposed by accident.
"""

from __future__ import annotations

import ipaddress
import os


DEFAULT_HOST = "127.0.0.1"


class UnsafeBindError(RuntimeError):
    """Raised when an unauthenticated server is asked to listen beyond loopback."""


def is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def bind_host(*, authenticated: bool, server_name: str = "MCP server") -> str:
    """Return the address to listen on, or raise ``UnsafeBindError``.

    ``authenticated`` must be True only when every non-health route of the server
    passes ``cohezion.mcp.shared.auth.api_key_middleware`` (or an equivalent that
    rejects requests when no key is configured).
    """
    host = (os.environ.get("MCP_HOST") or DEFAULT_HOST).strip()
    if not is_loopback(host) and not authenticated:
        raise UnsafeBindError(
            f"{server_name} has no authentication and refuses to listen on {host!r}. "
            "Unset MCP_HOST to listen on loopback, or put the server behind "
            "api_key_middleware first."
        )
    return host
