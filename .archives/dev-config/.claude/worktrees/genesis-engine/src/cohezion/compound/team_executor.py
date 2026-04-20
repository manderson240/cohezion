"""Multi-agent team execution with vault-guided coordination.

Orchestrates execution of teams of agents with task dependencies,
shared vault knowledge, and intelligent skill selection.
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from cohezion.compound.executor import CompoundExecutor, ExecutionResult
from cohezion.compound.skill_selector import SkillSelector
from cohezion.core.mcp_client import MCPClient


logger = logging.getLogger(__name__)


@dataclass
class AgentTask:
    """Task to be executed by an agent."""

    task_id: str  # Unique identifier
    agent_id: str  # Which agent executes this
    description: str  # What the task does
    operation_type: str  # generate, analyze, search, transform, persist
    dependencies: list[str] = field(default_factory=list)  # Task IDs it depends on
    available_skills: list[str] = field(
        default_factory=list
    )  # Skills this task can use
    execute_fn: Callable | None = None  # Optional execution function
    timeout_seconds: float = 300.0  # Execution timeout


@dataclass
class AgentTaskResult:
    """Result of executing an agent task."""

    task_id: str
    agent_id: str
    success: bool
    output: str
    metrics: dict[str, Any]
    selected_skill: str
    execution_result: ExecutionResult | None = None
    error: str = ""


@dataclass
class TeamExecutionResult:
    """Result of team execution."""

    success: bool
    tasks_executed: int
    tasks_failed: int
    results: list[AgentTaskResult] = field(default_factory=list)
    compound_score: float = 0.0  # Overall team performance
    execution_time_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


class TeamExecutor:
    """Coordinate multi-agent execution with vault knowledge sharing.

    Orchestrates a team of agents to execute interdependent tasks
    using vault-guided skill selection and intelligent coordination.

    Example:
        ```python
        team_executor = TeamExecutor(
            agents={"agent1": executor1, "agent2": executor2},
            mcp_client=mcp_client
        )

        tasks = [
            AgentTask(
                task_id="task1",
                agent_id="agent1",
                description="Generate ideas",
                operation_type="generate",
                available_skills=["generator", "brainstormer"]
            ),
            AgentTask(
                task_id="task2",
                agent_id="agent2",
                description="Analyze ideas",
                operation_type="analyze",
                dependencies=["task1"],
                available_skills=["analyzer", "evaluator"]
            )
        ]

        result = asyncio.run(team_executor.execute_team(tasks))
        ```
    """

    def __init__(
        self,
        agents: dict[str, CompoundExecutor],
        mcp_client: MCPClient,
        project: str = "cohezion",
    ):
        """Initialize team executor.

        Args:
            agents: Dictionary of agent_id -> CompoundExecutor
            mcp_client: Connected MCP client for vault access
            project: Project name for vault scoping
        """
        self.agents = agents
        self.mcp_client = mcp_client
        self.project = project
        self.skill_selector = SkillSelector(mcp_client)
        logger.debug("Initialized TeamExecutor with %d agents", len(agents))

    def _topological_sort(self, tasks: list[AgentTask]) -> list[AgentTask]:
        """Sort tasks by dependencies (topological sort).

        Args:
            tasks: List of tasks to sort

        Returns:
            Tasks sorted by dependencies (dependencies first)
        """
        task_by_id = {t.task_id: t for t in tasks}
        visited = set()
        sorted_tasks = []

        def visit(task_id: str) -> None:
            if task_id in visited:
                return

            task = task_by_id.get(task_id)
            if not task:
                return

            visited.add(task_id)

            # Visit dependencies first
            for dep_id in task.dependencies:
                visit(dep_id)

            sorted_tasks.append(task)

        # Visit all tasks
        for task in tasks:
            visit(task.task_id)

        logger.debug("Sorted %d tasks by dependencies", len(sorted_tasks))
        return sorted_tasks

    def _build_dependency_graph(self, tasks: list[AgentTask]) -> dict[str, list[str]]:
        """Build dependency graph for parallel execution.

        Returns:
            Dictionary of task_id -> list of task_ids that depend on it
        """
        graph = {t.task_id: [] for t in tasks}

        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id in graph:
                    graph[dep_id].append(task.task_id)

        return graph

    async def _select_skill_for_task(self, task: AgentTask) -> str:
        """Select best skill for task using vault patterns.

        Args:
            task: Task to select skill for

        Returns:
            Selected skill name
        """
        if not task.available_skills:
            logger.warning(
                "Task %s has no available skills, using 'default'",
                task.task_id,
            )
            return "default"

        # Get skill suggestions from vault
        suggestions = self.skill_selector.select_skills(
            task_description=task.description,
            operation_type=task.operation_type,
            project=self.project,
            top_k=len(task.available_skills),
        )

        # Find first suggested skill that's available
        for skill_score in suggestions:
            if skill_score.skill_name in task.available_skills:
                logger.info(
                    "Selected skill %s for task %s (score=%.3f)",
                    skill_score.skill_name,
                    task.task_id,
                    skill_score.composite_score,
                )
                return skill_score.skill_name

        # Fallback: use first available skill
        selected = task.available_skills[0]
        logger.info(
            "No suggested skills available, using first: %s",
            selected,
        )
        return selected

    async def _execute_task(
        self,
        task: AgentTask,
        agent: CompoundExecutor,
        parent_results: dict[str, AgentTaskResult],
    ) -> AgentTaskResult:
        """Execute a single task with an agent.

        Args:
            task: Task to execute
            agent: Agent (CompoundExecutor) to execute with
            parent_results: Results from dependent tasks

        Returns:
            AgentTaskResult with execution outcome
        """
        try:
            logger.info(
                "Executing task %s on agent %s",
                task.task_id,
                task.agent_id,
            )

            # Select best skill for this task
            selected_skill = await self._select_skill_for_task(task)

            # Prepare execution function or use provided one
            if task.execute_fn:
                execute_fn = task.execute_fn
            else:

                def execute_fn(guidance):
                    # Default execution: pass parent results as context
                    parent_outputs = {parent_id: result.output for parent_id, result in parent_results.items()}
                    return f"Executed {task.task_id}", {"parent_context": parent_outputs}

            # Execute task
            execution_result = agent.execute_task(
                task_description=task.description,
                skill_name=selected_skill,
                operation_type=task.operation_type,
                execute_fn=execute_fn,
                project=self.project,
            )

            result = AgentTaskResult(
                task_id=task.task_id,
                agent_id=task.agent_id,
                success=execution_result.success,
                output=execution_result.output,
                metrics=execution_result.metrics,
                selected_skill=selected_skill,
                execution_result=execution_result,
            )

            logger.info(
                "Task %s completed (success=%s)",
                task.task_id,
                execution_result.success,
            )

            return result

        except Exception as e:
            logger.error(
                "Error executing task %s: %s",
                task.task_id,
                e,
                exc_info=True,
            )

            return AgentTaskResult(
                task_id=task.task_id,
                agent_id=task.agent_id,
                success=False,
                output="",
                metrics={"error": str(e)},
                selected_skill="",
                error=str(e),
            )

    def _compute_compound_score(self, results: list[AgentTaskResult]) -> float:
        """Compute overall team performance score.

        Combines:
        - Success rate (60% weight)
        - Average coherence (25% weight)
        - Average efficiency (15% weight)

        Args:
            results: List of task results

        Returns:
            Compound score (0.0-1.0)
        """
        if not results:
            return 0.0

        # Success rate
        successful = sum(1 for r in results if r.success)
        success_rate = successful / len(results)

        # Average coherence
        coherence_scores = [
            r.metrics.get("coherence", 0.5) for r in results if r.success
        ]
        avg_coherence = (
            sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0.0
        )

        # Average efficiency (token efficiency)
        efficiency_scores = []
        for r in results:
            if r.execution_result and r.execution_result.token_metrics:
                cache_hit_rate = r.execution_result.token_metrics.get("cache_hit_rate", 0.0)
                efficiency_scores.append(cache_hit_rate)

        avg_efficiency = sum(efficiency_scores) / len(efficiency_scores) if efficiency_scores else 0.5

        # Weighted combination
        compound = (
            (success_rate * 0.6) + (avg_coherence * 0.25) + (avg_efficiency * 0.15)
        )

        logger.info(
            "Compound score: %.3f (success=%.2f, coherence=%.2f, efficiency=%.2f)",
            compound,
            success_rate,
            avg_coherence,
            avg_efficiency,
        )

        return compound

    async def execute_team(
        self,
        tasks: list[AgentTask],
        parallel_degree: int = 4,
    ) -> TeamExecutionResult:
        """Execute team tasks with dependency management.

        Args:
            tasks: List of tasks to execute
            parallel_degree: Max tasks to execute in parallel

        Returns:
            TeamExecutionResult with outcomes and scoring
        """
        import time

        start_time = time.time()

        try:
            logger.info(
                "Starting team execution: %d tasks, parallelism=%d",
                len(tasks),
                parallel_degree,
            )

            # Sort tasks by dependencies
            sorted_tasks = self._topological_sort(tasks)

            # Execute tasks respecting dependencies
            task_results = {}
            execution_order = []

            for task in sorted_tasks:
                # Wait for dependencies to complete
                while not all(dep_id in task_results for dep_id in task.dependencies):
                    await asyncio.sleep(0.1)

                # Get agent
                agent = self.agents.get(task.agent_id)
                if not agent:
                    logger.error(
                        "Agent %s not found for task %s",
                        task.agent_id,
                        task.task_id,
                    )
                    task_results[task.task_id] = AgentTaskResult(
                        task_id=task.task_id,
                        agent_id=task.agent_id,
                        success=False,
                        output="",
                        metrics={"error": f"Agent {task.agent_id} not found"},
                        selected_skill="",
                        error=f"Agent {task.agent_id} not found",
                    )
                    continue

                # Execute task
                result = await self._execute_task(
                    task,
                    agent,
                    {dep_id: task_results[dep_id] for dep_id in task.dependencies if dep_id in task_results},
                )

                task_results[task.task_id] = result
                execution_order.append(task.task_id)

            # Collect results
            results_list = [task_results[task.task_id] for task in sorted_tasks]

            # Compute metrics
            successful = sum(1 for r in results_list if r.success)
            failed = len(results_list) - successful
            compound_score = self._compute_compound_score(results_list)
            execution_time = time.time() - start_time

            team_result = TeamExecutionResult(
                success=failed == 0,
                tasks_executed=len(results_list),
                tasks_failed=failed,
                results=results_list,
                compound_score=compound_score,
                execution_time_seconds=execution_time,
            )

            logger.info(
                "Team execution complete: %d/%d successful, score=%.3f, time=%.2fs",
                successful,
                len(results_list),
                compound_score,
                execution_time,
            )

            return team_result

        except Exception as e:
            logger.error(
                "Team execution failed: %s",
                e,
                exc_info=True,
            )

            execution_time = time.time() - start_time
            return TeamExecutionResult(
                success=False,
                tasks_executed=0,
                tasks_failed=len(tasks),
                compound_score=0.0,
                execution_time_seconds=execution_time,
                errors=[str(e)],
            )


class TeamExecutorFactory:
    """Factory for creating team executors."""

    @staticmethod
    def create(
        agents: dict[str, CompoundExecutor],
        mcp_client: MCPClient,
        project: str = "cohezion",
    ) -> TeamExecutor:
        """Create a team executor.

        Args:
            agents: Dictionary of agent_id -> CompoundExecutor
            mcp_client: MCP client for vault access
            project: Project name

        Returns:
            TeamExecutor instance
        """
        return TeamExecutor(agents, mcp_client, project)
