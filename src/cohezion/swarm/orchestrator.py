"""Elegant simplified Swarm orchestration.

Replaces 12,590 lines of complex orchestration with clean, focused implementation.
Key principle: Simple agent coordination without over-engineering.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Callable


logger = logging.getLogger(__name__)


@dataclass
class Agent:
    """Simple agent definition."""

    id: str
    name: str
    execute_fn: Callable[..., Any]
    capabilities: list[str] = field(default_factory=list)

    async def execute(self, task: Task) -> AgentResult:
        """Execute task."""
        try:
            result = await asyncio.to_thread(self.execute_fn, task)
            return AgentResult(
                agent_id=self.id,
                success=True,
                output=result,
            )
        except Exception as e:
            return AgentResult(
                agent_id=self.id,
                success=False,
                error=str(e),
            )


@dataclass
class Task:
    """Simple task definition."""

    id: str
    description: str
    required_capabilities: list[str] = field(default_factory=list)
    priority: int = 5
    timeout_seconds: float = 60.0


@dataclass
class AgentResult:
    """Agent execution result."""

    agent_id: str
    success: bool
    output: Any = None
    error: str | None = None


@dataclass
class SwarmConfig:
    """Swarm configuration."""

    max_concurrent: int = 4
    timeout_seconds: float = 300.0
    enable_load_balancing: bool = True


class Swarm:
    """Elegant swarm orchestration.

    Clean implementation vs 12,590-line monster.
    Single responsibility: coordinate agents to complete tasks.
    """

    def __init__(self, config: SwarmConfig | None = None):
        self.config = config or SwarmConfig()
        self.agents: dict[str, Agent] = {}
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)

    def register_agent(self, agent: Agent) -> None:
        """Register an agent."""
        self.agents[agent.id] = agent
        logger.info(f"Registered agent: {agent.id}")

    def find_agent(self, task: Task) -> Agent | None:
        """Find best agent for task."""
        candidates = []
        for agent in self.agents.values():
            score = self._score_agent(agent, task)
            if score > 0:
                candidates.append((agent, score))

        if not candidates:
            return None

        # Sort by score, return best
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _score_agent(self, agent: Agent, task: Task) -> float:
        """Score agent suitability for task."""
        if not task.required_capabilities:
            return 0.5  # No requirements = neutral score

        matches = sum(1 for cap in task.required_capabilities if cap in agent.capabilities)
        return matches / len(task.required_capabilities)

    async def execute(self, task: Task) -> AgentResult:
        """Execute task with swarm."""
        agent = self.find_agent(task)

        if not agent:
            return AgentResult(
                agent_id="swarm",
                success=False,
                error="No suitable agent found",
            )

        async with self._semaphore:
            try:
                return await asyncio.wait_for(
                    agent.execute(task),
                    timeout=task.timeout_seconds,
                )
            except TimeoutError:
                return AgentResult(
                    agent_id=agent.id,
                    success=False,
                    error=f"Task timed out after {task.timeout_seconds}s",
                )

    async def execute_parallel(
        self,
        tasks: list[Task],
    ) -> list[AgentResult]:
        """Execute multiple tasks in parallel."""
        coros = [self.execute(task) for task in tasks]
        return await asyncio.gather(*coros, return_exceptions=True)

    def get_agent_stats(self) -> dict[str, int]:
        """Get agent statistics."""
        return {
            "total_agents": len(self.agents),
            "agents_by_capability": self._count_by_capability(),
        }

    def _count_by_capability(self) -> dict[str, int]:
        """Count agents by capability."""
        counts: dict[str, int] = {}
        for agent in self.agents.values():
            for cap in agent.capabilities:
                counts[cap] = counts.get(cap, 0) + 1
        return counts


class SimpleSwarm:
    """Minimal swarm for basic use cases."""

    def __init__(self):
        self.agents: dict[str, Agent] = {}

    def add_agent(self, agent: Agent) -> None:
        self.agents[agent.id] = agent

    async def run(self, task: Task) -> AgentResult:
        """Run task with first available agent."""
        if not self.agents:
            return AgentResult(
                agent_id="none",
                success=False,
                error="No agents available",
            )

        agent = next(iter(self.agents.values()))
        return await agent.execute(task)
