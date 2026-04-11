"""Dynamic agent registry with hot-reload capability.

Enables runtime agent registration, file watching for hot-reload,
and adaptive agent lifecycle management.
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import inspect
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from cohezion.swarm.specialist_agents import SpecialistAgent


logger = logging.getLogger(__name__)


@dataclass
class AgentModule:
    """Dynamically loaded agent module with metadata."""
    name: str
    version: str
    class_ref: type[SpecialistAgent]
    capabilities: list[str]
    load_path: Path | None
    checksum: str
    loaded_at: datetime = field(default_factory=datetime.now)
    active: bool = True
    instance: SpecialistAgent | None = None
    performance_stats: dict[str, Any] = field(default_factory=dict)

    def create_instance(self) -> SpecialistAgent:
        """Create agent instance from class reference."""
        if self.instance is None:
            self.instance = self.class_ref()
        return self.instance

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "capabilities": self.capabilities,
            "loaded_at": self.loaded_at.isoformat(),
            "active": self.active,
            "performance": self.performance_stats,
        }


class DynamicAgentRegistry:
    """Hot-swappable agent registry with runtime loading.
    
    Features:
    - Hot-reload: Update agents without restart
    - Runtime registration: Add agents from Python files
    - File watching: Auto-detect and reload changes
    - Performance tracking: Update metrics for adaptive routing
    """

    def __init__(self, modules_dir: Path | None = None):
        self.modules_dir = modules_dir or Path(
            __file__).parent / "agents" / "modules"
        self._agents: dict[str, AgentModule] = {}
        self._watchers: dict[str, Callable] = {}
        self._file_hashes: dict[str, str] = {}
        self._reload_task: asyncio.Task | None = None
        self._running = False
        self._check_interval = 5.0  # seconds

        # Load built-in specialists
        self._load_builtin_specialists()

    def _load_builtin_specialists(self):
        """Load validated specialists from specialist_agents module."""
        from cohezion.swarm.specialist_agents import VALIDATED_SPECIALISTS

        for name, agent in VALIDATED_SPECIALISTS.items():
            module = AgentModule(
                name=agent.name,
                version="1.0.0",
                class_ref=type(agent),
                capabilities=agent.capabilities,
                load_path=None,  # Built-in
                checksum="builtin",
                active=True,
                instance=agent,  # Use existing instance
            )
            self._agents[agent.name] = module
            logger.info(f"Loaded built-in specialist: {agent.name}")

    async def start_watching(self, interval: float | None = None):
        """Start file watcher for hot-reloading.
        
        Args:
            interval: Check interval in seconds (default: 5.0)
        """
        if self._running:
            logger.warning("File watcher already running")
            return

        self._check_interval = interval or self._check_interval
        self._running = True
        self._reload_task = asyncio.create_task(
            self._watch_loop(),
            name="agent_reload_watcher"
        )
        logger.info(f"Started file watcher (interval: {self._check_interval}s)")

    async def stop_watching(self):
        """Stop file watcher."""
        if not self._running:
            return

        self._running = False
        if self._reload_task:
            self._reload_task.cancel()
            try:
                await self._reload_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped file watcher")

    async def _watch_loop(self):
        """Main watch loop for file changes."""
        while self._running:
            try:
                await self._check_for_changes()
            except Exception as e:
                logger.error(f"Error in watch loop: {e}")

            await asyncio.sleep(self._check_interval)

    async def _check_for_changes(self):
        """Check module files for changes and reload."""
        if not self.modules_dir.exists():
            return

        # Check existing modules
        for agent_name, module in list(self._agents.items()):
            if not module.active or not module.load_path:
                continue

            file_path = module.load_path
            if not file_path.exists():
                # File deleted - deactivate
                await self._deactivate_agent(agent_name)
                logger.info(f"Deactivated agent (file deleted): {agent_name}")
                continue

            current_hash = self._compute_hash(file_path)
            if current_hash != module.checksum:
                logger.info(f"Detected change in {agent_name}, hot-reloading...")
                await self._reload_agent(agent_name, file_path)

        # Check for new modules
        await self._discover_new_modules()

    async def _discover_new_modules(self):
        """Discover and auto-register new modules."""
        if not self.modules_dir.exists():
            return

        for py_file in self.modules_dir.glob("*_agent.py"):
            agent_name = py_file.stem.replace("_agent", "").title()

            # Check if already registered
            if any(m.load_path == py_file for m in self._agents.values()):
                continue

            try:
                await self.register_from_file(py_file)
                logger.info(f"Auto-discovered and registered: {agent_name}")
            except Exception as e:
                logger.error(f"Failed to auto-discover {py_file}: {e}")

    def _compute_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file for change detection."""
        try:
            content = file_path.read_bytes()
            return hashlib.sha256(content).hexdigest()[:16]
        except Exception:
            return ""

    async def register_from_file(
        self,
        file_path: Path,
        activate: bool = True
    ) -> str:
        """Register agent from Python file at runtime.
        
        Args:
            file_path: Path to Python file containing agent class
            activate: Whether to activate immediately
            
        Returns:
            Name of registered agent
            
        Raises:
            ValueError: If no valid agent class found
            ImportError: If module cannot be loaded
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Load module
        module_name = file_path.stem
        spec = importlib.util.spec_from_file_location(
            module_name, file_path
        )
        if not spec or not spec.loader:
            raise ImportError(f"Cannot load module from {file_path}")

        module = importlib.util.module_from_spec(spec)

        # Execute module
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise ImportError(f"Failed to execute module: {e}")

        # Find agent class
        agent_class = None
        agent_metadata = None

        for name, obj in inspect.getmembers(module):
            if not inspect.isclass(obj):
                continue

            # Check for SpecialistAgent subclass
            if issubclass(obj, SpecialistAgent) and obj != SpecialistAgent:
                agent_class = obj

                # Try to get metadata from __agent_metadata__
                if hasattr(obj, "__agent_metadata__"):
                    agent_metadata = obj.__agent_metadata__
                break

        if not agent_class:
            raise ValueError(
                f"No SpecialistAgent subclass found in {file_path}"
            )

        # Extract name from metadata or class name
        if agent_metadata:
            agent_name = agent_metadata.get("name", agent_class.__name__)
            version = agent_metadata.get("version", "1.0.0")
            capabilities = agent_metadata.get("capabilities", [])
        else:
            agent_name = agent_class.__name__
            version = "1.0.0"
            capabilities = []

        # Create module entry
        agent_module = AgentModule(
            name=agent_name,
            version=version,
            class_ref=agent_class,
            capabilities=capabilities,
            load_path=file_path,
            checksum=self._compute_hash(file_path),
            active=activate,
            loaded_at=datetime.now(),
        )

        # Check if replacing existing
        if agent_name in self._agents and self._agents[agent_name].active:
            logger.info(f"Replacing existing agent: {agent_name}")

        self._agents[agent_name] = agent_module

        # Notify watchers
        await self._notify_registration(agent_name, agent_module)

        logger.info(f"Registered agent: {agent_name} v{version}")
        return agent_name

    async def _reload_agent(self, name: str, file_path: Path):
        """Hot-reload agent module."""
        old_module = self._agents.get(name)
        if old_module:
            old_module.active = False
            old_version = old_module.version
        else:
            old_version = "unknown"

        try:
            await self.register_from_file(file_path)
            new_module = self._agents[name]
            logger.info(
                f"Hot-reloaded {name}: {old_version} → {new_module.version}"
            )
            await self._notify_reload(name, old_module, new_module)
        except Exception as e:
            logger.error(f"Failed to reload {name}: {e}")
            # Restore old module
            if old_module:
                old_module.active = True
            raise

    async def _deactivate_agent(self, name: str):
        """Deactivate agent (mark as inactive)."""
        if name in self._agents:
            self._agents[name].active = False
            await self._notify_deactivation(name)

    async def unregister(self, name: str, force: bool = False) -> bool:
        """Unregister agent.
        
        Args:
            name: Name of agent to unregister
            force: If True, remove immediately; if False, deactivate gracefully
            
        Returns:
            True if successful
        """
        if name not in self._agents:
            logger.warning(f"Cannot unregister unknown agent: {name}")
            return False

        if force:
            del self._agents[name]
            logger.info(f"Force unregistered: {name}")
        else:
            await self._deactivate_agent(name)
            logger.info(f"Deactivated: {name} (can be reactivated)")

        return True

    async def reactivate(self, name: str) -> bool:
        """Reactivate a previously deactivated agent."""
        if name not in self._agents:
            logger.warning(f"Cannot reactivate unknown agent: {name}")
            return False

        module = self._agents[name]

        # If loaded from file, check if file still exists
        if module.load_path and not module.load_path.exists():
            logger.error(f"Cannot reactivate {name}: source file not found")
            return False

        module.active = True
        module.loaded_at = datetime.now()
        logger.info(f"Reactivated agent: {name}")

        await self._notify_reactivation(name, module)
        return True

    # ═══════════════════════════════════════════════════════════════════
    # Query Methods
    # ═══════════════════════════════════════════════════════════════════

    def get_agent(self, name: str) -> AgentModule | None:
        """Get active agent by name."""
        agent = self._agents.get(name)
        if agent and agent.active:
            return agent
        return None

    def get_agent_instance(self, name: str) -> SpecialistAgent | None:
        """Get agent instance by name."""
        module = self.get_agent(name)
        if module:
            return module.create_instance()
        return None

    def list_agents(
        self,
        active_only: bool = True,
        capability: str | None = None
    ) -> list[AgentModule]:
        """List agents with optional filtering.
        
        Args:
            active_only: If True, only return active agents
            capability: If specified, only return agents with this capability
            
        Returns:
            List of matching AgentModule instances
        """
        agents = list(self._agents.values())

        if active_only:
            agents = [a for a in agents if a.active]

        if capability:
            agents = [
                a for a in agents
                if capability in a.capabilities
            ]

        return agents

    def list_agent_names(
        self,
        active_only: bool = True
    ) -> list[str]:
        """List agent names."""
        return [a.name for a in self.list_agents(active_only=active_only)]

    def get_agents_by_capability(
        self,
        capability: str
    ) -> list[AgentModule]:
        """Get all agents with specific capability."""
        return self.list_agents(capability=capability)

    # ═══════════════════════════════════════════════════════════════════
    # Performance Tracking
    # ═══════════════════════════════════════════════════════════════════

    def update_performance(
        self,
        name: str,
        metrics: dict[str, Any]
    ):
        """Update performance stats for adaptive routing.
        
        Args:
            name: Agent name
            metrics: Performance metrics dict
        """
        if name not in self._agents:
            logger.warning(f"Cannot update performance for unknown agent: {name}")
            return

        agent = self._agents[name]
        agent.performance_stats.update(metrics)

        # Also update agent instance if exists
        if agent.instance:
            if "performance" not in agent.instance.performance_stats:
                agent.instance.performance_stats["performance"] = {}
            agent.instance.performance_stats["performance"].update(metrics)

    def get_performance_summary(self, name: str) -> dict[str, Any] | None:
        """Get performance summary for agent."""
        agent = self._agents.get(name)
        if agent:
            return {
                "name": name,
                "active": agent.active,
                "loaded_at": agent.loaded_at.isoformat(),
                **agent.performance_stats
            }
        return None

    def get_all_performance(self) -> dict[str, dict[str, Any]]:
        """Get performance for all agents."""
        return {
            name: self.get_performance_summary(name)
            for name in self._agents.keys()
        }

    # ═══════════════════════════════════════════════════════════════════
    # Watcher Notifications
    # ═══════════════════════════════════════════════════════════════════

    def register_watcher(
        self,
        name: str,
        callback: Callable[[str, str, AgentModule], None]
    ):
        """Register callback for agent lifecycle events.
        
        Args:
            name: Watcher identifier
            callback: Function(event_type, agent_name, agent_module)
        """
        self._watchers[name] = callback
        logger.debug(f"Registered watcher: {name}")

    def unregister_watcher(self, name: str):
        """Unregister watcher."""
        if name in self._watchers:
            del self._watchers[name]
            logger.debug(f"Unregistered watcher: {name}")

    async def _notify_event(
        self,
        event_type: str,
        agent_name: str,
        module: AgentModule
    ):
        """Notify all watchers of event."""
        for watcher_name, callback in self._watchers.items():
            try:
                result = callback(event_type, agent_name, module)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Watcher {watcher_name} failed: {e}")

    async def _notify_registration(
        self,
        name: str,
        module: AgentModule
    ):
        """Notify watchers of registration."""
        await self._notify_event("registered", name, module)

    async def _notify_reload(
        self,
        name: str,
        old_module: AgentModule,
        new_module: AgentModule
    ):
        """Notify watchers of reload."""
        await self._notify_event("reloaded", name, new_module)

    async def _notify_deactivation(self, name: str):
        """Notify watchers of deactivation."""
        if name in self._agents:
            await self._notify_event(
                "deactivated",
                name,
                self._agents[name]
            )

    async def _notify_reactivation(self, name: str, module: AgentModule):
        """Notify watchers of reactivation."""
        await self._notify_event("reactivated", name, module)

    # ═══════════════════════════════════════════════════════════════════
    # Persistence
    # ═══════════════════════════════════════════════════════════════════

    async def save_state(self, path: Path | None = None):
        """Save registry state to disk."""
        save_path = path or Path("data/agent_registry_state.json")
        save_path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "agents": {
                name: module.to_dict()
                for name, module in self._agents.items()
            },
            "saved_at": datetime.now().isoformat(),
            "check_interval": self._check_interval,
        }

        save_path.write_text(json.dumps(state, indent=2))
        logger.info(f"Saved registry state to {save_path}")

    async def load_state(self, path: Path | None = None) -> bool:
        """Load registry state from disk."""
        load_path = path or Path("data/agent_registry_state.json")

        if not load_path.exists():
            logger.warning(f"State file not found: {load_path}")
            return False

        try:
            state = json.loads(load_path.read_text())

            # Note: This only restores metadata, not actual modules
            # Would need to reload from files
            logger.info(f"Loaded registry state from {load_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return False

    def __repr__(self) -> str:
        """String representation."""
        active = len([a for a in self._agents.values() if a.active])
        total = len(self._agents)
        return f"DynamicAgentRegistry(active={active}, total={total})"


# Global registry instance for convenience
_global_registry: DynamicAgentRegistry | None = None


def get_global_registry() -> DynamicAgentRegistry:
    """Get or create global registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = DynamicAgentRegistry()
    return _global_registry


def reset_global_registry():
    """Reset global registry (useful for testing)."""
    global _global_registry
    _global_registry = None
