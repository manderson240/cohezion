"""Unified registry consolidating skill, capability, and MCP registries.

Provides a single interface for discovering and registering capabilities
across the system with plugin-based architecture.
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Capability:
    """Unified capability descriptor."""

    id: str
    name: str
    type: str  # "skill", "agent", "mcp", "tool"
    description: str
    provider: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "provider": self.provider,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Capability:
        return cls(
            id=data["id"],
            name=data["name"],
            type=data["type"],
            description=data.get("description", ""),
            provider=data.get("provider", ""),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


class RegistryPlugin(ABC):
    """Base class for registry plugins."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def scan(self) -> list[Capability]: ...

    @abstractmethod
    async def search(
        self, query: str, limit: int = 10
    ) -> list[tuple[Capability, float]]: ...


class SkillRegistryPlugin(RegistryPlugin):
    """Plugin for skill-based capabilities."""

    def __init__(self, registry_file: Path | str = "skills_registry.json"):
        self._file = Path(registry_file)
        self._skills: dict[str, Capability] = {}
        self._vectorizer = TfidfVectorizer(max_features=1000, stop_words="english")
        self._skill_vectors: np.ndarray | None = None
        self._last_scan = 0.0

    @property
    def name(self) -> str:
        return "skills"

    async def scan(self) -> list[Capability]:
        """Load skills from registry file."""
        if not self._file.exists():
            return []

        try:
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, self._file.read_text)
            data = json.loads(content)

            skills = []
            for skill_id, skill_data in data.get("skills", {}).items():
                cap = Capability(
                    id=skill_id,
                    name=skill_data.get("name", skill_id),
                    type="skill",
                    description=skill_data.get("description", ""),
                    provider=skill_data.get("source_file", ""),
                    tags=skill_data.get("tags", []),
                    metadata=skill_data,
                )
                skills.append(cap)
                self._skills[skill_id] = cap

            # Build search index
            if skills:
                descriptions = [s.description for s in skills]
                self._skill_vectors = self._vectorizer.fit_transform(descriptions)

            return skills

        except Exception as e:
            logger.error(f"Skill registry scan failed: {e}")
            return []

    async def search(
        self, query: str, limit: int = 10
    ) -> list[tuple[Capability, float]]:
        """Search skills using TF-IDF similarity."""
        if not self._skills or self._skill_vectors is None:
            await self.scan()

        if not self._skills:
            return []

        try:
            query_vec = self._vectorizer.transform([query])
            similarities = cosine_similarity(query_vec, self._skill_vectors)[0]

            # Get top matches
            skill_list = list(self._skills.values())
            indexed_sims = [(i, sim) for i, sim in enumerate(similarities)]
            indexed_sims.sort(key=lambda x: x[1], reverse=True)

            results = []
            for idx, sim in indexed_sims[:limit]:
                if sim > 0.1:  # Minimum similarity threshold
                    results.append((skill_list[idx], float(sim)))

            return results

        except Exception as e:
            logger.error(f"Skill search failed: {e}")
            return []

        try:
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, self._file.read_text)
            data = json.loads(content)

            skills = []
            for skill_id, skill_data in data.get("skills", {}).items():
                cap = Capability(
                    id=skill_id,
                    name=skill_data.get("name", skill_id),
                    type="skill",
                    description=skill_data.get("description", ""),
                    provider=skill_data.get("source_file", ""),
                    tags=skill_data.get("tags", []),
                    metadata=skill_data,
                )
                skills.append(cap)
                self._skills[skill_id] = cap

            return skills

        except Exception as e:
            logger.error(f"Skill registry scan failed: {e}")
            return []

    async def search(
        self, query: str, limit: int = 10
    ) -> list[tuple[Capability, float]]:
        """Search skills using keyword matching."""
        if not self._skills:
            await self.scan()

        if not self._skills:
            return []

        try:
            # Score all skills
            scored = []
            for skill in self._skills.values():
                score = self._compute_similarity(query, skill)
                if score > 0.1:  # Minimum threshold
                    scored.append((skill, score))

            # Sort by score and return top matches
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:limit]

        except Exception as e:
            logger.error(f"Skill search failed: {e}")
            return []
            return []


class AgentRegistryPlugin(RegistryPlugin):
    """Plugin for agent-based capabilities."""

    def __init__(self, agents_path: Path | str = "src/cohezion/swarm/agents"):
        self._path = Path(agents_path)
        self._agents: dict[str, Capability] = {}

    @property
    def name(self) -> str:
        return "agents"

    async def scan(self) -> list[Capability]:
        """Scan for available agent classes."""
        agents = []

        if not self._path.exists():
            return agents

        try:
            for file_path in self._path.glob("*.py"):
                if file_path.name.startswith("_"):
                    continue

                agent_name = file_path.stem.replace("_agent", "").replace("agent", "")
                cap = Capability(
                    id=f"agent:{agent_name}",
                    name=agent_name,
                    type="agent",
                    description=f"Agent implementation from {file_path.name}",
                    provider=str(file_path),
                    tags=["agent", agent_name],
                )
                agents.append(cap)
                self._agents[cap.id] = cap

            return agents

        except Exception as e:
            logger.error(f"Agent registry scan failed: {e}")
            return []

    async def search(
        self, query: str, limit: int = 10
    ) -> list[tuple[Capability, float]]:
        """Simple keyword search for agents."""
        if not self._agents:
            await self.scan()

        query_lower = query.lower()
        results = []

        for agent in self._agents.values():
            score = 0.0
            if query_lower in agent.name.lower():
                score = 1.0
            elif query_lower in agent.description.lower():
                score = 0.5
            elif any(query_lower in tag.lower() for tag in agent.tags):
                score = 0.3

            if score > 0:
                results.append((agent, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]


class MCPRegistryPlugin(RegistryPlugin):
    """Plugin for MCP server capabilities."""

    def __init__(self, mcp_servers: dict[str, Any] | None = None):
        self._servers = mcp_servers or {}
        self._capabilities: dict[str, Capability] = {}

    @property
    def name(self) -> str:
        return "mcp"

    async def scan(self) -> list[Capability]:
        """Scan registered MCP servers."""
        capabilities = []

        for server_name, server_info in self._servers.items():
            cap = Capability(
                id=f"mcp:{server_name}",
                name=server_name,
                type="mcp",
                description=server_info.get(
                    "description", f"MCP server: {server_name}"
                ),
                provider=server_info.get("endpoint", ""),
                tags=["mcp", server_name] + server_info.get("tags", []),
                metadata=server_info,
            )
            capabilities.append(cap)
            self._capabilities[cap.id] = cap

        return capabilities

    async def search(
        self, query: str, limit: int = 10
    ) -> list[tuple[Capability, float]]:
        """Search MCP capabilities."""
        if not self._capabilities:
            await self.scan()

        query_lower = query.lower()
        results = []

        for cap in self._capabilities.values():
            score = 0.0
            if query_lower in cap.name.lower():
                score = 1.0
            elif query_lower in cap.description.lower():
                score = 0.5
            elif any(query_lower in tag.lower() for tag in cap.tags):
                score = 0.3

            if score > 0:
                results.append((cap, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]


class UnifiedRegistry:
    """Unified registry combining all capability sources.

    Usage:
        registry = UnifiedRegistry()
        registry.register_plugin(SkillRegistryPlugin())
        registry.register_plugin(AgentRegistryPlugin())

        # Search across all sources
        results = await registry.search("data analysis", limit=5)

        # Get by type
        skills = await registry.get_by_type("skill")
    """

    def __init__(self):
        self._plugins: dict[str, RegistryPlugin] = {}
        self._all_capabilities: dict[str, Capability] = {}
        self._metrics = {
            "searches": 0,
            "scans": 0,
        }

    def register_plugin(self, plugin: RegistryPlugin) -> None:
        """Register a capability plugin."""
        self._plugins[plugin.name] = plugin
        logger.info(f"Registered registry plugin: {plugin.name}")

    async def scan_all(self) -> dict[str, list[Capability]]:
        """Scan all plugins for capabilities."""
        self._metrics["scans"] += 1
        results = {}

        for name, plugin in self._plugins.items():
            caps = await plugin.scan()
            results[name] = caps

            # Update unified index
            for cap in caps:
                self._all_capabilities[cap.id] = cap

        return results

    async def search(
        self, query: str, limit: int = 10, types: list[str] | None = None
    ) -> list[tuple[Capability, float]]:
        """Search across all registered plugins.

        Args:
            query: Search query
            limit: Maximum results
            types: Filter by capability types (skill, agent, mcp, etc.)

        Returns:
            List of (capability, score) tuples sorted by relevance
        """
        self._metrics["searches"] += 1

        all_results = []

        for plugin in self._plugins.values():
            try:
                results = await plugin.search(query, limit=limit * 2)
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"Search failed in {plugin.name}: {e}")

        # Filter by type if specified
        if types:
            all_results = [
                (cap, score) for cap, score in all_results if cap.type in types
            ]

        # Sort by score and deduplicate
        all_results.sort(key=lambda x: x[1], reverse=True)
        seen = set()
        unique_results = []
        for cap, score in all_results:
            if cap.id not in seen:
                seen.add(cap.id)
                unique_results.append((cap, score))

        return unique_results[:limit]

    async def get_by_type(self, cap_type: str) -> list[Capability]:
        """Get all capabilities of a specific type."""
        if not self._all_capabilities:
            await self.scan_all()

        return [cap for cap in self._all_capabilities.values() if cap.type == cap_type]

    async def get_by_id(self, cap_id: str) -> Capability | None:
        """Get capability by ID."""
        if not self._all_capabilities:
            await self.scan_all()

        return self._all_capabilities.get(cap_id)

    def get_metrics(self) -> dict[str, Any]:
        """Get registry metrics."""
        return {
            **self._metrics,
            "plugins": len(self._plugins),
            "indexed_capabilities": len(self._all_capabilities),
        }


# Global singleton
_unified_registry: UnifiedRegistry | None = None


async def get_unified_registry() -> UnifiedRegistry:
    """Get or create global unified registry with default plugins."""
    global _unified_registry
    if _unified_registry is None:
        _unified_registry = UnifiedRegistry()

        # Register default plugins
        _unified_registry.register_plugin(SkillRegistryPlugin())
        _unified_registry.register_plugin(AgentRegistryPlugin())

        # Initial scan
        await _unified_registry.scan_all()

    return _unified_registry


def reset_unified_registry() -> None:
    """Reset global registry (for testing)."""
    global _unified_registry
    _unified_registry = None
