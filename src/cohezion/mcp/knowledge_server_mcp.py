"""Knowledge MCP Server - Model Context Protocol wrapper for RAG over library and skills."""

import logging
from typing import Any

from fastmcp import FastMCP

from cohezion.mcp.knowledge_server import get_server


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("knowledge-mcp")

# Initialize FastMCP server
app = FastMCP("cohezion-knowledge")


@app.tool()
async def search_knowledge(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Semantic search over library documents and skill summaries.

    Args:
        query: Search term
        limit: Max results to return
    """
    server = get_server()
    return server.search_knowledge(query, limit)


@app.tool()
async def get_skill(skill_name: str) -> dict[str, Any]:
    """Retrieve the full content of a specific skill.

    Args:
        skill_name: Name of the skill to retrieve
    """
    server = get_server()
    return server.get_skill(skill_name)


@app.tool()
async def list_skills() -> list[str]:
    """List all available skill names in the knowledge graph."""
    server = get_server()
    return server.list_skills()


if __name__ == "__main__":
    # Always use stdio transport for CLI integration
    app.run(transport="stdio")
