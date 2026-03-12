"""BMAD MCP Server - Entrypoint.

Port: 8361
Provides: 90 BMAD tools, agent prompts, workflow resources.
Routes are split by domain into routes_*.py modules.
"""

from __future__ import annotations

import asyncio

from aiohttp import web

# Import route modules to register their @routes decorators
from . import (
    routes_bmb,  # noqa: F401
    routes_bmm,  # noqa: F401
    routes_bmm_ops,  # noqa: F401
    routes_cis,  # noqa: F401
    routes_gds,  # noqa: F401
    routes_general,  # noqa: F401
    routes_tea,  # noqa: F401
)
from ._shared import MCP_PORT, get_engine, logger, routes


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response({"status": "healthy", "server": "bmad", "port": MCP_PORT})


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    """Server info endpoint."""
    engine = get_engine()
    return web.json_response(
        {
            "server": "BMAD MCP Server",
            "version": "6.0.4",
            "port": MCP_PORT,
            "modules": [m["name"] for m in engine.list_modules()],
            "workflows_count": len(engine._workflows),
            "agents_count": len(engine._agents),
            "tools_count": 90,
        }
    )


@routes.get("/resources/workflows/{module}/{path:.*}")
async def get_workflow_resource(request: web.Request) -> web.Response:
    """Get workflow content."""
    module = request.match_info["module"]
    path = request.match_info["path"]
    engine = get_engine()
    workflow = engine.get_workflow(f"{module}/{path}")
    if "error" in workflow:
        return web.json_response(workflow, status=404)
    return web.json_response(workflow)


@routes.get("/resources/agents/{agent_id}")
async def get_agent_resource(request: web.Request) -> web.Response:
    """Get agent content."""
    agent_id = request.match_info["agent_id"]
    engine = get_engine()
    agent = engine.get_agent(agent_id)
    if "error" in agent:
        return web.json_response(agent, status=404)
    return web.json_response(agent)


@routes.get("/resources/modules")
async def list_modules_resource(request: web.Request) -> web.Response:
    """List all modules."""
    engine = get_engine()
    return web.json_response({"modules": engine.list_modules()})


def create_app() -> web.Application:
    """Create the web application."""
    from cohezion.mcp.shared.auth import api_key_middleware

    app = web.Application(middlewares=[api_key_middleware])
    app.add_routes(routes)
    return app


app = create_app()


async def main():
    """Run the BMAD MCP Server."""
    get_engine()
    logger.info(f"Starting BMAD MCP Server on port {MCP_PORT}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", MCP_PORT)
    await site.start()
    logger.info(f"BMAD MCP Server running on http://localhost:{MCP_PORT}")
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("BMAD MCP Server stopped")
