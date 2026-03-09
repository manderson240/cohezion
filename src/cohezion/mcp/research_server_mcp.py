"""Research MCP Server - Model Context Protocol wrapper for research discovery."""

from typing import Any

from fastmcp import FastMCP

from cohezion.mcp.research_server import get_server


# Initialize FastMCP server
app = FastMCP("cohezion-research")


@app.tool()
async def search_arxiv(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search arXiv for research papers.

    Args:
        query: Search query
        limit: Max results
    """
    server = get_server()
    return server.search_arxiv(query, limit)


@app.tool()
async def get_hf_trending(limit: int = 5) -> list[dict[str, Any]]:
    """Fetch trending daily papers from Hugging Face.

    Args:
        limit: Max results
    """
    server = get_server()
    return server.get_hf_trending(limit)


@app.tool()
async def list_research_channels() -> list[str]:
    """List available research channels."""
    server = get_server()
    return server.list_research_channels()


if __name__ == "__main__":
    # Always use stdio transport for CLI integration
    app.run(transport="stdio")
