"""
Agent composition system for mixin-based agent construction.

Replaces deep inheritance with composable behaviors for better modularity.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Protocol, Self

logger = logging.getLogger(__name__)


class AgentBehavior(Protocol):
    """Protocol for composable agent behaviors."""

    async def on_init(self, agent: ComposableAgent) -> None: ...
    async def on_process(self, agent: ComposableAgent, **kwargs) -> dict[str, Any]: ...
    async def on_cleanup(self, agent: ComposableAgent) -> None: ...


@dataclass
class DynamicScalingBehavior:
    """Behavior for dynamic agent scaling and composition."""

    def __init__(self, scaling_config: dict[str, Any] | None = None):
        self.scaling_config = scaling_config or {}
        self._agent_registry = None
        self._composition_rules = []

    async def on_init(self, agent: ComposableAgent) -> None:
        """Initialize dynamic scaling behavior."""
        # Get agent registry for discovering other agents
        from cohezion.core import get_unified_registry

        self._agent_registry = get_unified_registry()

        # Load composition rules from config
        self._load_composition_rules()

        # Initialize scaling state
        self._scaling_state = {
            "active_agents": set(),
            "scaling_requests": deque(),
            "last_scaling": 0,
            "metrics": {
                "created": 0,
                "destroyed": 0,
                "current_count": 0,
                "peak_count": 0,
            },
        }

        # Start scaling monitor
        asyncio.create_task(self._scaling_monitor())

    def _load_composition_rules(self) -> None:
        """Load composition rules for agent creation."""
        # Default composition rules
        self._composition_rules = [
            {
                "trigger": "high_load",
                "condition": "request_rate > 100 requests/minute",
                "composition": [
                    "SecurityBehavior",
                    "CachingBehavior",
                    "LoadBalancingBehavior",
                    "MonitoringBehavior",
                ],
                "max_instances": 10,
            },
            {
                "trigger": "complex_tasks",
                "condition": "task_complexity > 0.8",
                "composition": [
                    "SecurityBehavior",
                    "CachingBehavior",
                    "DeepAnalysisBehavior",
                    "QualityAssuranceBehavior",
                ],
                "max_instances": 5,
            },
        ]

    async def _scaling_monitor(self) -> None:
        """Monitor system load and scale agents accordingly."""
        while True:
            try:
                # Check system load
                load = await self._get_system_load()

                # Evaluate composition rules
                for rule in self._composition_rules:
                    if self._should_trigger_rule(rule, load):
                        await self._apply_scaling_rule(rule)

                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scaling monitor error: {e}")
                await asyncio.sleep(10)

    async def _get_system_load(self) -> dict[str, float]:
        """Get current system load metrics."""
        # This would integrate with system monitoring
        # For now, return mock data
        return {
            "cpu_percent": 45.0,
            "memory_percent": 65.0,
            "request_rate": 85.0,  # requests/minute
            "task_complexity": 0.7,
            "response_time": 120.0,  # ms
        }

    def _should_trigger_rule(
        self, rule: dict[str, Any], load: dict[str, float]
    ) -> bool:
        """Check if a scaling rule should be triggered."""
        condition = rule["condition"]

        if "request_rate" in condition:
            return load["request_rate"] > float(condition.split()[-1])
        elif "task_complexity" in condition:
            return load["task_complexity"] > float(condition.split()[-1])
        elif "response_time" in condition:
            return load["response_time"] > float(condition.split()[-1])

        return False

    async def _apply_scaling_rule(self, rule: dict[str, Any]) -> None:
        """Apply scaling rule by creating new agents."""
        current_count = self._scaling_state["metrics"]["current_count"]
        max_instances = rule["max_instances"]

        # Calculate how many to create
        needed = max(
            1, min(max_instances - current_count, 3)
        )  # Create up to 3 new agents

        if needed > 0:
            logger.info(f"Scaling up by {needed} agents for {rule['trigger']}")

            for _ in range(needed):
                await self._create_composed_agent(rule)

            self._scaling_state["metrics"]["current_count"] += needed
            self._scaling_state["metrics"]["peak_count"] = max(
                self._scaling_state["metrics"]["peak_count"],
                self._scaling_state["metrics"]["current_count"],
            )

    async def _create_composed_agent(self, rule: dict[str, Any]) -> ComposableAgent:
        """Create a new agent with specified composition."""
        # Create base agent
        agent = ComposableAgent(model_name="phi4")

        # Add behaviors from composition rule
        for behavior_class in rule["composition"]:
            # This would dynamically instantiate behavior classes
            # For now, use a placeholder
            if behavior_class == "SecurityBehavior":
                from cohezion.core import SecurityBehavior

                agent.add_behavior(SecurityBehavior())
            elif behavior_class == "CachingBehavior":
                from cohezion.core import CachingBehavior

                agent.add_behavior(CachingBehavior())
            elif behavior_class == "LoadBalancingBehavior":
                from cohezion.core import LoadBalancingBehavior

                agent.add_behavior(LoadBalancingBehavior())
            elif behavior_class == "MonitoringBehavior":
                from cohezion.core import MonitoringBehavior

                agent.add_behavior(MonitoringBehavior())
            elif behavior_class == "DeepAnalysisBehavior":
                from cohezion.core import DeepAnalysisBehavior

                agent.add_behavior(DeepAnalysisBehavior())
            elif behavior_class == "QualityAssuranceBehavior":
                from cohezion.core import QualityAssuranceBehavior

                agent.add_behavior(QualityAssuranceBehavior())

        # Initialize agent
        await agent.initialize()

        # Store in active agents
        self._scaling_state["active_agents"].add(agent)
        self._scaling_state["metrics"]["created"] += 1

        logger.info(f"Created composed agent with {len(rule['composition'])} behaviors")
        return agent

    async def on_process(self, agent: ComposableAgent, **kwargs) -> dict[str, Any]:
        """Process with dynamic scaling considerations."""
        # Check if we need to scale based on current request
        if "prompt" in kwargs:
            prompt = kwargs["prompt"]
            task_complexity = self._estimate_task_complexity(prompt)

            if task_complexity > 0.7:
                # Trigger complex task scaling
                rule = next(
                    (
                        r
                        for r in self._composition_rules
                        if r["trigger"] == "complex_tasks"
                    ),
                    None,
                )
                if rule:
                    asyncio.create_task(self._apply_scaling_rule(rule))

        return {}

    def _estimate_task_complexity(self, prompt: str) -> float:
        """Estimate task complexity from prompt."""
        prompt_lower = prompt.lower()

        # Simple complexity scoring based on keywords and length
        complexity = 0.3  # Base complexity

        # Add complexity for technical terms
        technical_terms = [
            "quantum",
            "neural",
            "optimization",
            "blockchain",
            "cryptography",
            "simulation",
            "physics",
            "biology",
        ]
        complexity += sum(1 for term in technical_terms if term in prompt_lower) * 0.1

        # Add complexity for longer prompts
        if len(prompt) > 200:
            complexity += 0.2
        elif len(prompt) > 100:
            complexity += 0.1

        # Cap complexity at 1.0
        return min(1.0, complexity)

    async def on_cleanup(self, agent: ComposableAgent) -> None:
        """Cleanup dynamic scaling resources."""
        # Stop scaling monitor
        # Clean up active agents
        for active_agent in list(self._scaling_state["active_agents"]):
            await active_agent.cleanup()
            self._scaling_state["active_agents"].remove(active_agent)
            self._scaling_state["metrics"]["destroyed"] += 1


@dataclass
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

    model_name: str
    _behaviors: list[AgentBehavior] = field(default_factory=list)
    _config: dict[str, Any] = field(default_factory=dict)
    _state: dict[str, Any] = field(default_factory=dict)
    _initialized: bool = False

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
                logger.error(f"Behavior initialization failed: {e}")

        self._initialized = True

    async def process(self, **kwargs) -> dict[str, Any]:
        """Process request through all behaviors."""
        if not self._initialized:
            await self.initialize()

        result = {}
        for behavior in self._behaviors:
            try:
                behavior_result = await behavior.on_process(self, **kwargs)
                result.update(behavior_result)
            except Exception as e:
                logger.error(f"Behavior processing failed: {e}")

        return result

    async def cleanup(self) -> None:
        """Cleanup all behaviors."""
        for behavior in self._behaviors:
            try:
                await behavior.on_cleanup(self)
            except Exception as e:
                logger.error(f"Behavior cleanup failed: {e}")

        self._initialized = False


class AgentBuilder:
    """Enhanced agent builder with dynamic scaling support."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._behaviors: list[AgentBehavior] = []
        self._scaling_config: dict[str, Any] | None = None

    def with_behavior(self, behavior: AgentBehavior) -> Self:
        """Add a behavior mixin."""
        self._behaviors.append(behavior)
        return self

    def with_scaling(self, config: dict[str, Any]) -> Self:
        """Add dynamic scaling behavior."""
        self._scaling_config = config
        return self

    def build(self) -> ComposableAgent:
        """Build the composed agent."""
        agent = ComposableAgent(self.model_name)

        # Add standard behaviors
        for behavior in self._behaviors:
            agent.add_behavior(behavior)

        # Add dynamic scaling behavior if configured
        if self._scaling_config:
            scaling_behavior = DynamicScalingBehavior(self._scaling_config)
            agent.add_behavior(scaling_behavior)

        return agent
