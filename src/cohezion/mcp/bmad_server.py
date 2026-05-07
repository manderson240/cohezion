"""BMAD MCP Server - 108 BMAD commands via MCP protocol.

Usage:
    uv run python -m cohezion.mcp.bmad_server

Ports:
    - 8361: BMAD MCP Server (HTTP/SSE)

Environment:
    - MCP_API_KEY: Authentication key (required)
    - REDIS_URL: Redis connection (default: redis://localhost:6379)
    - BMAD_DATA_PATH: Path to _bmad directory (default: ./_bmad)
    - MCP_PORT: Server port (default: 8361)
"""

from __future__ import annotations

import json
import os

# Import tool modules to register @app.tool() decorators
from cohezion.mcp.bmad_app import app, get_bmad_data_path, get_engine, get_redis_url, logger


# ============================================================================
# AGENT PROMPTS (28 agents as MCP prompts)
# ============================================================================


@app.prompt(name="bmad-pm")
def bmad_pm_prompt() -> str:
    """BMAD Product Manager agent prompt."""
    engine = get_engine()
    return engine.load_agent_prompt("bmm-pm")


@app.prompt(name="bmad-dev")
def bmad_dev_prompt() -> str:
    """BMAD Developer agent prompt."""
    engine = get_engine()
    return engine.load_agent_prompt("bmm-dev")


@app.prompt(name="bmad-architect")
def bmad_architect_prompt() -> str:
    """BMAD Architect agent prompt."""
    engine = get_engine()
    return engine.load_agent_prompt("bmm-architect")


@app.prompt(name="bmad-qa")
def bmad_qa_prompt() -> str:
    """BMAD QA agent prompt."""
    engine = get_engine()
    return engine.load_agent_prompt("bmm-qa")


@app.prompt(name="bmad-game-designer")
def bmad_game_designer_prompt() -> str:
    """BMAD Game Designer agent prompt."""
    engine = get_engine()
    return engine.load_agent_prompt("gds-game-designer")


@app.prompt(name="bmad-game-dev")
def bmad_game_dev_prompt() -> str:
    """BMAD Game Developer agent prompt."""
    engine = get_engine()
    return engine.load_agent_prompt("gds-game-dev")


# ============================================================================
# RESOURCES (Workflows, Agents, Documentation)
# ============================================================================


@app.resource("bmad://workflows/{module}/{workflow_id}")
async def get_workflow_resource(module: str, workflow_id: str) -> str:
    """Get BMAD workflow content."""
    engine = get_engine()
    result = engine.load_workflow(module, workflow_id)
    if "error" in result:
        return f"# Error\n{result['error']}"
    return result.get("content", "")


@app.resource("bmad://agents/{agent_name}")
async def get_agent_resource(agent_name: str) -> str:
    """Get BMAD agent persona."""
    engine = get_engine()
    content = engine.load_agent(agent_name)
    return json.dumps(content, indent=2)


@app.resource("bmad://modules")
async def list_modules_resource() -> str:
    """List all BMAD modules."""
    engine = get_engine()
    modules = engine.list_modules()
    return json.dumps(modules, indent=2)


# ============================================================================
# MAIN ENTRY
# ============================================================================


def main():
    """Run the BMAD MCP server."""
    port = int(os.getenv("MCP_PORT", "8361"))
    transport = os.getenv("MCP_TRANSPORT", "http")

    if transport == "stdio":
        app.run(transport="stdio")
    else:
        logger.info(f"Starting BMAD MCP Server v6.0.4 on port {port}")
        logger.info(f"BMAD data path: {get_bmad_data_path()}")
        logger.info(f"Redis URL: {get_redis_url()}")
        logger.info(f"Transport: {transport}")
        app.run(host="0.0.0.0", port=port, transport="http")


if __name__ == "__main__":
    main()
