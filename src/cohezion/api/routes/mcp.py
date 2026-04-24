"""MCP registry routes — server / tool listings.

Extracted from api/__init__.py (Wave 2B of synthetic-sniffing-panda).
"""

from __future__ import annotations

from fastapi import APIRouter

from cohezion.mcp.registry import get_registry


mcp_router = APIRouter(tags=["mcp"])


@mcp_router.get("/mcp/servers")
async def list_servers():
    """List all available MCP servers."""
    registry = get_registry()
    return {
        "servers": [
            {"name": s.name, "type": s.type, "status": s.status} for s in registry.list_servers()
        ]
    }


@mcp_router.get("/mcp/tools")
async def list_tools():
    """List all available MCP tools."""
    registry = get_registry()
    return {"tools": registry.list_tools()}
