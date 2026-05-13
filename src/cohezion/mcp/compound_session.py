"""Compound MCP Integration - BMAD infrastructure as compound sessions.

Features:
- MCP servers run as compound sessions
- Automatic checkpointing of server state
- Warm-start / clean-shutdown for long-running MCP servers
- Vault persistence for MCP infrastructure state
- Integration with existing compound session manager
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from cohezion.compound.session_manager import (
    CompoundSessionManager,
    VaultCheckpointManager,
)


logger = logging.getLogger(__name__)


@dataclass
class MCPServerState:
    """State snapshot of an MCP server for checkpointing."""

    server_name: str
    port: int
    pid: int | None = None
    status: str = "stopped"
    start_time: float = field(default_factory=time.time)
    restart_count: int = 0
    total_requests: int = 0
    total_errors: int = 0
    last_health_check: float | None = None
    cache_stats: dict[str, Any] = field(default_factory=dict)
    session_count: int = 0


@dataclass
class MCPInfrastructureState:
    """Compound state for entire MCP infrastructure."""

    infrastructure_id: str
    servers: dict[str, MCPServerState] = field(default_factory=dict)
    redis_connected: bool = False
    total_uptime_seconds: float = 0.0
    created_at: float = field(default_factory=time.time)


class CompoundMCPSessionManager:
    """Manage MCP servers as compound sessions with checkpointing.

    Integrates BMAD MCP infrastructure with Cohezion's compound system:
    - Long-running MCP servers with automatic checkpointing
    - Warm-start capability for instant server recovery
    - Vault persistence for complete infrastructure state
    - Graceful shutdown preserving all session data
    """

    def __init__(self, infrastructure_id: str | None = None):
        """Initialize compound MCP session manager.

        Args:
            infrastructure_id: Unique ID for this infrastructure (generated if not provided)
        """
        self.infrastructure_id = infrastructure_id or f"mcp_{uuid.uuid4().hex[:8]}"
        self.state = MCPInfrastructureState(infrastructure_id=self.infrastructure_id)
        self._compound_session = CompoundSessionManager()
        self._vault_manager = VaultCheckpointManager()
        self._running = False

    async def start_infrastructure(
        self, servers: list[dict[str, Any]] | None = None, max_cache_entries: int = 256
    ) -> dict[str, Any]:
        """Start MCP infrastructure as compound session.

        Performs warm-start sequence:
        1. Start compound session (load cached data)
        2. Restore MCP server states from checkpoint
        3. Start all registered MCP servers
        4. Register with MCP Manager

        Args:
            servers: List of server configs to start
            max_cache_entries: Maximum cache entries to warm-load

        Returns:
            Session summary with infrastructure state
        """
        logger.info(f"Starting MCP infrastructure {self.infrastructure_id}")

        # Step 1: Start compound session (warm-start)
        compound_summary = self._compound_session.start_session(max_cache_entries)
        logger.info(f"Compound session started: {compound_summary.session_id}")

        # Step 2: Try to restore MCP infrastructure state
        restored_state = await self._restore_infrastructure_state()
        if restored_state:
            self.state = restored_state
            logger.info("Restored infrastructure state from checkpoint")

        # Step 3: Update state with current compound session info
        self.state.infrastructure_id = self.infrastructure_id

        # Step 4: Start MCP servers
        if servers:
            for server_config in servers:
                await self._start_server_compound(server_config)

        self._running = True

        # Step 5: Initial checkpoint
        await self._checkpoint_infrastructure()

        return {
            "infrastructure_id": self.infrastructure_id,
            "compound_session": compound_summary.session_id,
            "servers_running": len(self.state.servers),
            "restored_from_checkpoint": restored_state is not None,
            "state": self._state_to_dict(),
        }

    async def stop_infrastructure(self, graceful: bool = True) -> dict[str, Any]:
        """Stop MCP infrastructure with clean shutdown.

        Performs clean-shutdown sequence:
        1. Stop all MCP servers gracefully
        2. Save MCP infrastructure state to checkpoint
        3. End compound session (persist cache/metrics)
        4. Clean up resources

        Args:
            graceful: Whether to wait for in-flight requests

        Returns:
            Shutdown summary with final state
        """
        logger.info(f"Stopping MCP infrastructure {self.infrastructure_id}")

        # Step 1: Stop all servers
        shutdown_results = []
        for server_name in list(self.state.servers.keys()):
            result = await self._stop_server_compound(server_name, graceful)
            shutdown_results.append({"server": server_name, "result": result})

        # Step 2: Final checkpoint
        await self._checkpoint_infrastructure()

        # Step 3: End compound session
        compound_summary = self._compound_session.end_session()

        self._running = False

        return {
            "infrastructure_id": self.infrastructure_id,
            "compound_session": compound_summary.session_id,
            "servers_stopped": len(shutdown_results),
            "shutdown_results": shutdown_results,
            "total_uptime": self.state.total_uptime_seconds,
            "final_state": self._state_to_dict(),
        }

    async def register_server(
        self, server_name: str, port: int, entry_point: str, auto_restart: bool = True
    ) -> MCPServerState:
        """Register a new MCP server with compound session management.

        Args:
            server_name: Unique server name
            port: Server port
            entry_point: Python module entry point
            auto_restart: Whether to auto-restart on failure

        Returns:
            Server state object
        """
        server_state = MCPServerState(server_name=server_name, port=port, status="registered", start_time=time.time())

        self.state.servers[server_name] = server_state

        # Checkpoint after registration
        await self._checkpoint_infrastructure()

        logger.info(f"Registered server {server_name} on port {port}")
        return server_state

    async def update_server_state(self, server_name: str, **updates) -> MCPServerState | None:
        """Update server state and checkpoint.

        Args:
            server_name: Server to update
            **updates: State fields to update

        Returns:
            Updated server state or None if not found
        """
        if server_name not in self.state.servers:
            return None

        server_state = self.state.servers[server_name]

        # Update fields
        for key, value in updates.items():
            if hasattr(server_state, key):
                setattr(server_state, key, value)

        # Checkpoint periodically (every 5 updates)
        if server_state.total_requests % 5 == 0:
            await self._checkpoint_infrastructure()

        return server_state

    async def get_server_health(self, server_name: str) -> dict[str, Any]:
        """Get compound health status for a server.

        Args:
            server_name: Server to check

        Returns:
            Health status with compound session info
        """
        if server_name not in self.state.servers:
            return {"error": f"Server {server_name} not found"}

        server_state = self.state.servers[server_name]

        # Calculate uptime
        uptime = time.time() - server_state.start_time

        # Calculate error rate
        total = server_state.total_requests
        errors = server_state.total_errors
        error_rate = (errors / total * 100) if total > 0 else 0

        return {
            "server": server_name,
            "status": server_state.status,
            "port": server_state.port,
            "uptime_seconds": uptime,
            "total_requests": total,
            "total_errors": errors,
            "error_rate_percent": error_rate,
            "restart_count": server_state.restart_count,
            "last_health_check": server_state.last_health_check,
            "cache_stats": server_state.cache_stats,
            "infrastructure_id": self.infrastructure_id,
        }

    async def list_servers(self) -> list[dict[str, Any]]:
        """List all registered servers with compound state."""
        return [
            {
                "name": name,
                "port": state.port,
                "status": state.status,
                "uptime": time.time() - state.start_time,
                "requests": state.total_requests,
            }
            for name, state in self.state.servers.items()
        ]

    async def _start_server_compound(self, server_config: dict[str, Any]) -> bool:
        """Start a server with compound session tracking."""
        try:
            from cohezion.mcp.manager.server_manager import get_manager

            manager = get_manager()

            # Register with MCP manager
            port = manager.register_server(
                name=server_config["name"],
                entry_point=server_config["entry_point"],
                preferred_port=server_config.get("port"),
                auto_restart=server_config.get("auto_restart", True),
            )

            # Start the server
            success = await manager.start_server(server_config["name"])

            if success:
                # Update compound state
                await self.update_server_state(
                    server_config["name"], status="running", port=port, start_time=time.time()
                )

                logger.info(f"Started server {server_config['name']} on port {port}")
                return True
            else:
                logger.error(f"Failed to start server {server_config['name']}")
                return False

        except Exception as e:
            logger.exception(f"Error starting server: {e}")
            return False

    async def _stop_server_compound(self, server_name: str, graceful: bool = True) -> bool:
        """Stop a server with compound session tracking."""
        try:
            from cohezion.mcp.manager.server_manager import get_manager

            manager = get_manager()
            success = await manager.stop_server(server_name)

            if success:
                await self.update_server_state(server_name, status="stopped")

                logger.info(f"Stopped server {server_name}")
                return True
            else:
                return False

        except Exception as e:
            logger.exception(f"Error stopping server: {e}")
            return False

    async def _checkpoint_infrastructure(self) -> bool:
        """Save infrastructure state to vault checkpoint."""
        try:
            # Update total uptime
            self.state.total_uptime_seconds = time.time() - self.state.created_at

            # Convert to dict
            state_dict = self._state_to_dict()

            # Save to vault via MCP
            from cohezion.core.mcp_client import get_mcp_client

            mcp = get_mcp_client()
            path = f"mcp-infrastructure/{self.infrastructure_id}.json"

            mcp.vault_write(path, json.dumps(state_dict, indent=2))

            logger.debug(f"Infrastructure checkpoint saved: {path}")
            return True

        except Exception as e:
            logger.exception(f"Checkpoint save failed: {e}")
            return False

    async def _restore_infrastructure_state(self) -> MCPInfrastructureState | None:
        """Restore infrastructure state from checkpoint."""
        try:
            from cohezion.core.mcp_client import get_mcp_client

            mcp = get_mcp_client()
            path = f"mcp-infrastructure/{self.infrastructure_id}.json"

            content = mcp.vault_read(path)
            data = json.loads(content)

            # Reconstruct state
            state = MCPInfrastructureState(
                infrastructure_id=data["infrastructure_id"],
                redis_connected=data.get("redis_connected", False),
                total_uptime_seconds=data.get("total_uptime_seconds", 0.0),
                created_at=data.get("created_at", time.time()),
            )

            # Reconstruct server states
            for server_name, server_data in data.get("servers", {}).items():
                state.servers[server_name] = MCPServerState(
                    server_name=server_name,
                    port=server_data["port"],
                    status=server_data.get("status", "stopped"),
                    start_time=server_data.get("start_time", time.time()),
                    restart_count=server_data.get("restart_count", 0),
                    total_requests=server_data.get("total_requests", 0),
                    total_errors=server_data.get("total_errors", 0),
                )

            logger.info("Restored infrastructure state from checkpoint")
            return state

        except Exception as e:
            logger.debug(f"No checkpoint found or restore failed: {e}")
            return None

    def _state_to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            "infrastructure_id": self.state.infrastructure_id,
            "created_at": self.state.created_at,
            "redis_connected": self.state.redis_connected,
            "total_uptime_seconds": self.state.total_uptime_seconds,
            "servers": {
                name: {
                    "server_name": s.server_name,
                    "port": s.port,
                    "status": s.status,
                    "start_time": s.start_time,
                    "restart_count": s.restart_count,
                    "total_requests": s.total_requests,
                    "total_errors": s.total_errors,
                    "last_health_check": s.last_health_check,
                }
                for name, s in self.state.servers.items()
            },
        }

    async def __aenter__(self) -> "CompoundMCPSessionManager":
        """Async context manager entry."""
        await self.start_infrastructure()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop_infrastructure(graceful=True)


# Global compound MCP session manager
_compound_mcp_manager: CompoundMCPSessionManager | None = None


def get_compound_mcp_manager(infrastructure_id: str | None = None) -> CompoundMCPSessionManager:
    """Get or create global compound MCP session manager.

    Args:
        infrastructure_id: Optional ID for infrastructure

    Returns:
        CompoundMCPSessionManager singleton
    """
    global _compound_mcp_manager
    if _compound_mcp_manager is None:
        _compound_mcp_manager = CompoundMCPSessionManager(infrastructure_id)
    return _compound_mcp_manager


async def start_compound_mcp_infrastructure(
    servers: list[dict[str, Any]] | None = None, max_cache_entries: int = 256
) -> dict[str, Any]:
    """Convenience function to start compound MCP infrastructure.

    Args:
        servers: Server configs to start
        max_cache_entries: Cache entries to warm-load

    Returns:
        Start summary
    """
    manager = get_compound_mcp_manager()
    return await manager.start_infrastructure(servers, max_cache_entries)


async def stop_compound_mcp_infrastructure(graceful: bool = True) -> dict[str, Any]:
    """Convenience function to stop compound MCP infrastructure.

    Args:
        graceful: Whether to wait for in-flight requests

    Returns:
        Shutdown summary
    """
    global _compound_mcp_manager
    if _compound_mcp_manager:
        result = await _compound_mcp_manager.stop_infrastructure(graceful)
        _compound_mcp_manager = None
        return result
    return {"error": "No MCP infrastructure running"}
