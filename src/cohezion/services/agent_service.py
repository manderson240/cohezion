"""Agent Service - Agent orchestration and lifecycle management."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cohezion.core.persistence.repositories.journey_repository import (
    AgentJourney,
    JourneyMetrics,
    JourneyStep,
)
from cohezion.core.persistence.repositories.universe_repository import PhysicsState


logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for agent instances."""

    name: str
    agent_type: str
    model_name: str
    capabilities: list[str] = field(default_factory=list)
    priority: int = 3
    max_concurrency: int = 1


@dataclass
class AgentStatus:
    """Status information for an agent."""

    agent_name: str
    is_active: bool
    current_tasks: int
    total_processed: int
    avg_duration_ms: float
    last_active: str
    error_count: int


class AgentService:
    """Service for agent orchestration and lifecycle management."""

    def __init__(
        self,
        journey_repo: Any,
        universe_repo: Any,
    ):
        """
        Initialize AgentService.

        Args:
            journey_repo: Journey repository instance.
            universe_repo: Universe repository instance.
        """
        self._journey_repo = journey_repo
        self._universe_repo = universe_repo
        self._active_agents: dict[str, AgentConfig] = {}
        self._agent_status: dict[str, AgentStatus] = {}

    async def register_agent(self, config: AgentConfig) -> bool:
        """Register a new agent configuration.

        Args:
            config: Agent configuration.

        Returns:
            True if successful, False otherwise.
        """
        try:
            if config.name in self._active_agents:
                logger.warning(f"Agent {config.name} already registered")
                return False

            self._active_agents[config.name] = config
            self._agent_status[config.name] = AgentStatus(
                agent_name=config.name,
                is_active=True,
                current_tasks=0,
                total_processed=0,
                avg_duration_ms=0.0,
                last_active=datetime.now().isoformat(),
                error_count=0,
            )

            logger.info(f"Registered agent: {config.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            return False

    async def unregister_agent(self, agent_name: str) -> bool:
        """Unregister an agent.

        Args:
            agent_name: Name of agent to unregister.

        Returns:
            True if successful, False otherwise.
        """
        try:
            if agent_name in self._active_agents:
                self._active_agents.pop(agent_name)
                self._agent_status.pop(agent_name)
                logger.info(f"Unregistered agent: {agent_name}")
                return True

            logger.warning(f"Agent {agent_name} not found")
            return False

        except Exception as e:
            logger.error(f"Failed to unregister agent: {e}")
            return False

    async def get_agent_status(self, agent_name: str) -> AgentStatus | None:
        """Get status information for an agent.

        Args:
            agent_name: Name of agent.

        Returns:
            Agent status if found, None otherwise.
        """
        return self._agent_status.get(agent_name)

    async def get_all_agent_status(self) -> dict[str, AgentStatus]:
        """Get status for all registered agents.

        Returns:
            Dictionary mapping agent names to status.
        """
        return self._agent_status.copy()

    async def execute_task(
        self,
        agent_name: str,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> AgentJourney:
        """Execute a task with a specific agent.

        Args:
            agent_name: Name of agent to execute.
            query: Query string to process.
            context: Optional context dictionary.

        Returns:
            AgentJourney tracking the execution.
        """
        journey_id = f"journey_{agent_name}_{int(datetime.now().timestamp())}"
        journey = AgentJourney(
            journey_id=journey_id,
            query=query,
            started_at=datetime.now().isoformat(),
        )

        start_time = datetime.now()

        try:
            config = self._active_agents.get(agent_name)
            if not config:
                raise ValueError(f"Agent {agent_name} not registered")

            await self._update_agent_status(agent_name, current_tasks=1)

            step = await self._create_step(
                agent_name=agent_name,
                agent_type=config.agent_type,
                query=query,
                context=context,
            )

            journey.add_step(step)

            await self._journey_repo.create(journey)

            await self._update_agent_status(
                agent_name,
                total_processed=1,
                current_tasks=-1,
            )

            return journey

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            await self._update_agent_status(
                agent_name,
                current_tasks=-1,
                error_count=1,
            )

            error_step = JourneyStep(
                timestamp=datetime.now().isoformat(),
                agent_type="error",
                agent_name=agent_name,
                perspective=None,
                input_summary=query,
                output_summary=str(e),
                physics_state={},
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
                confidence=0.0,
            )
            journey.add_step(error_step)

            return journey

    async def _create_step(
        self,
        agent_name: str,
        agent_type: str,
        query: str,
        context: dict[str, Any] | None,
    ) -> JourneyStep:
        """Create a journey step from agent execution.

        Args:
            agent_name: Name of the agent.
            agent_type: Type of the agent.
            query: Input query.
            context: Optional context.

        Returns:
            JourneyStep representing the execution.
        """
        start = datetime.now()

        physics_state = PhysicsState(
            x=0.5,
            y=0.5,
            z=0.5,
            time=1.0,
            mass=0.8,
            sentiment=0.2,
            complexity=0.6,
            factuality=0.9,
            connectivity=0.7,
            stability=0.8,
            novelty=0.5,
            coherence=0.9,
        )

        physics_dict = physics_state.to_dict()

        return JourneyStep(
            timestamp=start.isoformat(),
            agent_type=agent_type,
            agent_name=agent_name,
            perspective=None,
            input_summary=query[:200],
            output_summary=f"Processed by {agent_name}",
            physics_state=physics_dict,
            duration_ms=0.0,
            confidence=0.8,
            metrics=JourneyMetrics(
                context_utilization=0.7,
                latent_coherence=0.85,
                capability_delta=0.05,
                latency_per_token_ms=10.0,
                safety_alignment_score=0.95,
                computational_relativity_factor=1.0,
            ),
        )

    async def _update_agent_status(
        self,
        agent_name: str,
        current_tasks: int = 0,
        total_processed: int = 0,
        error_count: int = 0,
    ) -> None:
        """Update agent status metrics.

        Args:
            agent_name: Name of agent.
            current_tasks: Delta for current tasks.
            total_processed: Delta for total processed.
            error_count: Delta for error count.
        """
        if agent_name not in self._agent_status:
            return

        status = self._agent_status[agent_name]
        status.current_tasks = max(0, status.current_tasks + current_tasks)
        status.total_processed += total_processed
        status.error_count += error_count
        status.last_active = datetime.now().isoformat()

    async def get_agent_config(self, agent_name: str) -> AgentConfig | None:
        """Get configuration for an agent.

        Args:
            agent_name: Name of agent.

        Returns:
            Agent configuration if found, None otherwise.
        """
        return self._active_agents.get(agent_name)

    async def list_agents(self) -> list[str]:
        """List all registered agent names.

        Returns:
            List of agent names.
        """
        return list(self._active_agents.keys())
