"""Skills MCP Server - Model Context Protocol wrapper for direct skill invocation."""

from typing import Any

from fastmcp import FastMCP

from cohezion.mcp.skills_server import get_server


# Initialize FastMCP server
app = FastMCP("cohezion-skills")


@app.tool()
async def invoke_skill(skill_name: str) -> dict[str, Any]:
    """Load and return a skill's content and metadata.

    Args:
        skill_name: Name of the skill to load (e.g., 'CODE_REVIEW', 'GIT_HYGIENE')
    """
    server = get_server()
    return server.invoke_skill(skill_name)


@app.tool()
async def register_skill(
    name: str,
    description: str,
    keywords: list[str],
    path: str,
) -> dict[str, Any]:
    """Register a new skill in the cohezion registry.

    Args:
        name: Unique name for the skill
        description: Brief description of capabilities
        keywords: Search keywords for discovery
        path: Path to the skill file relative to src/cohezion/skills/
    """
    server = get_server()
    return server.register_skill(name, description, keywords, path)


@app.tool()
async def search_skills(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Fuzzy search for skills in the registry.

    Args:
        query: Search term
        limit: Max results to return
    """
    server = get_server()
    return server.search_skills(query, limit)


@app.tool()
async def list_all_skills() -> list[dict[str, str]]:
    """List all registered skills with their descriptions."""
    server = get_server()
    return server.list_all()


if __name__ == "__main__":
    # Always use stdio transport for CLI integration
    app.run(transport="stdio")
