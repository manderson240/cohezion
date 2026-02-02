"""Agent composition system for mixin-based agent construction.

Replaces deep inheritance with composable behaviors for better modularity.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, TypeVar
from typing_extensions import Self

logger = logging.getLogger(__name__)


class AgentBehavior(Protocol):
    """Protocol for composable agent behaviors."""

    async def on_init(self, agent: ComposableAgent) -> None: ...
    async def on_process(self, agent: ComposableAgent, **kwargs) -> dict[str, Any]: ...
    async def on_cleanup(self, agent: ComposableAgent) -> None: ...


class ComposableAgent:
    """Base agent that supports mixin-based composition.

    Usage:
        agent = (AgentBuilder("model_name")
            .with_behavior(SecurityBehavior())
            .with_behavior(CachingBehavior())
            .with_behavior(PersistenceBehavior())
            .build())

        result = await agent.process(prompt="Hello")
    """

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._behaviors: list[AgentBehavior] = []
        self._config: dict[str, Any] = {}
        self._state: dict[str, Any] = {}
        self._initialized = False

    def add_behavior(self, behavior: AgentBehavior) -> None:
        """Add a behavior mixin."""
        self._behaviors.append(behavior)

    async def initialize(self) -> None:
        """Initialize all behaviors."""
        if self._initialized:
            return

        for behavior in self._behaviors:
            try:
                await behavior.on_init(self)
            except Exception as e:
                logger.error(f"Behavior init failed: {e}")

        self._initialized = True

    async def process(self, **kwargs) -> dict[str, Any]:
        """Process with all behaviors."""
        if not self._initialized:
            await self.initialize()

        # Run through behavior chain
        context = {"input": kwargs, "output": None}

        for behavior in self._behaviors:
            try:
                result = await behavior.on_process(self, **context)
                if result:
                    context.update(result)
            except Exception as e:
                logger.error(f"Behavior processing failed: {e}")
                raise

        return context.get("output", {})

    async def cleanup(self) -> None:
        """Cleanup all behaviors."""
        for behavior in reversed(self._behaviors):
            try:
                await behavior.on_cleanup(self)
            except Exception as e:
                logger.error(f"Behavior cleanup failed: {e}")


class SecurityBehavior:
    """Security validation behavior."""

    def __init__(self, pipeline=None):
        from .security_pipeline import get_security_pipeline

        self._pipeline = pipeline
        self._get_pipeline = get_security_pipeline

    async def on_init(self, agent: ComposableAgent) -> None:
        if self._pipeline is None:
            self._pipeline = await self._get_pipeline()

    async def on_process(self, agent: ComposableAgent, **kwargs) -> dict[str, Any]:
        input_data = kwargs.get("input", {})
        prompt = input_data.get("prompt", "")

        # Check input
        result = await self._pipeline.check_input(prompt)
        if not result.allowed:
            return {"output": {"error": f"Security violation: {result.reason}"}}

        return {"input": input_data}  # Continue processing

    async def on_cleanup(self, agent: ComposableAgent) -> None:
        pass


class CachingBehavior:
    """Response caching behavior."""

    def __init__(self, ttl_seconds: int = 3600):
        from .cache_manager import get_cache_manager

        self._ttl = ttl_seconds
        self._cache = None
        self._get_cache = get_cache_manager

    async def on_init(self, agent: ComposableAgent) -> None:
        if self._cache is None:
            self._cache = await self._get_cache()

    async def on_process(self, agent: ComposableAgent, **kwargs) -> dict[str, Any]:
        input_data = kwargs.get("input", {})
        prompt = input_data.get("prompt", "")

        # Try cache first
        entry = await self._cache.get(agent.model_name, prompt)
        if entry:
            return {
                "output": {
                    "response": entry.response,
                    "cached": True,
                    "phi_score": entry.phi_score,
                }
            }

        return {"input": input_data, "cache_miss": True}

    async def on_cleanup(self, agent: ComposableAgent) -> None:
        pass


class PersistenceBehavior:
    """Database persistence behavior."""

    def __init__(self, repository_factory=None):
        from .repositories import get_repository_factory

        self._factory = repository_factory
        self._get_factory = get_repository_factory
        self._journey_repo = None

    async def on_init(self, agent: ComposableAgent) -> None:
        if self._factory is None:
            self._factory = self._get_factory()
        self._journey_repo = self._factory.journey_repository()

    async def on_process(self, agent: ComposableAgent, **kwargs) -> dict[str, Any]:
        # Could log journey steps here
        return {}

    async def on_cleanup(self, agent: ComposableAgent) -> None:
        pass


class EventPublishingBehavior:
    """Event publishing behavior."""

    def __init__(self, event_bus=None):
        from .event_bus import get_event_bus

        self._bus = event_bus
        self._get_bus = get_event_bus

    async def on_init(self, agent: ComposableAgent) -> None:
        if self._bus is None:
            self._bus = await self._get_bus()

    async def on_process(self, agent: ComposableAgent, **kwargs) -> dict[str, Any]:
        from .event_bus import Event

        input_data = kwargs.get("input", {})

        # Publish agent start event
        await self._bus.publish(
            Event.agent_start(
                agent_name=agent.__class__.__name__,
                model=agent.model_name,
                prompt_length=len(input_data.get("prompt", "")),
            )
        )

        return {"input": input_data}

    async def on_cleanup(self, agent: ComposableAgent) -> None:
        pass


class AgentBuilder:
    """Builder for constructing composable agents.

    Usage:
        agent = (AgentBuilder("phi4")
            .with_security()
            .with_caching(ttl_seconds=3600)
            .with_persistence()
            .with_events()
            .build())
    """

    def __init__(self, model_name: str):
        self._model_name = model_name
        self._behaviors: list[AgentBehavior] = []

    def with_security(self) -> Self:
        """Add security validation."""
        self._behaviors.append(SecurityBehavior())
        return self

    def with_caching(self, ttl_seconds: int = 3600) -> Self:
        """Add response caching."""
        self._behaviors.append(CachingBehavior(ttl_seconds))
        return self

    def with_persistence(self) -> Self:
        """Add database persistence."""
        self._behaviors.append(PersistenceBehavior())
        return self

    def with_events(self) -> Self:
        """Add event publishing."""
        self._behaviors.append(EventPublishingBehavior())
        return self

    def with_behavior(self, behavior: AgentBehavior) -> Self:
        """Add custom behavior."""
        self._behaviors.append(behavior)
        return self

    def build(self) -> ComposableAgent:
        """Build the agent."""
        agent = ComposableAgent(self._model_name)
        for behavior in self._behaviors:
            agent.add_behavior(behavior)
        return agent
