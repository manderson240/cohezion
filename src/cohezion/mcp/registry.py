"""
MCP Registry - Manage internal and external MCP servers.

Provides discovery, status tracking, tool invocation, and governance enforcement.

Extended with:
  - Per-tool autonomy tier requirements (cosmogonic chain governance)
  - Call tracking for SLA observability
  - Tier-based access control (can_access)

References:
  - InfoWorld (2026): How to Build an Enterprise-Grade MCP Registry
  - arXiv:2601.08687: Data Product MCP
  - Zhamak Dehghani: Data Mesh (O'Reilly, 2022)
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

MCP_REGISTRY_PATH = Path(__file__).parent / "mcp_registry.json"


@dataclass
class MCPServer:
    """Represents an MCP server."""

    name: str
    type: str
    description: str
    url: str | None = None
    path: str | None = None
    tools: list[str] | None = None
    status: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "url": self.url,
            "path": self.path,
            "tools": self.tools,
            "status": self.status,
        }


class MCPRegistry:
    """
    Registry for MCP servers.

    Manages both external (Mem0, Context7) and
    internal (Knowledge, Skills, SurrealDB, Swarm) servers.
    """

    def __init__(self, registry_path: Path | None = None):
        self.registry_path = registry_path or MCP_REGISTRY_PATH
        self._external: list[MCPServer] = []
        self._internal: list[MCPServer] = []
        self._relationships: dict[str, list[str]] = {}
        self._load()

    def _load(self) -> None:
        """Load registry from JSON."""
        if not self.registry_path.exists():
            logger.warning(f"Registry not found: {self.registry_path}")
            return

        with open(self.registry_path) as f:
            data = json.load(f)

        for server in data.get("external", []):
            self._external.append(
                MCPServer(
                    name=server["name"],
                    type=server["type"],
                    description=server["description"],
                    url=server.get("url"),
                    status=server.get("status", "unknown"),
                )
            )

        for server in data.get("internal", []):
            self._internal.append(
                MCPServer(
                    name=server["name"],
                    type=server["type"],
                    description=server["description"],
                    path=server.get("path"),
                    tools=server.get("tools", []),
                    status="available",
                )
            )

        self._relationships = data.get("relationships", {})

    def save(self) -> None:
        """Save registry to JSON."""
        data = {
            "version": "1.0",
            "external": [s.to_dict() for s in self._external],
            "internal": [s.to_dict() for s in self._internal],
            "relationships": self._relationships,
        }
        with open(self.registry_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_server(self, name: str) -> MCPServer | None:
        """Get a server by name."""
        for server in self._external + self._internal:
            if server.name == name:
                return server
        return None

    def list_servers(self, type_filter: str | None = None) -> list[MCPServer]:
        """List all servers, optionally filtered by type."""
        servers = self._external + self._internal
        if type_filter:
            servers = [s for s in servers if s.type == type_filter]
        return servers

    def list_tools(self, server_name: str | None = None) -> list[str]:
        """List all available tools."""
        tools = []
        servers = self._internal if server_name is None else [self.get_server(server_name)]
        for server in servers:
            if server and server.tools:
                tools.extend([f"{server.name}.{t}" for t in server.tools])
        return tools

    def get_relationships(self, server_name: str) -> list[str]:
        """Get related components for a server."""
        return self._relationships.get(server_name, [])

    def update_status(self, name: str, status: str) -> None:
        """Update server status."""
        server = self.get_server(name)
        if server:
            server.status = status
            self.save()

    def to_entity_dict(self) -> dict[str, Any]:
        """Export as entity for knowledge graph."""
        return {
            "id": "mcp_registry",
            "type": "registry",
            "entities": [s.name for s in self._external + self._internal],
            "relationships": [
                {"source": name, "target": rel, "type": "depends_on"}
                for name, rels in self._relationships.items()
                for rel in rels
            ],
        }

    # --- Governance extensions (Wire 5 / Horizon 3) ---

    # Tool-level autonomy tier requirements
    _tool_tiers: dict[str, str] = {
        # Read-only tools: SO(12) (observe)
        "skill_get_definition": "SO(12)",
        "vault_find_relevant_context": "SO(12)",
        "journey_get_trajectory": "SO(12)",
        "security_scan": "SO(12)",
        # Write tools: SO(3)^4 (edit)
        "vault_write": "SO(3)^4",
        "journey_save_checkpoint": "SO(3)^4",
        # Execution tools: U(1)^4 (commit)
        "compound_execute": "U(1)^4",
        "bmad_execute_workflow": "U(1)^4",
        "skill_refine": "U(1)^4",
    }

    _tier_levels = {
        "void": 0,
        "SO(12)": 1,
        "SO(3)^4": 2,
        "U(1)^4": 3,
        "Z_2^4": 4,
        "HIHO": 5,
    }

    # Call tracking for observability
    _call_counts: dict[str, int] = {}
    _error_counts: dict[str, int] = {}

    def can_access(self, agent_tier: str, tool_name: str) -> bool:
        """Check if an agent at a given tier can access a tool.

        Governance enforcement: "Without enforcement, all you're doing is cataloging risk."
        """
        agent_level = self._tier_levels.get(agent_tier, 0)
        required_tier = self._tool_tiers.get(tool_name, "SO(12)")
        required_level = self._tier_levels.get(required_tier, 1)
        return agent_level >= required_level

    def record_tool_call(self, tool_name: str, success: bool = True) -> None:
        """Record a tool call for SLA observability."""
        self._call_counts[tool_name] = self._call_counts.get(tool_name, 0) + 1
        if not success:
            self._error_counts[tool_name] = self._error_counts.get(tool_name, 0) + 1

    def get_tool_health(self, tool_name: str) -> dict[str, Any]:
        """Get health metrics for a tool."""
        calls = self._call_counts.get(tool_name, 0)
        errors = self._error_counts.get(tool_name, 0)
        return {
            "tool": tool_name,
            "calls": calls,
            "errors": errors,
            "error_rate": errors / calls if calls > 0 else 0.0,
            "required_tier": self._tool_tiers.get(tool_name, "SO(12)"),
        }


# Singleton instance
_registry: MCPRegistry | None = None


def get_registry() -> MCPRegistry:
    """Get the global MCP registry."""
    global _registry
    if _registry is None:
        _registry = MCPRegistry()
    return _registry
