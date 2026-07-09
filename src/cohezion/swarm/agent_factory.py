# class attrs treated as immutable config; never mutated per-instance
"""Agent Factory pattern for Cohezion swarm.

Implements decorator-based registration and dynamic agent loading
to eliminate boilerplate in agent creation.
"""

import importlib
import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cohezion.swarm.swarm_types import SwarmConfig


logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration metadata for an agent class."""

    name: str
    default_model: str
    capabilities: list[str] = field(default_factory=list)
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    tags: list[str] = field(default_factory=list)
    config_params: dict[str, Any] = field(default_factory=dict)
    requires_dependencies: list[str] = field(default_factory=list)


class AgentFactory:
    """Factory for creating and managing swarm agents.

    Implements decorator-based registration pattern:
    - @AgentFactory.register() decorator for class registration
    - Dynamic agent instantiation with dependency injection
    - Metadata-driven agent configuration
    """

    _registry: dict[str, type[Any]] = {}
    _metadata: dict[str, AgentConfig] = {}

    @classmethod
    def register(
        cls,
        name: str | None = None,
        default_model: str | None = None,
        capabilities: list[str] | None = None,
        description: str = "",
        version: str = "1.0.0",
        author: str = "",
        tags: list[str] | None = None,
        config_params: dict[str, Any] | None = None,
        requires_dependencies: list[str] | None = None,
    ) -> Callable[[type[Any]], type[Any]]:
        """Decorator to register an agent class with metadata.

        Args:
            name: Agent name (defaults to class name)
            default_model: Default LLM model for this agent
            capabilities: List of capability strings
            description: Human-readable description
            version: Agent version
            author: Author name
            tags: List of tags for categorization
            config_params: Additional configuration parameters
            requires_dependencies: List of required dependency keys

        Returns:
            Decorator function that registers the class

        Example:
            @AgentFactory.register(
                name="ResearchMiner",
                default_model="qwen3-coder:30b",
                capabilities=["research", "arxiv", "huggingface"],
                description="Mines arXiv, HF, and GitHub for SOTA research"
            )
            class NexusResearchAgent(BaseAgent):
                pass
        """

        def decorator(agent_class: type[Any]) -> type[Any]:
            registry_name = name or agent_class.__name__

            config = AgentConfig(
                name=registry_name,
                default_model=default_model or getattr(agent_class, "_default_model", "gemma3:4b"),
                capabilities=capabilities or getattr(agent_class, "_capabilities", []),
                description=description or agent_class.__doc__ or "",
                version=version,
                author=author,
                tags=tags or [],
                config_params=config_params or {},
                requires_dependencies=requires_dependencies or [],
            )

            cls._registry[registry_name] = agent_class
            cls._metadata[registry_name] = config

            logger.info(
                f"Registered agent: {registry_name} "
                f"(model: {config.default_model}, "
                f"capabilities: {len(config.capabilities)})"
            )

            return agent_class

        return decorator

    @classmethod
    def create(
        cls,
        agent_name: str,
        model: str | None = None,
        config: SwarmConfig | None = None,
        dependencies: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Create an agent instance by name.

        Args:
            agent_name: Name of the registered agent
            model: Override default model
            config: Swarm configuration
            dependencies: Injected dependencies (HTTPClient, cache, etc.)
            **kwargs: Additional agent-specific arguments

        Returns:
            Instantiated agent

        Raises:
            ValueError: If agent not registered
            RuntimeError: If dependency requirements not met

        Example:
            agent = AgentFactory.create(
                "NexusResearchAgent",
                model="llama3:70b",
                dependencies={"cache": my_cache, "security": my_guard}
            )
        """
        if agent_name not in cls._registry:
            raise ValueError(f"Agent '{agent_name}' not registered")

        agent_class = cls._registry[agent_name]
        metadata = cls._metadata[agent_name]

        model_name = model or metadata.default_model

        if dependencies is None:
            dependencies = {}

        required = metadata.requires_dependencies
        missing = [dep for dep in required if dep not in dependencies]
        if missing:
            raise RuntimeError(f"Agent '{agent_name}' requires dependencies: {missing}")

        try:
            sig = inspect.signature(agent_class.__init__)
            init_params = sig.parameters

            init_kwargs = {
                "model_name": model_name,
                "config": config,
            }
            init_kwargs.update(kwargs)

            for dep_name, dep_value in dependencies.items():
                if dep_name in init_params:
                    init_kwargs[dep_name] = dep_value

            instance = agent_class(**init_kwargs)

            logger.debug(f"Created agent: {agent_name} with model {model_name}")
            return instance

        except Exception as e:
            logger.error(f"Failed to create agent '{agent_name}': {e}")
            raise

    @classmethod
    def get_metadata(cls, agent_name: str) -> AgentConfig | None:
        """Get metadata for a registered agent.

        Args:
            agent_name: Name of the agent

        Returns:
            AgentConfig or None if not found
        """
        return cls._metadata.get(agent_name)

    @classmethod
    def list_agents(
        cls,
        capability: str | None = None,
        tag: str | None = None,
    ) -> list[str]:
        """List registered agents, optionally filtered.

        Args:
            capability: Filter by capability
            tag: Filter by tag

        Returns:
            List of agent names
        """
        agents = list(cls._registry.keys())

        if capability:
            agents = [name for name in agents if capability in cls._metadata[name].capabilities]

        if tag:
            agents = [name for name in agents if tag in cls._metadata[name].tags]

        return agents

    @classmethod
    def find_by_capability(cls, capability: str) -> list[tuple[str, AgentConfig]]:
        """Find agents that support a given capability.

        Args:
            capability: The capability to search for

        Returns:
            List of (agent_name, config) tuples
        """
        return [
            (name, config)
            for name, config in cls._metadata.items()
            if capability in config.capabilities
        ]

    @classmethod
    def is_registered(cls, agent_name: str) -> bool:
        """Check if an agent is registered.

        Args:
            agent_name: Name of the agent

        Returns:
            True if registered
        """
        return agent_name in cls._registry

    @classmethod
    def get_registry_size(cls) -> int:
        """Get the number of registered agents."""
        return len(cls._registry)

    @classmethod
    def discover_agents(cls, agents_dir: Path | str) -> int:
        """Dynamically discover and register agents from directory.

        Scans the agents directory for Python files and imports them
        to trigger decorator registration.

        Args:
            agents_dir: Path to agents directory

        Returns:
            Number of newly discovered agents
        """
        agents_path = Path(agents_dir)
        if not agents_path.exists():
            logger.warning(f"Agents directory not found: {agents_path}")
            return 0

        before = cls.get_registry_size()

        for py_file in agents_path.glob("*_agent.py"):
            if py_file.name.startswith("_") or py_file.name.endswith("_test.py"):
                continue

            module_name = py_file.stem

            try:
                module_path = f"cohezion.agents.{module_name}"
                importlib.import_module(module_path)
            except ImportError as e:
                logger.debug(f"Could not import {module_name}: {e}")

        discovered = cls.get_registry_size() - before
        logger.info(f"Discovered {discovered} agents from {agents_path}")
        return discovered

    @classmethod
    def get_default_model(cls, agent_name: str) -> str:
        """Get the default model for a registered agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Default model name

        Raises:
            ValueError: If agent not registered
        """
        if agent_name not in cls._metadata:
            raise ValueError(f"Agent '{agent_name}' not registered")
        return cls._metadata[agent_name].default_model

    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered agents (useful for testing)."""
        cls._registry.clear()
        cls._metadata.clear()
        logger.warning("Agent registry cleared")
