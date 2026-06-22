"""Shared utilities for MCP servers."""

from .logging import VaultLogger, get_logger
from .session import SessionManager, get_session_manager


__all__ = [
    "MCPClient",
    "SessionManager",
    "VaultLogger",
    "get_logger",
    "get_session_manager",
]

import contextlib

# Wiring-sweep 2026-06-22: client and auth were import-graph orphans.
with contextlib.suppress(Exception):
    from cohezion.mcp.shared.client import MCPClient as MCPClient

with contextlib.suppress(Exception):
    from cohezion.mcp.shared.auth import get_api_key as get_api_key
