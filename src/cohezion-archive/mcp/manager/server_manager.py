"""MCP Server Manager - Orchestrates all MCP servers.

Port: 8370
Features:
- Port allocation (8360-8399)
- Health monitoring
- Auto-restart
- Unified logging
- Metrics collection
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp
from aiohttp import web


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Configuration
PORT_RANGE = range(8360, 8400)
MANAGER_PORT = int(os.getenv("MANAGER_PORT", "8370"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
VAULT_LOG_PATH = Path(os.getenv("VAULT_LOG_PATH", "cloud-vault-mcp/vault/logs"))


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    port: int
    entry_point: str  # e.g., "cohezion.mcp.servers.bmad.server:app"
    auto_restart: bool = True
    health_check_interval: int = 30
    max_restarts: int = 5
    env_vars: dict[str, str] = field(default_factory=dict)
    status: str = "stopped"
    pid: int | None = None
    process: subprocess.Popen | None = None
    last_health_check: datetime | None = None
    restart_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "port": self.port,
            "entry_point": self.entry_point,
            "auto_restart": self.auto_restart,
            "health_check_interval": self.health_check_interval,
            "max_restarts": self.max_restarts,
            "env_vars": self.env_vars,
            "status": self.status,
            "pid": self.pid,
            "last_health_check": self.last_health_check.isoformat()
            if self.last_health_check
            else None,
            "restart_count": self.restart_count,
        }


class PortAllocator:
    """Manages port allocation for MCP servers."""

    def __init__(self, port_range: range = PORT_RANGE):
        self.port_range = port_range
        self.allocated: dict[int, str] = {}  # port -> server_name

    def allocate(self, server_name: str, preferred_port: int | None = None) -> int:
        """Allocate a port for a server.

        Args:
            server_name: Name of the server
            preferred_port: Preferred port (optional)

        Returns:
            Allocated port number
        """
        # Check if server already has a port
        for port, name in self.allocated.items():
            if name == server_name:
                return port

        # Try preferred port first
        if preferred_port and preferred_port in self.port_range:
            if preferred_port not in self.allocated:
                self.allocated[preferred_port] = server_name
                return preferred_port

        # Find first available port
        for port in self.port_range:
            if port not in self.allocated:
                self.allocated[port] = server_name
                return port

        raise RuntimeError(f"No available ports in range {self.port_range}")

    def release(self, server_name: str) -> bool:
        """Release a port allocated to a server."""
        for port, name in list(self.allocated.items()):
            if name == server_name:
                del self.allocated[port]
                return True
        return False

    def get_server_port(self, server_name: str) -> int | None:
        """Get the port allocated to a server."""
        for port, name in self.allocated.items():
            if name == server_name:
                return port
        return None


class MCPServerManager:
    """Manages all MCP servers."""

    def __init__(self):
        self.port_allocator = PortAllocator()
        self.servers: dict[str, MCPServerConfig] = {}
        self.health_check_task: asyncio.Task | None = None
        self.metrics: dict[str, Any] = {}

        # Ensure vault log directory exists
        VAULT_LOG_PATH.mkdir(parents=True, exist_ok=True)

    def register_server(
        self,
        name: str,
        entry_point: str,
        preferred_port: int | None = None,
        auto_restart: bool = True,
        env_vars: dict[str, str] | None = None,
    ) -> int:
        """Register a new MCP server.

        Args:
            name: Server name
            entry_point: Python module entry point
            preferred_port: Preferred port number
            auto_restart: Whether to auto-restart on failure
            env_vars: Environment variables

        Returns:
            Allocated port number
        """
        port = self.port_allocator.allocate(name, preferred_port)

        config = MCPServerConfig(
            name=name,
            port=port,
            entry_point=entry_point,
            auto_restart=auto_restart,
            env_vars=env_vars or {},
        )

        self.servers[name] = config
        logger.info(f"Registered MCP server '{name}' on port {port}")
        return port

    async def start_server(self, name: str) -> bool:
        """Start an MCP server.

        Args:
            name: Server name

        Returns:
            True if started successfully
        """
        from cohezion.mcp.servers.safe_input import sanitize_log, sanitize_path

        if name not in self.servers:
            logger.error("Server not found: %s", sanitize_log(name))
            return False

        config = self.servers[name]

        if config.status == "running":
            logger.warning("Server '%s' is already running", sanitize_log(name))
            return True

        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(config.env_vars)
            env["MCP_PORT"] = str(config.port)
            env["REDIS_URL"] = REDIS_URL

            # Parse entry point
            module_path, _app_name = config.entry_point.rsplit(":", 1)

            # Start the server
            cmd = [
                sys.executable,
                "-m",
                module_path,
            ]

            # Create log file (validate path stays in log directory)
            log_file = sanitize_path(f"{name}.log", base_dir=VAULT_LOG_PATH)

            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=open(log_file, "a"),
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

            config.process = process
            config.pid = process.pid
            config.status = "starting"

            logger.info("Started server '%s' (PID: %d)", sanitize_log(name), process.pid)

            # Wait a moment for server to start
            await asyncio.sleep(2)

            # Check if process is still running
            if process.poll() is None:
                config.status = "running"
                config.restart_count = 0
                return True
            else:
                config.status = "failed"
                logger.error("Server '%s' failed to start", sanitize_log(name))
                return False

        except Exception as _e:
            logger.exception("Error starting server '%s'", sanitize_log(name))
            config.status = "failed"
            return False

    async def stop_server(self, name: str) -> bool:
        """Stop an MCP server.

        Args:
            name: Server name

        Returns:
            True if stopped successfully
        """
        if name not in self.servers:
            return False

        config = self.servers[name]

        if config.status == "stopped":
            return True

        try:
            if config.process and config.process.poll() is None:
                config.process.terminate()
                try:
                    config.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    config.process.kill()
                    config.process.wait()

            config.status = "stopped"
            config.pid = None
            config.process = None

            from cohezion.mcp.servers.safe_input import sanitize_log

            logger.info("Stopped server '%s'", sanitize_log(name))
            return True

        except Exception as _e:
            logger.exception("Error stopping server '%s'", sanitize_log(name))
            return False

    async def restart_server(self, name: str) -> bool:
        """Restart an MCP server.

        Args:
            name: Server name

        Returns:
            True if restarted successfully
        """
        await self.stop_server(name)
        return await self.start_server(name)

    async def health_check(self, name: str) -> bool:
        """Check health of an MCP server.

        Args:
            name: Server name

        Returns:
            True if healthy
        """
        if name not in self.servers:
            return False

        config = self.servers[name]
        config.last_health_check = datetime.utcnow()

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    f"http://localhost:{config.port}/health",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response,
            ):
                healthy = response.status == 200
                if healthy:
                    config.status = "running"
                return healthy
        except Exception:
            # Server not responding
            return False

    async def health_check_loop(self):
        """Continuous health checking of all servers."""
        while True:
            try:
                for name, config in self.servers.items():
                    if config.status == "running":
                        healthy = await self.health_check(name)

                        if not healthy:
                            logger.warning(f"Server '{name}' is unhealthy")
                            config.status = "unhealthy"

                            if config.auto_restart and config.restart_count < config.max_restarts:
                                logger.info(f"Auto-restarting server '{name}'")
                                config.restart_count += 1
                                await self.restart_server(name)
                            else:
                                logger.error(
                                    f"Server '{name}' failed health check, not restarting (max restarts: {config.max_restarts})"
                                )

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.exception(f"Error in health check loop: {e}")
                await asyncio.sleep(30)

    def get_status(self) -> dict[str, Any]:
        """Get status of all servers."""
        return {
            "manager": {
                "port": MANAGER_PORT,
                "servers_count": len(self.servers),
                "port_range": f"{PORT_RANGE.start}-{PORT_RANGE.stop - 1}",
            },
            "servers": {name: config.to_dict() for name, config in self.servers.items()},
        }

    async def start_all(self):
        """Start all registered servers."""
        logger.info(f"Starting {len(self.servers)} MCP servers...")

        for name in self.servers:
            await self.start_server(name)

        # Start health checking
        self.health_check_task = asyncio.create_task(self.health_check_loop())

    async def stop_all(self):
        """Stop all servers."""
        if self.health_check_task:
            self.health_check_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.health_check_task

        logger.info(f"Stopping {len(self.servers)} MCP servers...")

        for name in self.servers:
            await self.stop_server(name)


# Global manager instance
_manager: MCPServerManager | None = None


def get_manager() -> MCPServerManager:
    """Get or create global manager instance."""
    global _manager
    if _manager is None:
        _manager = MCPServerManager()
    return _manager


# HTTP API routes
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
    return web.json_response(
        {
            "name": name,
            "success": success,
            "status": status,
        }
    )


@routes.post("/servers/{name}/stop")
async def stop_server_handler(request: web.Request) -> web.Response:
    """Stop a specific server."""
    name = request.match_info["name"]
    manager = get_manager()

    success = await manager.stop_server(name)
    server_info = manager.servers.get(name)
    status = server_info.status if server_info else "unknown"
    return web.json_response(
        {
            "name": name,
            "success": success,
            "status": status,
        }
    )


@routes.post("/servers/{name}/restart")
async def restart_server_handler(request: web.Request) -> web.Response:
    """Restart a specific server."""
    name = request.match_info["name"]
    manager = get_manager()

    success = await manager.restart_server(name)
    server_info = manager.servers.get(name)
    status = server_info.status if server_info else "unknown"
    return web.json_response(
        {
            "name": name,
            "success": success,
            "status": status,
        }
    )


@routes.get("/servers/{name}/health")
async def server_health_handler(request: web.Request) -> web.Response:
    """Check health of a specific server."""
    name = request.match_info["name"]
    manager = get_manager()

    if name not in manager.servers:
        return web.json_response({"error": "Server not found"}, status=404)

    healthy = await manager.health_check(name)
    return web.json_response(
        {
            "name": name,
            "healthy": healthy,
            "status": manager.servers[name].status,
        }
    )


def init_default_servers():
    """Register default MCP servers."""
    manager = get_manager()

    # Register BMAD server (Port 8361)
    manager.register_server(
        name="bmad",
        entry_point="cohezion.mcp.servers.bmad.server:app",
        preferred_port=8361,
        auto_restart=True,
        env_vars={
            "BMAD_DATA_PATH": "_bmad",
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Skills.sh server (Port 8362)
    manager.register_server(
        name="skills",
        entry_point="cohezion.mcp.servers.skills.server:app",
        preferred_port=8362,
        auto_restart=True,
        env_vars={
            "SKILLS_CACHE_SIZE": "1000",
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Doc Retriever server (Port 8364)
    manager.register_server(
        name="doc-retriever",
        entry_point="cohezion.mcp.servers.doc.server:app",
        preferred_port=8364,
        auto_restart=True,
        env_vars={
            "SURREAL_URL": "ws://localhost:8000/rpc",
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Hugging Face MCP Server (Port 8365) - Official HF managed service
    manager.register_server(
        name="huggingface",
        entry_point="cohezion.mcp.servers.huggingface.server:app",
        preferred_port=8365,
        auto_restart=True,
        env_vars={
            "HF_MCP_URL": "https://huggingface.co/mcp",
            "HF_TOKEN": os.getenv("HF_TOKEN", ""),
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Memory MCP Server (Port 8366) - Knowledge graph
    manager.register_server(
        name="memory",
        entry_point="cohezion.mcp.servers.memory.server:app",
        preferred_port=8366,
        auto_restart=True,
        env_vars={
            "SURREAL_URL": "ws://localhost:8000/rpc",
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Sequential Thinking MCP Server (Port 8367)
    manager.register_server(
        name="sequential-thinking",
        entry_point="cohezion.mcp.servers.sequential.server:app",
        preferred_port=8367,
        auto_restart=True,
        env_vars={
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Git Context MCP Server (Port 8368)
    manager.register_server(
        name="git-context",
        entry_point="cohezion.mcp.servers.git.server:app",
        preferred_port=8368,
        auto_restart=True,
        env_vars={
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Security MCP Server (Port 8369)
    manager.register_server(
        name="security",
        entry_point="cohezion.mcp.servers.security.server:app",
        preferred_port=8369,
        auto_restart=True,
        env_vars={
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Knowledge MCP Server (Port 8371)
    manager.register_server(
        name="knowledge",
        entry_point="cohezion.mcp.knowledge_server:app",
        preferred_port=8371,
        auto_restart=True,
        env_vars={
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Swarm MCP Server (Port 8372)
    manager.register_server(
        name="swarm",
        entry_point="cohezion.mcp.swarm_server:app",
        preferred_port=8372,
        auto_restart=True,
        env_vars={
            "LOG_LEVEL": "INFO",
        },
    )

    # Register Research MCP Server (Port 8373)
    manager.register_server(
        name="research",
        entry_point="cohezion.mcp.research_server:app",
        preferred_port=8373,
        auto_restart=True,
        env_vars={
            "LOG_LEVEL": "INFO",
        },
    )

    logger.info(f"Registered {len(manager.servers)} default MCP servers")


async def main():
    """Run the MCP Server Manager."""
    # Initialize default servers
    init_default_servers()

    # Create web app
    app = web.Application()
    app.add_routes(routes)

    # Get manager and start servers
    manager = get_manager()

    # Start servers on startup
    async def on_startup(app):
        await manager.start_all()

    # Stop servers on shutdown
    async def on_shutdown(app):
        await manager.stop_all()

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Run the server
    logger.info(f"Starting MCP Server Manager on port {MANAGER_PORT}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", MANAGER_PORT)
    await site.start()

    # Keep running
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("MCP Server Manager stopped")
