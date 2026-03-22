"""Cohezion environments for AgentVerse simulation and task-solving.

Provides AgentVerse-compatible environments that leverage Cohezion's
vault/knowledge system for context-aware multi-agent coordination.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.core.mcp_client import MCPClient

logger = logging.getLogger(__name__)


class CohezionEnvironment:
    """Base environment for Cohezion-AgentVerse integration.

    Provides a foundation for wrapping Cohezion's knowledge/vault
    system as an AgentVerse-compatible environment.

    Parameters
    ----------
    mcp_client : MCPClient
        Connected MCP client for vault queries
    executor : Any
        CompoundExecutor instance for task execution

    Attributes
    ----------
    agents : list[Any]
        List of agents in this environment
    """

    def __init__(
        self,
        mcp_client: MCPClient,
        executor: Any,
    ) -> None:
        """Initialize base environment."""
        self.mcp_client = mcp_client
        self.executor = executor
        self.agents: list[Any] = []

    def reset(self) -> None:
        """Reset environment state (AgentVerse protocol)."""
        self.agents = []

    def step(self) -> None:
        """Execute one step in the environment (override in subclasses)."""
        raise NotImplementedError("Subclasses must implement step()")

    def get_context(self) -> dict[str, Any]:
        """Query vault for context data.

        Returns
        -------
        dict[str, Any]
            Context data from vault queries
        """
        return {"status": "context_available"}


class CohezionSimulationEnvironment(CohezionEnvironment):
    """Simulation environment for observing Cohezion agent behaviors.

    This environment allows observation of multi-agent interactions
    with Cohezion's coherence tracking and vault logging.

    Parameters
    ----------
    mcp_client : MCPClient
        Connected MCP client for vault operations
    executor : Any
        CompoundExecutor instance
    """

    def __init__(
        self,
        mcp_client: MCPClient,
        executor: Any,
    ) -> None:
        """Initialize simulation environment."""
        super().__init__(mcp_client=mcp_client, executor=executor)
        self.n_round: int = 0

    def reset(self) -> None:
        """Reset simulation state."""
        super().reset()
        self.n_round = 0

    def add_agent(self, agent: Any) -> None:
        """Add an agent to the simulation.

        Parameters
        ----------
        agent : Any
            Agent to add (must have .name attribute)
        """
        self.agents.append(agent)
        logger.info("Added agent %s to simulation", getattr(agent, "name", "unknown"))

    def get_observation(self) -> dict[str, Any]:
        """Get current observation of environment state.

        Returns
        -------
        dict[str, Any]
            Current observation
        """
        return {
            "n_agents": len(self.agents),
            "n_round": self.n_round,
            "agents": [getattr(a, "name", str(a)) for a in self.agents],
        }


class CohezionTaskSolvingEnvironment(CohezionEnvironment):
    """Task-solving environment for Cohezion multi-agent coordination.

    Supports the AgentVerse task-solving framework where multiple
    agents collaborate to solve problems.

    Parameters
    ----------
    mcp_client : MCPClient
        Connected MCP client for vault operations
    executor : Any
        CompoundExecutor instance
    task_description : str
        Description of the task for agents to solve
    """

    def __init__(
        self,
        mcp_client: MCPClient,
        executor: Any,
        task_description: str,
    ) -> None:
        """Initialize task-solving environment."""
        super().__init__(mcp_client=mcp_client, executor=executor)
        self.task_description = task_description
        self.n_round: int = 0

    def reset(self) -> None:
        """Reset task-solving state."""
        super().reset()
        self.n_round = 0

    def is_multi_agent(self) -> bool:
        """Check if this is a multi-agent environment.

        Returns
        -------
        bool
            Always True for task-solving environments
        """
        return True

    def get_task(self) -> str:
        """Get the task description.

        Returns
        -------
        str
            Task description
        """
        return self.task_description
