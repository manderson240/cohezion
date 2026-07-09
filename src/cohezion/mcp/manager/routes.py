# binds 0.0.0.0 in dev/internal services
"""MCP Server Manager - HTTP routes and application entrypoint."""

from __future__ import annotations

import asyncio
import logging
import sys

from aiohttp import web

from .defaults import init_default_servers
from .models import MANAGER_PORT
from .server_manager import get_manager


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

routes = web.RouteTableDef()


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    """Manager status endpoint."""
    manager = get_manager()
    return web.json_response(manager.get_status())


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response({"status": "healthy", "port": MANAGER_PORT})


@routes.post("/servers/{name}/start")
async def start_server_handler(request: web.Request) -> web.Response:
    """Start a specific server."""
    name = request.match_info["name"]
    manager = get_manager()

    success = await manager.start_server(name)
    server_info = manager.servers.get(name)
    status = server_info.status if server_info else "unknown"
    return web.json_response({"name": name, "success": success, "status": status})


@routes.post("/servers/{name}/stop")
async def stop_server_handler(request: web.Request) -> web.Response:
    """Stop a specific server."""
    name = request.match_info["name"]
    manager = get_manager()

    success = await manager.stop_server(name)
    server_info = manager.servers.get(name)
    status = server_info.status if server_info else "unknown"
    return web.json_response({"name": name, "success": success, "status": status})


@routes.post("/servers/{name}/restart")
async def restart_server_handler(request: web.Request) -> web.Response:
    """Restart a specific server."""
    name = request.match_info["name"]
    manager = get_manager()

    success = await manager.restart_server(name)
    server_info = manager.servers.get(name)
    status = server_info.status if server_info else "unknown"
    return web.json_response({"name": name, "success": success, "status": status})


@routes.get("/servers/{name}/health")
async def server_health_handler(request: web.Request) -> web.Response:
    """Check health of a specific server."""
    name = request.match_info["name"]
    manager = get_manager()

    if name not in manager.servers:
        return web.json_response({"error": "Server not found"}, status=404)

    healthy = await manager.health_check(name)
    return web.json_response(
        {"name": name, "healthy": healthy, "status": manager.servers[name].status}
    )


async def main() -> None:
    """Run the MCP Server Manager."""
    init_default_servers()

    from cohezion.mcp.shared.auth import api_key_middleware

    app = web.Application(middlewares=[api_key_middleware])
    app.add_routes(routes)

    manager = get_manager()

    async def on_startup(app: web.Application) -> None:
        await manager.start_all()

    async def on_shutdown(app: web.Application) -> None:
        await manager.stop_all()

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    logger.info("Starting MCP Server Manager on port %d", MANAGER_PORT)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", MANAGER_PORT)
    await site.start()

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("MCP Server Manager stopped")
