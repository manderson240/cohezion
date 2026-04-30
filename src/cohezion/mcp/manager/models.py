"""MCP Server Manager - data models and configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    import subprocess


# Port allocation range for all MCP servers
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
        safe_env = {}
        for k, v in self.env_vars.items():
            if any(secret in k.lower() for secret in ["token", "key", "secret", "password"]):
                safe_env[k] = "***REDACTED***"
            else:
                safe_env[k] = v

        return {
            "name": self.name,
            "port": self.port,
            "entry_point": self.entry_point,
            "auto_restart": self.auto_restart,
            "health_check_interval": self.health_check_interval,
            "max_restarts": self.max_restarts,
            "env_vars": safe_env,
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
