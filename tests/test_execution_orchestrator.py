"""Tests for Phase 4C ExecutionOrchestrator."""

from __future__ import annotations

import pytest

from cohezion.swarm.execution_orchestrator import (
    ExecutionOrchestrator,
    ExecutionReport,
    _topological_sort,
)
from cohezion.swarm.team_orchestrator import TaskSpec, TeamOrchestrator, TeamPlan


# ---------------------------------------------------------------------------
# Topological sort
# ---------------------------------------------------------------------------


class TestTopologicalSort:
    def test_no_dependencies(self):
        """Tasks with no deps all go in wave 1."""
        tasks = [
            TaskSpec(id="t1", subject="A", description=""),
            TaskSpec(id="t2", subject="B", description=""),
        ]
        waves = _topological_sort(tasks)
        assert len(waves) == 1
        assert len(waves[0]) == 2

    def test_linear_chain(self):
        """A -> B -> C produces 3 waves of 1."""
        tasks = [
            TaskSpec(id="t1", subject="A", description=""),
            TaskSpec(id="t2", subject="B", description="", blocked_by=["t1"]),
            TaskSpec(id="t3", subject="C", description="", blocked_by=["t2"]),
        ]
        waves = _topological_sort(tasks)
        assert len(waves) == 3
        assert waves[0][0].id == "t1"
        assert waves[1][0].id == "t2"
        assert waves[2][0].id == "t3"

    def test_parallel_then_join(self):
        """A and B parallel, C depends on both."""
        tasks = [
            TaskSpec(id="t1", subject="A", description=""),
            TaskSpec(id="t2", subject="B", description=""),
            TaskSpec(id="t3", subject="C", description="", blocked_by=["t1", "t2"]),
        ]
        waves = _topological_sort(tasks)
        assert len(waves) == 2
        wave1_ids = {t.id for t in waves[0]}
        assert wave1_ids == {"t1", "t2"}
        assert waves[1][0].id == "t3"

    def test_cycle_breaks(self):
        """Cycle detection forces remaining tasks into one wave."""
        tasks = [
            TaskSpec(id="t1", subject="A", description="", blocked_by=["t2"]),
            TaskSpec(id="t2", subject="B", description="", blocked_by=["t1"]),
        ]
        waves = _topological_sort(tasks)
        # Should still produce something (forced)
        total = sum(len(w) for w in waves)
        assert total == 2


# ---------------------------------------------------------------------------
# ExecutionOrchestrator
# ---------------------------------------------------------------------------


class TestExecutionOrchestrator:
    @pytest.mark.asyncio
    async def test_execute_empty_plan(self):
        """Empty plan produces empty report."""
        plan = TeamPlan(name="empty", intent="test", agents=[], tasks=[])
        orch = ExecutionOrchestrator()
        report = await orch.execute(plan)
        assert isinstance(report, ExecutionReport)
        assert report.status == "completed"
        assert len(report.task_results) == 0

    @pytest.mark.asyncio
    async def test_execute_single_task(self):
        """Single task with no deps executes."""
        plan = TeamPlan(
            name="single",
            intent="test",
            tasks=[TaskSpec(id="t1", subject="Do thing", description="A simple task")],
        )
        orch = ExecutionOrchestrator()
        report = await orch.execute(plan)
        assert len(report.task_results) == 1
        assert report.task_results[0].task_id == "t1"
        assert report.task_results[0].status == "completed"

    @pytest.mark.asyncio
    async def test_execute_parallel_tasks(self):
        """Independent tasks run in parallel wave."""
        plan = TeamPlan(
            name="parallel",
            intent="test",
            tasks=[
                TaskSpec(id="t1", subject="Task A", description="Do A"),
                TaskSpec(id="t2", subject="Task B", description="Do B"),
            ],
        )
        orch = ExecutionOrchestrator()
        report = await orch.execute(plan)
        assert len(report.task_results) == 2
        assert report.status == "completed"

    @pytest.mark.asyncio
    async def test_execute_respects_dependencies(self):
        """Dependent tasks execute after their blockers."""
        plan = TeamPlan(
            name="deps",
            intent="test",
            tasks=[
                TaskSpec(id="t1", subject="First", description="Do first"),
                TaskSpec(
                    id="t2",
                    subject="Second",
                    description="Do second",
                    blocked_by=["t1"],
                ),
            ],
        )
        orch = ExecutionOrchestrator()
        report = await orch.execute(plan)
        assert len(report.task_results) == 2
        # t1 should appear before t2
        ids = [tr.task_id for tr in report.task_results]
        assert ids.index("t1") < ids.index("t2")

    @pytest.mark.asyncio
    async def test_report_tracks_metrics(self):
        """Report aggregates duration and tokens."""
        plan = TeamPlan(
            name="metrics",
            intent="test",
            tasks=[
                TaskSpec(id="t1", subject="A", description="task A"),
            ],
        )
        orch = ExecutionOrchestrator()
        report = await orch.execute(plan)
        assert report.total_duration_ms >= 0
        assert report.total_tokens >= 0
        assert report.report_id.startswith("exec_")

    @pytest.mark.asyncio
    async def test_report_to_dict(self):
        """Report serialization produces expected keys."""
        plan = TeamPlan(
            name="dict-test",
            intent="test",
            tasks=[TaskSpec(id="t1", subject="A", description="task")],
        )
        orch = ExecutionOrchestrator()
        report = await orch.execute(plan)
        d = report.to_dict()
        assert "report_id" in d
        assert "tasks" in d
        assert "status" in d
        assert len(d["tasks"]) == 1


# ---------------------------------------------------------------------------
# TeamOrchestrator.execute_team integration
# ---------------------------------------------------------------------------


class TestTeamOrchestratorExecute:
    @pytest.mark.asyncio
    async def test_execute_team_produces_report(self):
        """execute_team() returns an ExecutionReport."""
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_task_result = {
            "skill_name": "test",
            "output": "ok",
            "tokens": 10,
            "status": "completed",
        }

        # Mock registry to avoid missing cohezion.registry.capability_registry
        mock_registry = MagicMock()
        mock_registry.find.return_value = [
            MagicMock(name="TEST_SKILL", description="A test skill"),
        ]

        with (
            patch(
                "cohezion.swarm.team_execution.TeamCompoundExecutor.execute_task",
                new_callable=AsyncMock,
                return_value=mock_task_result,
            ),
            patch("cohezion.swarm.compound_client.get_compound_client"),
        ):
            orch = TeamOrchestrator()
            orch._registry = mock_registry
            report = await orch.execute_team("test compound engineering", max_agents=2)
        assert hasattr(report, "task_results")
        assert hasattr(report, "status")
        assert hasattr(report, "to_dict")
