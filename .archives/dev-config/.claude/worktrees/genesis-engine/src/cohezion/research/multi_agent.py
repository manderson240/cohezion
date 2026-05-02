"""Multi-agent research orchestration.

Uses Cohezion's Swarm for coordinated multi-agent research.
Elegant integration with existing infrastructure.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from cohezion.compound.models import Task
from cohezion.research.agent import ResearchAgent, ResearchConfig
from cohezion.swarm.orchestrator import Agent as SwarmAgent
from cohezion.swarm.orchestrator import Swarm
from cohezion.swarm.orchestrator import Task as SwarmTask


logger = logging.getLogger(__name__)


@dataclass
class MultiAgentResearchConfig:
    """Configuration for multi-agent research."""

    num_agents: int = 3
    experiments_per_agent: int = 33  # ~100 total
    agent_diversity: str = "high"  # high = different strategies


@dataclass
class MultiAgentResult:
    """Result from multi-agent research."""

    experiments_completed: int = 0
    best_metric: float = float("inf")
    agent_results: dict[str, Any] = field(default_factory=dict)
    collaboration_insights: list[str] = field(default_factory=list)


class ResearchSwarm:
    """Multi-agent research using Cohezion's Swarm.

    Coordinates multiple ResearchAgents for parallel experimentation.
    Leverages existing Swarm infrastructure.
    """

    def __init__(
        self,
        config: MultiAgentResearchConfig,
        swarm: Swarm | None = None,
    ):
        """Initialize research swarm.

        Args:
            config: Multi-agent configuration
            swarm: Optional existing Swarm instance
        """
        self.config = config
        self.results = MultiAgentResult()

        # Create swarm if not provided
        if swarm is None:
            swarm = Swarm()
        self.swarm = swarm

        # Register research agents
        self._register_agents()

    def _register_agents(self) -> None:
        """Register research agents with different strategies."""
        strategies = [
            ("architect", "Optimize model architecture"),
            ("optimizer", "Tune optimizer hyperparameters"),
            ("data", "Improve data pipeline"),
        ]

        for i in range(self.config.num_agents):
            strategy_name, strategy_desc = strategies[i % len(strategies)]

            agent_id = f"research-{strategy_name}-{i + 1}"

            # Create agent
            agent = SwarmAgent(
                id=agent_id,
                name=f"Research Agent {i + 1}",
                execute_fn=self._create_agent_executor(agent_id),
                capabilities=["research", "optimization", strategy_name],
            )

            self.swarm.register_agent(agent)
            logger.info(f"Registered agent: {agent_id}")

    def _create_agent_executor(self, agent_id: str):
        """Create executor function for an agent."""

        def executor(task, context):
            # Create research agent for this task
            research_config = ResearchConfig(
                max_experiments=self.config.experiments_per_agent,
            )

            research_agent = ResearchAgent(config=research_config)

            # Run research session
            session = research_agent.run_session()

            # Get best result
            best = research_agent.get_best_result()

            return {
                "agent_id": agent_id,
                "experiments": session.experiments_completed,
                "best_metric": best["metric"] if best else float("inf"),
            }

        return executor

    async def run_multi_agent_research(self) -> MultiAgentResult:
        """Run coordinated multi-agent research.

        Returns:
            MultiAgentResult with combined results
        """
        logger.info(f"Starting multi-agent research with {self.config.num_agents} agents")

        # Create tasks for each agent
        tasks = [
            SwarmTask(
                id=f"research-task-{i + 1}",
                description=f"Agent {i + 1} research session",
                required_capabilities=["research"],
            )
            for i in range(self.config.num_agents)
        ]

        # Execute in parallel
        results = await self.swarm.execute_parallel(tasks)

        # Process results
        self._process_results(results)

        return self.results

    def _process_results(
        self,
        results: list[Any],
    ) -> None:
        """Process results from all agents."""
        best_overall = float("inf")

        for result in results:
            if result.success:
                data = result.output
                agent_id = data.get("agent_id", "unknown")
                experiments = data.get("experiments", 0)
                metric = data.get("best_metric", float("inf"))

                self.results.agent_results[agent_id] = {
                    "experiments": experiments,
                    "best_metric": metric,
                }

                self.results.experiments_completed += experiments

                if metric < best_overall:
                    best_overall = metric

        self.results.best_metric = best_overall

        # Generate collaboration insights
        self._generate_insights()

    def _generate_insights(self) -> None:
        """Generate insights from multi-agent collaboration."""
        insights = []

        # Compare agent performance
        metrics = [r["best_metric"] for r in self.results.agent_results.values()]

        if metrics:
            best_agent = min(
                self.results.agent_results.items(),
                key=lambda x: x[1]["best_metric"],
            )

            insights.append(f"Best performing strategy: {best_agent[0]} (metric: {best_agent[1]['best_metric']:.4f})")

        # Check diversity
        if len(self.results.agent_results) > 1:
            insights.append(
                f"Multi-agent diversity enabled exploration of {len(self.results.agent_results)} different strategies"
            )

        self.results.collaboration_insights = insights

    def get_collaboration_report(self) -> dict[str, Any]:
        """Get detailed collaboration report."""
        return {
            "total_experiments": self.results.experiments_completed,
            "best_metric": self.results.best_metric,
            "num_agents": self.config.num_agents,
            "agent_breakdown": self.results.agent_results,
            "insights": self.results.collaboration_insights,
        }


class SimpleMultiAgent:
    """Minimal multi-agent for basic use cases."""

    def __init__(self, num_agents: int = 2):
        self.num_agents = num_agents
        self.agents = []

    def add_agent(
        self,
        agent_id: str,
        execute_fn,
    ) -> None:
        """Add an agent."""
        self.agents.append(
            {
                "id": agent_id,
                "execute": execute_fn,
            }
        )

    async def run(self, tasks: list[Task]) -> list[Any]:
        """Run tasks across agents."""
        results = []

        for i, task in enumerate(tasks):
            agent = self.agents[i % len(self.agents)]
            result = await agent["execute"](task)
            results.append(result)

        return results
