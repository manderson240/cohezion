"""Swarm MCP Server - Model Context Protocol wrapper for SLM swarm debate workflows."""

import logging
from typing import Any

from fastmcp import FastMCP

from cohezion.mcp.swarm_server import get_server


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("swarm-mcp")

# Initialize FastMCP server
app = FastMCP("cohezion-swarm")


@app.tool()
async def run_debate(
    query: str,
    perspectives: list[str] | None = None,
) -> dict[str, Any]:
    """Execute a full SLM swarm debate workflow on a query.

    Args:
        query: The topic or question to debate
        perspectives: Optional list of perspective names (e.g., 'ARCHITECT', 'ENGINEER', 'CRITIC')
    """
    server = get_server()
    return await server.run_debate(query, perspectives)


@app.tool()
async def get_perspectives() -> list[dict[str, str]]:
    """Get list of available analyst perspectives in the swarm."""
    server = get_server()
    return server.get_perspectives()


@app.tool()
async def get_swarm_metrics() -> dict[str, Any]:
    """Get metrics about the current swarm workflow state."""
    server = get_server()
    return server.get_metrics()


if __name__ == "__main__":
    # Always use stdio transport for CLI integration
    app.run(transport="stdio")
