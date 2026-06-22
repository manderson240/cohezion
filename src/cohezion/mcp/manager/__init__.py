"""MCP server manager — lifecycle and routing."""

import contextlib

# Wiring-sweep 2026-06-22: mcp/manager orphan modules.
with contextlib.suppress(Exception):
    from cohezion.mcp.manager.server_manager import (
        MCPServerManager as MCPServerManager,
    )

with contextlib.suppress(Exception):
    from cohezion.mcp.manager.models import MCPServerConfig as MCPServerConfig
    from cohezion.mcp.manager.models import PortAllocator as PortAllocator

with contextlib.suppress(Exception):
    from cohezion.mcp.manager.auth import (
        generate_ephemeral_token as generate_ephemeral_token,
    )
    from cohezion.mcp.manager.auth import validate_token as validate_token
