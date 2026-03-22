"""SurrealDB MCP Server - Model Context Protocol wrapper for universe node and learning storage."""

import logging
from typing import Any

from fastmcp import FastMCP

from cohezion.mcp.surreal_server import get_server


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("surreal-mcp")

# Initialize FastMCP server
app = FastMCP("cohezion-surreal")


@app.tool()
async def query_nodes(limit: int = 10, filter_type: str | None = None) -> list[dict[str, Any]]:
    """Query universe nodes from SurrealDB.

    Args:
        limit: Max results to return
        filter_type: Optional type filter (e.g., 'document', 'agent', 'event')
    """
    server = get_server()
    return await server.query_nodes(limit, filter_type)


@app.tool()
async def store_node(
    content: str, node_type: str = "document", physics: dict[str, float] | None = None
) -> dict[str, Any]:
    """Store a new universe node with physics state.

    Args:
        content: The text content of the node
        node_type: Categorization for the node
        physics: Optional 12D physics state parameters
    """
    server = get_server()
    return await server.store_node(content, node_type, physics)


@app.tool()
async def search_similar(query_embedding: list[float], limit: int = 5) -> list[dict[str, Any]]:
    """Vector similarity search for universe nodes.

    Args:
        query_embedding: Vector embedding to search with
        limit: Max results to return
    """
    server = get_server()
    return await server.search_similar(query_embedding, limit)


@app.tool()
async def store_learning(
    learning_id: str,
    title: str,
    content: str,
    pattern: str | None = None,
    score: float = 0.0,
) -> dict[str, Any]:
    """Store an extracted learning for trajectory prediction.

    Args:
        learning_id: Unique identifier for the learning
        title: Short descriptive title
        content: Detailed learning content
        pattern: Optional pattern name (e.g., 'HIHO', 'FLUME')
        score: Confidence or importance score (0.0 to 1.0)
    """
    server = get_server()
    return await server.store_learning(learning_id, title, content, pattern, score)


@app.tool()
async def query_learnings(limit: int = 20, min_score: float = 0.0) -> list[dict[str, Any]]:
    """Query stored learnings for state awareness.

    Args:
        limit: Max results to return
        min_score: Minimum confidence score to include
    """
    server = get_server()
    return await server.query_learnings(limit, min_score)


@app.tool()
async def sync_key_learnings(markdown_path: str | None = None) -> dict[str, Any]:
    """Synchronize the KEY_LEARNINGS.md file into SurrealDB.

    Args:
        markdown_path: Optional path to the markdown file
    """
    server = get_server()
    return await server.sync_key_learnings(markdown_path)


if __name__ == "__main__":
    # Always use stdio transport for CLI integration
    app.run(transport="stdio")
