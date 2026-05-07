"""MCP Server Manager - MCPServerManager class and singleton accessor."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import subprocess
import sys
from datetime import datetime
from typing import Any

import aiohttp

from .models import (
    MANAGER_PORT,
    PORT_RANGE,
    REDIS_URL,
    VAULT_LOG_PATH,
    MCPServerConfig,
    PortAllocator,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


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
        logger.info("Registered MCP server '%s' on port %d", name, port)
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
            env = os.environ.copy()
            env.update(config.env_vars)
            env["MCP_PORT"] = str(config.port)
            env["REDIS_URL"] = REDIS_URL

            module_path, _ = config.entry_point.rsplit(":", 1)

            # Per coding-standards L367: prefer venv python over sys.executable
            # (sys.executable can be system Python when invoked from a hook/cron).
            # (Ω12 P2 Patch 18 — TODO: extract to cohezion.utils.python_exec)
            def _python_exec_inline() -> str:
                from pathlib import Path as _Path

                _venv_py = _Path(__file__).resolve().parents[4] / ".venv" / "bin" / "python3"
                return str(_venv_py) if _venv_py.exists() else sys.executable

            cmd = [_python_exec_inline(), "-m", module_path]

            log_file = sanitize_path(f"{name}.log", base_dir=VAULT_LOG_PATH)

            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=open(log_file, "a", encoding="utf-8"),
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

            config.process = process
            config.pid = process.pid
            config.status = "starting"

            logger.info("Started server '%s' (PID: %d)", sanitize_log(name), process.pid)

            await asyncio.sleep(2)

            if process.poll() is None:
                config.status = "running"
                config.restart_count = 0
                return True
            else:
                config.status = "failed"
                logger.error("Server '%s' failed to start", sanitize_log(name))
                return False

        except Exception:
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

        except Exception:
            logger.exception("Error stopping server '%s'", sanitize_log(name))
            return False

    async def restart_server(self, name: str) -> bool:
        """Restart an MCP server."""
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
            headers = {}
            mcp_api_key = os.environ.get("MCP_API_KEY")
            if mcp_api_key:
                headers["Authorization"] = f"Bearer {mcp_api_key}"

            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    f"http://localhost:{config.port}/health",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response,
            ):
                healthy = response.status == 200
                if healthy:
                    config.status = "running"
                return healthy
        except Exception:
            return False

    async def health_check_loop(self) -> None:
        """Continuous health checking of all servers."""
        while True:
            try:
                for name, config in self.servers.items():
                    if config.status == "running":
                        healthy = await self.health_check(name)

                        if not healthy:
                            logger.warning("Server '%s' is unhealthy", name)
                            config.status = "unhealthy"

                            if config.auto_restart and config.restart_count < config.max_restarts:
                                logger.info("Auto-restarting server '%s'", name)
                                config.restart_count += 1
                                await self.restart_server(name)
                            else:
                                logger.error(
                                    "Server '%s' failed health check, not restarting (max restarts: %d)",
                                    name,
                                    config.max_restarts,
                                )

                await asyncio.sleep(30)

            except Exception as e:
                logger.exception("Error in health check loop: %s", e)
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

    async def start_all(self) -> None:
        """Start all registered servers."""
        logger.info("Starting %d MCP servers...", len(self.servers))

        for name in self.servers:
            await self.start_server(name)

        self.health_check_task = asyncio.create_task(self.health_check_loop())

    async def stop_all(self) -> None:
        """Stop all servers."""
        if self.health_check_task:
            self.health_check_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.health_check_task

        logger.info("Stopping %d MCP servers...", len(self.servers))

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
