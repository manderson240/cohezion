"""Shared utilities for MCP compound tools.

Eliminates the repeated patterns that bloat tool definitions:
- Error handling (16 identical try/except blocks)
- MCP client resolution (duped in 2+ tools)
- Response factories (consistent ok/error shape)
- Tool registration (declarative class-based)

Usage:
    from compound_utils import mcp_tool, ok, err, McpClientResolver

    @mcp_tool(mcp, description="...")
    async def my_tool(x: int) -> dict[str, Any]:
        return ok(value=x * 2)
"""

from __future__ import annotations

import functools
import inspect
import logging
from typing import Any, Awaitable, Callable, TypeVar


logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Awaitable[dict[str, Any]]])


def mcp_tool(mcp_instance: Any, *, description: str = "") -> Callable[[F], F]:
    """Decorator that registers an async function as an MCP tool.

    Wraps the handler in uniform error handling so every tool
    returns {"status": "...", ...} reliably without try/except duplication.
    Preserves the original function signature for FastMCP schema generation.
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            try:
                return await fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                logger.error("%s failed: %s", fn.__name__, exc)
                return err(str(exc))

        # Preserve exact signature for FastMCP JSON-schema generation
        wrapper.__signature__ = inspect.signature(fn)  # type: ignore[attr-defined]
        wrapper.__annotations__ = fn.__annotations__

        mcp_instance.tool(description=description or fn.__doc__ or "")(wrapper)
        return wrapper  # type: ignore[return-value]

    return decorator


def ok(**fields: Any) -> dict[str, Any]:
    """Build a success response with consistent shape."""
    return {"status": "success", **fields}


def err(message: str, **fields: Any) -> dict[str, Any]:
    """Build an error response with consistent shape."""
    return {"status": "error", "error": message, **fields}


class McpClientResolver:
    """Unified MCP client resolution across tools.

    Eliminates the duplicated "create fresh client if server_url is provided"
    pattern found in learning_capture and learning_process_execution.
    """

    def __init__(self, get_default_client: Callable[..., Any]) -> None:
        self._get_default = get_default_client

    async def resolve(self, server_url: str | None = None) -> tuple[Any, bool]:
        """Return (client, is_fresh).

        If server_url is provided, creates a new client and connects.
        Otherwise, returns the default shared client (best-effort connect).
        """
        import os

        from cohezion.core.mcp_client import create_mcp_client

        if server_url:
            api_key = os.getenv("CLOUD_VAULT_API_KEY", "cohezion-dev-key")
            client = create_mcp_client(server_url=server_url, api_key=api_key)
            await client.connect()
            return client, True

        client = self._get_default()
        try:
            await client.connect()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Default MCP client connect failed: %s", exc)
        return client, False
