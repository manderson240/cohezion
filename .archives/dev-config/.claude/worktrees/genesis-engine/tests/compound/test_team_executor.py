"""Tests for multi-agent team execution with vault coordination."""

from unittest.mock import MagicMock

import pytest

from cohezion.compound.executor import CompoundExecutor, ExecutionResult
from cohezion.compound.team_executor import (
    AgentTask,
    AgentTaskResult,
    TeamExecutionResult,
    TeamExecutor,
    TeamExecutorFactory,
)


@pytest.fixture
def mock_mcp_client():
    """Create mock MCP client."""
    return MagicMock()


@pytest.fixture
def mock_executor():
    """Create mock CompoundExecutor."""
    executor = MagicMock(spec=CompoundExecutor)
    executor.execute_task = MagicMock(
        return_value=ExecutionResult(
            success=True,
            output="test output",
            metrics={"coherence": 0.85, "efficiency": 0.8},
            token_metrics={},
        )
    )
    return executor


@pytest.fixture
def team_executor(mock_mcp_client):
    """Create team executor with mock MCP client."""
    agents = {
        "agent1": MagicMock(spec=CompoundExecutor),
        "agent2": MagicMock(spec=CompoundExecutor),
    }
    return TeamExecutor(agents, mock_mcp_client)


class TestAgentTask:
    """Tests for AgentTask dataclass."""

    def test_agent_task_creation(self):
        """Test creating an AgentTask."""
        task = AgentTask(
            task_id="task1",
            agent_id="agent1",
            description="Generate ideas",
            operation_type="generate",
            dependencies=[],
            available_skills=["skill1", "skill2"],
        )

        assert task.task_id == "task1"
        assert task.agent_id == "agent1"
        assert task.description == "Generate ideas"
        assert task.operation_type == "generate"
        assert task.dependencies == []
        assert task.available_skills == ["skill1", "skill2"]
        assert task.timeout_seconds == 300.0

    def test_agent_task_with_dependencies(self):
        """Test AgentTask with dependencies."""
        task = AgentTask(
            task_id="task2",
            agent_id="agent2",
            description="Analyze ideas",
            operation_type="analyze",
            dependencies=["task1"],
        )

        assert task.dependencies == ["task1"]

    def test_agent_task_with_custom_timeout(self):
        """Test AgentTask with custom timeout."""
        task = AgentTask(
            task_id="task1",
            agent_id="agent1",
            description="Task",
            operation_type="generate",
            timeout_seconds=600.0,
        )

        assert task.timeout_seconds == 600.0


class TestAgentTaskResult:
    """Tests for AgentTaskResult dataclass."""

    def test_agent_task_result_success(self):
        """Test successful task result."""
        result = AgentTaskResult(
            task_id="task1",
            agent_id="agent1",
            success=True,
            output="generated content",
            metrics={"coherence": 0.85},
            selected_skill="generator",
        )

        assert result.success is True
        assert result.output == "generated content"
        assert result.metrics["coherence"] == 0.85
        assert result.selected_skill == "generator"

    def test_agent_task_result_failure(self):
        """Test failed task result."""
        result = AgentTaskResult(
            task_id="task1",
            agent_id="agent1",
            success=False,
            output="",
            metrics={},
            selected_skill="",
            error="Task execution failed",
        )

        assert result.success is False
        assert result.error == "Task execution failed"


class TestTeamExecutionResult:
    """Tests for TeamExecutionResult dataclass."""

    def test_team_execution_result_success(self):
        """Test successful team execution result."""
        result = TeamExecutionResult(
            success=True,
            tasks_executed=2,
            tasks_failed=0,
            results=[],
            compound_score=0.85,
            execution_time_seconds=10.5,
        )

        assert result.success is True
        assert result.tasks_executed == 2
        assert result.tasks_failed == 0
        assert result.compound_score == 0.85

    def test_team_execution_result_partial_failure(self):
        """Test team execution with partial failure."""
        result = TeamExecutionResult(
            success=False,
            tasks_executed=2,
            tasks_failed=1,
            results=[],
            compound_score=0.5,
            execution_time_seconds=15.0,
            errors=["task1 failed"],
        )

        assert result.success is False
        assert result.tasks_failed == 1
        assert len(result.errors) == 1


class TestTeamExecutorTopologicalSort:
    """Tests for topological sorting."""

    def test_topological_sort_no_dependencies(self, team_executor):
        """Test sorting tasks with no dependencies."""
        tasks = [
            AgentTask("task1", "agent1", "Task 1", "generate"),
            AgentTask("task2", "agent2", "Task 2", "analyze"),
        ]

        sorted_tasks = team_executor._topological_sort(tasks)

        assert len(sorted_tasks) == 2
        assert {t.task_id for t in sorted_tasks} == {"task1", "task2"}

    def test_topological_sort_with_dependencies(self, team_executor):
        """Test sorting tasks with dependencies."""
        tasks = [
            AgentTask("task2", "agent2", "Task 2", "analyze", dependencies=["task1"]),
            AgentTask("task1", "agent1", "Task 1", "generate"),
        ]

        sorted_tasks = team_executor._topological_sort(tasks)

        # task1 should come before task2
        task1_idx = next(i for i, t in enumerate(sorted_tasks) if t.task_id == "task1")
        task2_idx = next(i for i, t in enumerate(sorted_tasks) if t.task_id == "task2")
        assert task1_idx < task2_idx

    def test_topological_sort_chain(self, team_executor):
        """Test sorting a chain of dependent tasks."""
        tasks = [
            AgentTask("task3", "agent2", "Task 3", "transform", dependencies=["task2"]),
            AgentTask("task1", "agent1", "Task 1", "generate"),
            AgentTask("task2", "agent2", "Task 2", "analyze", dependencies=["task1"]),
        ]

        sorted_tasks = team_executor._topological_sort(tasks)

        # task1 < task2 < task3
        indices = {t.task_id: i for i, t in enumerate(sorted_tasks)}
        assert indices["task1"] < indices["task2"] < indices["task3"]

    def test_topological_sort_diamond(self, team_executor):
        """Test sorting a diamond dependency graph."""
        tasks = [
            AgentTask("task1", "agent1", "Task 1", "generate"),
            AgentTask("task2", "agent2", "Task 2", "analyze", dependencies=["task1"]),
            AgentTask("task3", "agent2", "Task 3", "transform", dependencies=["task1"]),
            AgentTask(
                "task4", "agent2", "Task 4", "persist", dependencies=["task2", "task3"]
            ),
        ]

        sorted_tasks = team_executor._topological_sort(tasks)

        # task1 first, task4 last
        indices = {t.task_id: i for i, t in enumerate(sorted_tasks)}
        assert indices["task1"] < indices["task2"]
        assert indices["task1"] < indices["task3"]
        assert indices["task2"] < indices["task4"]
        assert indices["task3"] < indices["task4"]


class TestDependencyGraph:
    """Tests for dependency graph building."""

    def test_build_dependency_graph_simple(self, team_executor):
        """Test building dependency graph."""
        tasks = [
            AgentTask("task1", "agent1", "Task 1", "generate"),
            AgentTask("task2", "agent2", "Task 2", "analyze", dependencies=["task1"]),
        ]

        graph = team_executor._build_dependency_graph(tasks)

        assert graph["task1"] == ["task2"]
        assert graph["task2"] == []

    def test_build_dependency_graph_complex(self, team_executor):
        """Test building complex dependency graph."""
        tasks = [
            AgentTask("task1", "agent1", "Task 1", "generate"),
            AgentTask("task2", "agent2", "Task 2", "analyze", dependencies=["task1"]),
            AgentTask("task3", "agent2", "Task 3", "transform", dependencies=["task1"]),
            AgentTask(
                "task4", "agent2", "Task 4", "persist", dependencies=["task2", "task3"]
            ),
        ]

        graph = team_executor._build_dependency_graph(tasks)

        assert set(graph["task1"]) == {"task2", "task3"}
        assert graph["task2"] == ["task4"]
        assert graph["task3"] == ["task4"]
        assert graph["task4"] == []


class TestSkillSelection:
    """Tests for skill selection in team executor."""

    @pytest.mark.asyncio
    async def test_select_skill_for_task(self, team_executor):
        """Test selecting skill for a task."""
        task = AgentTask(
            "task1",
            "agent1",
            "Generate creative content",
            "generate",
            available_skills=["skill1", "skill2"],
        )

        team_executor.skill_selector.select_skills = MagicMock(
            return_value=[
                MagicMock(skill_name="skill1", composite_score=0.9),
                MagicMock(skill_name="skill2", composite_score=0.7),
            ]
        )

        selected = await team_executor._select_skill_for_task(task)

        assert selected == "skill1"

    @pytest.mark.asyncio
    async def test_select_skill_fallback_to_first(self, team_executor):
        """Test fallback to first skill when no suggestions."""
        task = AgentTask(
            "task1",
            "agent1",
            "Task",
            "generate",
            available_skills=["fallback_skill"],
        )

        team_executor.skill_selector.select_skills = MagicMock(return_value=[])

        selected = await team_executor._select_skill_for_task(task)

        assert selected == "fallback_skill"

    @pytest.mark.asyncio
    async def test_select_skill_no_available(self, team_executor):
        """Test when no skills available."""
        task = AgentTask(
            "task1",
            "agent1",
            "Task",
            "generate",
            available_skills=[],
        )

        selected = await team_executor._select_skill_for_task(task)

        assert selected == "default"


class TestTaskExecution:
    """Tests for individual task execution."""

    @pytest.mark.asyncio
    async def test_execute_task_success(self, team_executor):
        """Test successful task execution."""
        task = AgentTask(
            "task1",
            "agent1",
            "Generate content",
            "generate",
            available_skills=["skill1"],
        )

        agent = MagicMock(spec=CompoundExecutor)
        agent.execute_task = MagicMock(
            return_value=ExecutionResult(
                success=True,
                output="generated",
                metrics={"coherence": 0.85},
                duration_seconds=1.5,
                token_metrics={},
            )
        )
        team_executor.agents["agent1"] = agent

        team_executor.skill_selector.select_skills = MagicMock(
            return_value=[MagicMock(skill_name="skill1", composite_score=0.9)]
        )

        result = await team_executor._execute_task(task, agent, {})

        assert result.success is True
        assert result.output == "generated"
        assert result.selected_skill == "skill1"

    @pytest.mark.asyncio
    async def test_execute_task_failure(self, team_executor):
        """Test failed task execution."""
        task = AgentTask(
            "task1",
            "agent1",
            "Generate content",
            "generate",
            available_skills=["skill1"],
        )

        agent = MagicMock(spec=CompoundExecutor)
        agent.execute_task = MagicMock(side_effect=RuntimeError("Execution failed"))
        team_executor.agents["agent1"] = agent

        team_executor.skill_selector.select_skills = MagicMock(
            return_value=[MagicMock(skill_name="skill1", composite_score=0.9)]
        )

        result = await team_executor._execute_task(task, agent, {})

        assert result.success is False
        assert "Execution failed" in result.error

    @pytest.mark.asyncio
    async def test_execute_task_with_parent_results(self, team_executor):
        """Test task execution with parent task results as context."""
        task = AgentTask(
            "task2",
            "agent1",
            "Analyze content",
            "analyze",
            available_skills=["skill2"],
            dependencies=["task1"],
        )

        parent_result = AgentTaskResult(
            "task1",
            "agent1",
            success=True,
            output="parent output",
            metrics={},
            selected_skill="skill1",
        )

        agent = MagicMock(spec=CompoundExecutor)
        agent.execute_task = MagicMock(
            return_value=ExecutionResult(
                success=True,
                output="analyzed",
                metrics={"coherence": 0.8},
                duration_seconds=1.2,
                token_metrics={},
            )
        )

        team_executor.skill_selector.select_skills = MagicMock(
            return_value=[MagicMock(skill_name="skill2", composite_score=0.85)]
        )

        result = await team_executor._execute_task(
            task, agent, {"task1": parent_result}
        )

        assert result.success is True


class TestCompoundScoring:
    """Tests for compound score calculation."""

    def test_compute_compound_score_perfect(self, team_executor):
        """Test computing score for perfect execution."""
        results = [
            AgentTaskResult(
                "task1",
                "agent1",
                success=True,
                output="out1",
                metrics={"coherence": 1.0},
                selected_skill="skill1",
                execution_result=ExecutionResult(
                    success=True,
                    output="out1",
                    metrics={},
                    duration_seconds=1.0,
                    token_metrics={"cache_hit_rate": 1.0},
                ),
            ),
            AgentTaskResult(
                "task2",
                "agent2",
                success=True,
                output="out2",
                metrics={"coherence": 1.0},
                selected_skill="skill2",
                execution_result=ExecutionResult(
                    success=True,
                    output="out2",
                    metrics={},
                    duration_seconds=1.0,
                    token_metrics={"cache_hit_rate": 1.0},
                ),
            ),
        ]

        score = team_executor._compute_compound_score(results)

        # Perfect: 100% success + 100% coherence + 100% efficiency = 1.0
        assert score == pytest.approx(1.0, abs=0.01)

    def test_compute_compound_score_partial(self, team_executor):
        """Test computing score for partial success."""
        results = [
            AgentTaskResult(
                "task1",
                "agent1",
                success=True,
                output="out1",
                metrics={"coherence": 0.8},
                selected_skill="skill1",
                execution_result=ExecutionResult(
                    success=True,
                    output="out1",
                    metrics={},
                    duration_seconds=1.0,
                    token_metrics={"cache_hit_rate": 0.5},
                ),
            ),
            AgentTaskResult(
                "task2",
                "agent2",
                success=False,
                output="",
                metrics={},
                selected_skill="skill2",
                error="Failed",
            ),
        ]

        score = team_executor._compute_compound_score(results)

        # 50% success + 40% coherence (1 result) + 25% efficiency = weighted
        assert 0.3 < score < 0.7

    def test_compute_compound_score_empty(self, team_executor):
        """Test computing score with no results."""
        score = team_executor._compute_compound_score([])

        assert score == 0.0

    def test_compute_compound_score_all_failed(self, team_executor):
        """Test computing score when all tasks fail."""
        results = [
            AgentTaskResult(
                "task1",
                "agent1",
                success=False,
                output="",
                metrics={},
                selected_skill="",
                error="Failed",
            ),
        ]

        score = team_executor._compute_compound_score(results)

        # 0% success rate, should be low
        assert score < 0.5


class TestTeamExecution:
    """Tests for team execution orchestration."""

    @pytest.mark.asyncio
    async def test_execute_team_single_task(self, team_executor):
        """Test executing a single task."""
        tasks = [
            AgentTask(
                "task1", "agent1", "Generate", "generate", available_skills=["skill1"]
            )
        ]

        agent = MagicMock(spec=CompoundExecutor)
        agent.execute_task = MagicMock(
            return_value=ExecutionResult(
                success=True,
                output="generated",
                metrics={"coherence": 0.85},
                duration_seconds=1.5,
                token_metrics={"cache_hit_rate": 0.5},
            )
        )
        team_executor.agents["agent1"] = agent

        team_executor.skill_selector.select_skills = MagicMock(
            return_value=[MagicMock(skill_name="skill1", composite_score=0.9)]
        )

        result = await team_executor.execute_team(tasks)

        assert result.success is True
        assert result.tasks_executed == 1
        assert result.tasks_failed == 0

    @pytest.mark.asyncio
    async def test_execute_team_multiple_tasks(self, team_executor):
        """Test executing multiple independent tasks."""
        tasks = [
            AgentTask(
                "task1", "agent1", "Generate", "generate", available_skills=["skill1"]
            ),
            AgentTask(
                "task2", "agent2", "Analyze", "analyze", available_skills=["skill2"]
            ),
        ]

        agent1 = MagicMock(spec=CompoundExecutor)
        agent1.execute_task = MagicMock(
            return_value=ExecutionResult(
                success=True,
                output="generated",
                metrics={"coherence": 0.85},
                duration_seconds=1.5,
                token_metrics={},
            )
        )

        agent2 = MagicMock(spec=CompoundExecutor)
        agent2.execute_task = MagicMock(
            return_value=ExecutionResult(
                success=True,
                output="analyzed",
                metrics={"coherence": 0.8},
                duration_seconds=1.2,
                token_metrics={},
            )
        )

        team_executor.agents["agent1"] = agent1
        team_executor.agents["agent2"] = agent2

        team_executor.skill_selector.select_skills = MagicMock(
            return_value=[MagicMock(skill_name="skill1", composite_score=0.9)]
        )

        result = await team_executor.execute_team(tasks)

        assert result.success is True
        assert result.tasks_executed == 2
        assert result.tasks_failed == 0

    @pytest.mark.asyncio
    async def test_execute_team_with_dependencies(self, team_executor):
        """Test executing tasks with dependencies."""
        tasks = [
            AgentTask(
                "task1", "agent1", "Generate", "generate", available_skills=["skill1"]
            ),
            AgentTask(
                "task2",
                "agent2",
                "Analyze",
                "analyze",
                available_skills=["skill2"],
                dependencies=["task1"],
            ),
        ]

        agent1 = MagicMock(spec=CompoundExecutor)
        agent1.execute_task = MagicMock(
            return_value=ExecutionResult(
                success=True,
                output="generated",
                metrics={"coherence": 0.85},
                duration_seconds=1.5,
                token_metrics={},
            )
        )

        agent2 = MagicMock(spec=CompoundExecutor)
        agent2.execute_task = MagicMock(
            return_value=ExecutionResult(
                success=True,
                output="analyzed",
                metrics={"coherence": 0.8},
                duration_seconds=1.2,
                token_metrics={},
            )
        )

        team_executor.agents["agent1"] = agent1
        team_executor.agents["agent2"] = agent2

        team_executor.skill_selector.select_skills = MagicMock(
            return_value=[MagicMock(skill_name="skill1", composite_score=0.9)]
        )

        result = await team_executor.execute_team(tasks)

        assert result.success is True
        assert result.tasks_executed == 2

    @pytest.mark.asyncio
    async def test_execute_team_missing_agent(self, team_executor):
        """Test handling missing agent."""
        tasks = [
            AgentTask(
                "task1",
                "agent_missing",
                "Task",
                "generate",
                available_skills=["skill1"],
            )
        ]

        result = await team_executor.execute_team(tasks)

        assert result.success is False
        assert result.tasks_failed == 1

    @pytest.mark.asyncio
    async def test_execute_team_partial_failure(self, team_executor):
        """Test handling partial failure."""
        tasks = [
            AgentTask(
                "task1", "agent1", "Generate", "generate", available_skills=["skill1"]
            ),
            AgentTask(
                "task2", "agent2", "Analyze", "analyze", available_skills=["skill2"]
            ),
        ]

        agent1 = MagicMock(spec=CompoundExecutor)
        agent1.execute_task = MagicMock(
            return_value=ExecutionResult(
                success=True,
                output="generated",
                metrics={"coherence": 0.85},
                duration_seconds=1.5,
                token_metrics={},
            )
        )

        agent2 = MagicMock(spec=CompoundExecutor)
        agent2.execute_task = MagicMock(side_effect=RuntimeError("Failed"))

        team_executor.agents["agent1"] = agent1
        team_executor.agents["agent2"] = agent2

        team_executor.skill_selector.select_skills = MagicMock(
            return_value=[MagicMock(skill_name="skill1", composite_score=0.9)]
        )

        result = await team_executor.execute_team(tasks)

        assert result.success is False
        assert result.tasks_executed == 2
        assert result.tasks_failed == 1


class TestTeamExecutorFactory:
    """Tests for factory pattern."""

    def test_create_team_executor(self, mock_mcp_client):
        """Test factory creates team executor."""
        agents = {"agent1": MagicMock(spec=CompoundExecutor)}

        executor = TeamExecutorFactory.create(
            agents, mock_mcp_client, project="test_project"
        )

        assert isinstance(executor, TeamExecutor)
        assert len(executor.agents) == 1
        assert executor.project == "test_project"

    def test_factory_default_project(self, mock_mcp_client):
        """Test factory uses default project."""
        agents = {"agent1": MagicMock(spec=CompoundExecutor)}

        executor = TeamExecutorFactory.create(agents, mock_mcp_client)

        assert executor.project == "cohezion"
