"""Rewards MCP Server.

Provides: Tools for viewing rewards, achievements, and progress.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from aiohttp import web

from cohezion.mcp.shared.auth import api_key_middleware
from cohezion.mcp.shared.server import run_server


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Configuration
MCP_PORT = int(os.getenv("MCP_PORT", "8365"))

# HTTP API routes
routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response(
        {
            "status": "healthy",
            "server": "rewards",
            "port": MCP_PORT,
        }
    )


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    """Server info."""
    return web.json_response(
        {
            "name": "Cohezion Rewards MCP Server",
            "version": "1.0.0",
            "port": MCP_PORT,
        }
    )


# =============================================================================
# TOOLS API
# =============================================================================


@routes.post("/tools/get_reward_status")
async def tool_get_reward_status(request: web.Request) -> web.Response:
    """Get reward status for an agent."""
    try:
        data = await request.json()
        agent_id = data.get("agent", "me")

        # Mock status - would query reward system
        status = {
            "agent_id": agent_id,
            "total_xp": 12450,
            "tier": "Master",
            "capabilities": ["access_deepseek_70b", "meta_programming", "generate_agents"],
            "parallel_agents": 20,
            "autonomy_tier": 3,
            "achievements": [
                {"name": "Quality Craftsman", "rarity": "rare"},
                {"name": "Collaborator", "rarity": "common"},
                {"name": "Dedicated", "rarity": "epic"},
            ],
            "streak": {"current": 5, "longest": 12},
            "next_unlock": {"name": "Architect", "threshold": 25000, "xp_needed": 12550},
        }

        return web.json_response(
            {
                "tool": "get_reward_status",
                "status": status,
            }
        )
    except Exception as e:
        logger.exception("Error getting reward status")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/get_leaderboard")
async def tool_get_leaderboard(request: web.Request) -> web.Response:
    """Get XP leaderboard."""
    try:
        data = await request.json()
        top = data.get("top", 10)

        # Mock leaderboard
        leaderboard = [
            {"rank": 1, "agent": "EvolutionAgent", "xp": 45600, "tier": "Architect"},
            {"rank": 2, "agent": "NexusResearchAgent", "xp": 38900, "tier": "Master"},
            {"rank": 3, "agent": "ArchitectAgent", "xp": 32100, "tier": "Master"},
        ]

        return web.json_response(
            {
                "tool": "get_leaderboard",
                "leaderboard": leaderboard[:top],
            }
        )
    except Exception as e:
        logger.exception("Error getting leaderboard")
        return web.json_response({"error": str(e)}, status=500)


def create_app() -> web.Application:
    """Create the web application."""
    app = web.Application(middlewares=[api_key_middleware])
    app.add_routes(routes)
    return app


app = create_app()


async def main():
    """Run the Rewards MCP Server."""
    await run_server(create_app, MCP_PORT, "Rewards MCP Server")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Rewards MCP Server stopped")
