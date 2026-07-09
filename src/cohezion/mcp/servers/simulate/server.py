# long lines: SQL/URLs/docstrings — wrapping reduces readability
"""Simulate MCP Server.

Provides: Tools for running sandboxed simulations.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from uuid import uuid4

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
MCP_PORT = int(os.getenv("MCP_PORT", "8364"))

# HTTP API routes
routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response(
        {
            "status": "healthy",
            "server": "simulate",
            "port": MCP_PORT,
        }
    )


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    """Server info."""
    return web.json_response(
        {
            "name": "Cohezion Simulate MCP Server",
            "version": "1.0.0",
            "port": MCP_PORT,
        }
    )


# =============================================================================
# TOOLS API
# =============================================================================


@routes.post("/tools/run_simulation")
async def tool_run_simulation(request: web.Request) -> web.Response:
    """Run a sandboxed simulation."""
    try:
        data = await request.json()
        tier_name = data.get("tier", "light")
        backend_name = data.get("backend")
        script_content = data.get("script")
        example_name = data.get("example")

        if not script_content and not example_name:
            return web.json_response(
                {"error": "Provide 'script' content or 'example' name"}, status=400
            )

        # Integration with Universe Simulation
        try:
            from cohezion.universe.example_simulations import EXAMPLES
            from cohezion.universe.sandbox_backends import (
                DockerBackend,
                SubprocessBackend,
                SystemdRunBackend,
                select_backend,
            )
            from cohezion.universe.sandbox_profiles import SandboxTier, get_profile
            from cohezion.universe.sandbox_results import persist_result

            # Resolve script content
            if example_name:
                if example_name not in EXAMPLES:
                    return web.json_response(
                        {"error": f"Example '{example_name}' not found"}, status=404
                    )
                script = EXAMPLES[example_name]
            else:
                script = script_content

            # Resolve tier
            tier_map = {
                "light": SandboxTier.LIGHT,
                "medium": SandboxTier.MEDIUM,
                "heavy": SandboxTier.HEAVY,
            }
            tier = tier_map.get(tier_name, SandboxTier.LIGHT)
            profile = get_profile(tier)

            # Resolve backend
            backend_map = {
                "docker": DockerBackend,
                "systemd": SystemdRunBackend,
                "subprocess": SubprocessBackend,
            }
            backend = (
                backend_map[backend_name]() if backend_name in backend_map else select_backend()
            )

            run_id = f"sim_{uuid4().hex[:8]}"
            logger.info(
                f"Executing simulation {run_id} (tier={tier_name}, backend={type(backend).__name__})"
            )

            result = await backend.execute(script, profile)

            # Persist results
            run_dir = persist_result(
                result,
                run_id,
                tier=tier_name,
                backend=type(backend).__name__,
            )

            return web.json_response(
                {
                    "tool": "run_simulation",
                    "run_id": run_id,
                    "success": result.success,
                    "exit_code": result.exit_code,
                    "duration": result.duration,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "output_files": list(result.output_files.keys()),
                    "run_dir": str(run_dir),
                }
            )

        except Exception as e:
            logger.exception("Error in simulation logic")
            return web.json_response({"error": f"Simulation execution failed: {e}"}, status=500)

    except Exception as e:
        logger.exception("Error processing request")
        return web.json_response({"error": str(e)}, status=500)


def create_app() -> web.Application:
    """Create the web application."""
    app = web.Application(middlewares=[api_key_middleware])
    app.add_routes(routes)
    return app


app = create_app()


async def main():
    """Run the Simulate MCP Server."""
    await run_server(create_app, MCP_PORT, "Simulate MCP Server")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Simulate MCP Server stopped")
