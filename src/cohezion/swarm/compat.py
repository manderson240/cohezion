"""Compatibility layer for legacy Swarm module API.

Bridges old Swarm API to new simplified implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from cohezion.swarm.orchestrator import (
    Agent as NewAgent,
)

# Import new simplified implementation
from cohezion.swarm.orchestrator import (
    Swarm as NewSwarm,
)
from cohezion.swarm.orchestrator import (
    SwarmConfig as NewSwarmConfig,
)
from cohezion.swarm.orchestrator import (
    Task as NewTask,
)

if TYPE_CHECKING:
    from collections.abc import Callable


# ============================================================================
# Legacy SwarmOrchestrator (wraps new Swarm)
# ============================================================================


class SwarmOrchestrator:
    """Legacy SwarmOrchestrator - wraps new Swarm.

    Maintains old interface while using clean internals.
    """

    def __init__(
        self,
        max_concurrent: int = 4,
        enable_load_balancing: bool = True,
        **kwargs,
    ):
        """Initialize with legacy parameters."""
        config = NewSwarmConfig(
            max_concurrent=max_concurrent,
            enable_load_balancing=enable_load_balancing,
        )
        self._swarm = NewSwarm(config)

        # Store legacy attributes
        self.max_concurrent = max_concurrent
        self.enable_load_balancing = enable_load_balancing

    def register_agent(
        self,
        agent_id: str,
        name: str,
        capabilities: list[str],
        execute_fn: Callable,
    ) -> None:
        """Register agent with legacy interface."""
        agent = NewAgent(
            id=agent_id,
            name=name,
            execute_fn=execute_fn,
            capabilities=capabilities,
        )
        self._swarm.register_agent(agent)

    async def execute_task(
        self,
        task_id: str,
        description: str,
        required_capabilities: list[str],
        **kwargs,
    ) -> LegacyAgentResult:
        """Execute task with legacy interface."""
        task = NewTask(
            id=task_id,
            description=description,
            required_capabilities=required_capabilities,
        )

        result = await self._swarm.execute(task)
        return LegacyAgentResult(
            agent_id=result.agent_id,
            success=result.success,
            output=result.output,
            error=result.error,
        )

    async def execute_parallel(
        self,
        tasks: list[dict[str, Any]],
    ) -> list[LegacyAgentResult]:
        """Execute tasks in parallel."""
        new_tasks = [
            NewTask(
                id=t["task_id"],
                description=t["description"],
                required_capabilities=t.get("required_capabilities", []),
            )
            for t in tasks
        ]

        results = await self._swarm.execute_parallel(new_tasks)
        return [
            LegacyAgentResult(
                agent_id=r.agent_id,
                success=r.success,
                output=r.output,
                error=r.error,
            )
            for r in results
        ]

    def get_agent_stats(self) -> dict[str, Any]:
        """Get agent statistics."""
        return self._swarm.get_agent_stats()


# ============================================================================
# Legacy Data Classes
# ============================================================================


@dataclass
class LegacyAgentResult:
    """Legacy agent result."""

    agent_id: str
    success: bool
    output: Any = None
    error: str | None = None


@dataclass
class AgentCapability:
    """Legacy agent capability."""

    name: str
    confidence: float = 1.0


# ============================================================================
# Legacy Type Aliases
# ============================================================================

# For imports that expect these names
Swarm = SwarmOrchestrator
Agent = NewAgent
Task = NewTask
AgentResult = LegacyAgentResult


__all__ = [
    "Agent",
    "AgentCapability",
    "AgentResult",
    "LegacyAgentResult",
    "Swarm",
    "SwarmOrchestrator",
    "Task",
]
