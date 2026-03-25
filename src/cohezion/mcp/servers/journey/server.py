"""Journey MCP Server.

Provides: Tools for starting, listing, and tracking journeys.
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
MCP_PORT = int(os.getenv("MCP_PORT", "8363"))

# HTTP API routes
routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response(
        {
            "status": "healthy",
            "server": "journey",
            "port": MCP_PORT,
        }
    )


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    """Server info."""
    return web.json_response(
        {
            "name": "Cohezion Journey MCP Server",
            "version": "1.0.0",
            "port": MCP_PORT,
        }
    )


# =============================================================================
# TOOLS API
# =============================================================================


@routes.post("/tools/journey_start")
async def tool_journey_start(request: web.Request) -> web.Response:
    """Start a new universe journey."""
    try:
        data = await request.json()
        intent = data.get("intent")
        agent = data.get("agent", "AutoAgent")
        model = data.get("model", "deepseek-r1:7b")
        data.get("agents", 1)

        if not intent:
            return web.json_response({"error": "Missing 'intent' parameter"}, status=400)

        # Integration with Universe Engine
        try:
            from cohezion.universe.engine import UniverseSimulationEngine

            engine = UniverseSimulationEngine()
            journey = await engine.start_journey(
                agent_name=agent,
                intent=intent,
                # Additional params can be passed here
            )
            journey_id = journey.id
        except Exception as e:
            logger.warning(f"Could not use real engine, falling back to mock: {e}")
            journey_id = f"journey_{intent[:20].replace(' ', '_')}"

        return web.json_response(
            {
                "tool": "journey_start",
                "journey_id": journey_id,
                "intent": intent,
                "agent": agent,
                "model": model,
                "status": "active",
                "created_at": "now",
            }
        )
    except Exception as e:
        logger.exception("Error starting journey")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/journey_list")
async def tool_journey_list(request: web.Request) -> web.Response:
    """List available journeys."""
    try:
        # Mock data - would query SurrealDB
        journeys = [
            {
                "id": "journey_001",
                "intent": "Design API",
                "status": "completed",
                "phi": 0.85,
            },
            {
                "id": "journey_002",
                "intent": "Refactor auth",
                "status": "active",
                "phi": 0.72,
            },
        ]

        return web.json_response(
            {
                "tool": "journey_list",
                "journeys": journeys,
            }
        )
    except Exception as e:
        logger.exception("Error listing journeys")
        return web.json_response({"error": str(e)}, status=500)


def create_app() -> web.Application:
    """Create the web application."""
    app = web.Application(middlewares=[api_key_middleware])
    app.add_routes(routes)
    return app


app = create_app()


async def main():
    """Run the Journey MCP Server."""
    await run_server(create_app, MCP_PORT, "Journey MCP Server")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Journey MCP Server stopped")
