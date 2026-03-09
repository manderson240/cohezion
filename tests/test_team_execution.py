"""Tests for team-aware compound execution.

Covers TeamCompoundExecutor (single task, multi-task, model routing,
feedback integration), TeamMetricsAggregator, and ExecutionOrchestrator
compound path.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.swarm.team_execution import TeamCompoundExecutor
from cohezion.swarm.team_metrics import (
    TeamCompoundMetrics,
    TeamMetricsAggregator,
    WaveMetrics,
)
from cohezion.swarm.team_orchestrator import TaskSpec, TeamPlan


# ---------------------------------------------------------------------------
# TeamMetricsAggregator tests
# ---------------------------------------------------------------------------


class TestTeamMetricsAggregator:
    def test_empty_finalize(self) -> None:
        agg = TeamMetricsAggregator(plan_name="empty")
        metrics = agg.finalize(total_duration_ms=100.0)
        assert isinstance(metrics, TeamCompoundMetrics)
        assert metrics.total_tasks == 0
        assert metrics.total_tokens == 0
        assert metrics.plan_name == "empty"
        assert metrics.success_rate == 0.0

    def test_single_wave(self) -> None:
        agg = TeamMetricsAggregator(plan_name="test-plan")
        wave = agg.record_wave(
            wave_index=0,
            task_results=[
                {"tokens": 100, "model": "phi3:mini", "status": "completed"},
                {"tokens": 200, "model": "qwen3-coder:30b", "status": "completed"},
            ],
            duration_ms=500.0,
        )
        assert isinstance(wave, WaveMetrics)
        assert wave.task_count == 2
        assert wave.tokens == 300
        assert wave.successes == 2
        assert wave.failures == 0

        metrics = agg.finalize(total_duration_ms=500.0)
        assert metrics.total_tasks == 2
        assert metrics.total_tokens == 300
        assert metrics.success_rate == 1.0
        assert len(metrics.waves) == 1

    def test_multiple_waves(self) -> None:
        agg = TeamMetricsAggregator(plan_name="multi")
        agg.record_wave(0, [{"tokens": 50, "model": "phi3:mini", "status": "completed"}], 200.0)
        agg.record_wave(
            1,
            [
                {"tokens": 100, "model": "qwen3-coder:30b", "status": "completed"},
                {"tokens": 0, "model": "", "status": "failed"},
            ],
            300.0,
        )

        metrics = agg.finalize(total_duration_ms=500.0)
        assert metrics.total_tasks == 3
        assert metrics.total_tokens == 150
        assert len(metrics.waves) == 2
        assert metrics.success_rate == pytest.approx(2 / 3, abs=0.01)

    def test_parallel_efficiency(self) -> None:
        agg = TeamMetricsAggregator()
        agg.record_wave(0, [{"tokens": 10, "model": "m", "status": "completed"}], 200.0)
        agg.record_wave(1, [{"tokens": 10, "model": "m", "status": "completed"}], 300.0)
        # Sum of wave durations = 500, total = 400 → efficiency = 1.25
        metrics = agg.finalize(total_duration_ms=400.0)
        assert metrics.parallel_efficiency == pytest.approx(1.25, abs=0.01)

    def test_model_usage_tracking(self) -> None:
        agg = TeamMetricsAggregator()
        agg.record_wave(
            0,
            [
                {"tokens": 10, "model": "phi3:mini", "status": "completed"},
                {"tokens": 10, "model": "phi3:mini", "status": "completed"},
                {"tokens": 10, "model": "qwen3-coder:30b", "status": "completed"},
            ],
            100.0,
        )
        metrics = agg.finalize(total_duration_ms=100.0)
        assert metrics.model_usage["phi3:mini"] == 2
        assert metrics.model_usage["qwen3-coder:30b"] == 1

    def test_compound_score_delta(self) -> None:
        agg = TeamMetricsAggregator()
        agg.record_wave(0, [{"tokens": 10, "model": "m", "status": "completed"}], 50.0)
        metrics = agg.finalize(total_duration_ms=50.0, compound_score_delta=0.15)
        assert metrics.compound_score_delta == 0.15


# ---------------------------------------------------------------------------
# TeamCompoundExecutor tests
# ---------------------------------------------------------------------------


class TestTeamCompoundExecutor:
    @pytest.mark.asyncio
    @patch("cohezion.swarm.compound_client.get_compound_client")
    async def test_execute_task_no_matching_skill(self, mock_client: MagicMock) -> None:
        """Tasks with no matching skill return a direct execution result."""
        executor = TeamCompoundExecutor()
        # Use a subject/description with words that won't match any PRIME skill
        # name fragments (the keyword matcher splits skill names on '_')
        task = TaskSpec(
            id="t1",
            subject="zzz qqq xxx",
            description="zzz qqq xxx",
            tags=["nonexistent_zzzzzz"],
        )

        result = await executor.execute_task(task)
        assert result["status"] == "completed"
        assert result["skill_name"] == "direct"
        assert "Executed:" in result["output"]

    @pytest.mark.asyncio
    @patch("cohezion.swarm.compound_client.get_compound_client")
    async def test_execute_task_with_matching_skill(self, mock_client: MagicMock) -> None:
        """When a skill matches, delegates to compound executor."""
        mock_exec = AsyncMock()
        mock_exec.execute_skill.return_value = MagicMock(
            final_output="generated code",
            total_tokens=150,
            total_duration_ms=200.0,
            model_usage={"qwen3-coder:30b": 1},
            steps=[],
        )

        executor = TeamCompoundExecutor(compound_executor=mock_exec)
        # Mock the engine to find a skill
        mock_engine = MagicMock()
        mock_spec = MagicMock()
        mock_spec.name = "CODE_REVIEW_PRIME"
        mock_engine.get_spec_by_name.return_value = mock_spec
        mock_engine.parse_all.return_value = []
        mock_engine._cache = {}
        executor._engine = mock_engine

        task = TaskSpec(
            id="t2",
            subject="Code review",
            description="Review the module",
            tags=["CODE_REVIEW_PRIME"],
        )

        result = await executor.execute_task(task)
        assert result["status"] == "completed"
        assert result["skill_name"] == "CODE_REVIEW_PRIME"
        assert result["tokens"] == 150

    @pytest.mark.asyncio
    @patch("cohezion.swarm.compound_client.get_compound_client")
    async def test_execute_task_handles_exception(self, mock_client: MagicMock) -> None:
        """When compound execution raises, the result captures the error."""
        mock_exec = AsyncMock()
        mock_exec.execute_skill.side_effect = RuntimeError("Ollama down")

        executor = TeamCompoundExecutor(compound_executor=mock_exec)
        mock_engine = MagicMock()
        mock_spec = MagicMock()
        mock_spec.name = "FAILING_SKILL"
        mock_engine.get_spec_by_name.return_value = mock_spec
        mock_engine.parse_all.return_value = []
        mock_engine._cache = {}
        executor._engine = mock_engine

        task = TaskSpec(
            id="t3",
            subject="Failing task",
            description="This will fail",
            tags=["FAILING_SKILL"],
        )

        result = await executor.execute_task(task)
        assert result["status"] == "failed"
        assert "Ollama down" in result["error"]

    @pytest.mark.asyncio
    @patch("cohezion.swarm.compound_client.get_compound_client")
    async def test_feedback_loop_integration(self, mock_client: MagicMock) -> None:
        """When auto_feedback=True, a feedback cycle is triggered after execution."""
        mock_exec = AsyncMock()
        mock_exec.execute_skill.return_value = MagicMock(
            final_output="result",
            total_tokens=50,
            total_duration_ms=100.0,
            model_usage={"phi3:mini": 1},
            steps=[],
        )

        executor = TeamCompoundExecutor(
            compound_executor=mock_exec,
            auto_feedback=True,
        )
        mock_engine = MagicMock()
        mock_spec = MagicMock()
        mock_spec.name = "FEEDBACK_SKILL"
        mock_engine.get_spec_by_name.return_value = mock_spec
        mock_engine.parse_all.return_value = []
        mock_engine._cache = {}
        executor._engine = mock_engine

        task = TaskSpec(
            id="t4",
            subject="Feedback test",
            description="Test feedback",
            tags=["FEEDBACK_SKILL"],
        )

        with patch.object(executor, "_run_feedback", new_callable=AsyncMock) as mock_fb:
            result = await executor.execute_task(task)
            assert result["status"] == "completed"
            mock_fb.assert_awaited_once_with("FEEDBACK_SKILL", "Test feedback")

    def test_create_metrics_aggregator(self) -> None:
        executor = TeamCompoundExecutor()
        agg = executor.create_metrics_aggregator("test-plan")
        assert isinstance(agg, TeamMetricsAggregator)


# ---------------------------------------------------------------------------
# ExecutionOrchestrator compound path tests
# ---------------------------------------------------------------------------


class TestExecutionOrchestratorCompound:
    @pytest.mark.asyncio
    @patch("cohezion.swarm.compound_client.get_compound_client")
    async def test_orchestrator_uses_compound_executor(self, mock_client: MagicMock) -> None:
        """When compound_executor is provided, ExecutionOrchestrator delegates to it."""
        from cohezion.swarm.execution_orchestrator import ExecutionOrchestrator

        mock_compound = AsyncMock()
        mock_compound.execute_task.return_value = {
            "skill_name": "test_skill",
            "output": "done",
            "tokens": 42,
            "status": "completed",
        }

        orch = ExecutionOrchestrator(compound_executor=mock_compound)

        plan = TeamPlan(
            name="test-plan",
            intent="Test compound path",
            tasks=[
                TaskSpec(
                    id="t1",
                    subject="Single task",
                    description="Just one task",
                    tags=["test"],
                )
            ],
        )

        report = await orch.execute(plan)
        assert report.status == "completed"
        assert len(report.task_results) == 1
        assert report.task_results[0].task_id == "t1"
        mock_compound.execute_task.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("cohezion.swarm.compound_client.get_compound_client")
    async def test_orchestrator_direct_fallback(self, mock_client: MagicMock) -> None:
        """Without compound_executor, falls back to direct execution."""
        from cohezion.swarm.execution_orchestrator import ExecutionOrchestrator

        orch = ExecutionOrchestrator()

        plan = TeamPlan(
            name="fallback-plan",
            intent="Test fallback",
            tasks=[
                TaskSpec(
                    id="t1",
                    subject="Direct task",
                    description="Uses direct path",
                    tags=["testing"],
                )
            ],
        )

        report = await orch.execute(plan)
        assert report.status == "completed"
        assert len(report.task_results) == 1

    @pytest.mark.asyncio
    @patch("cohezion.swarm.compound_client.get_compound_client")
    async def test_orchestrator_dependency_waves(self, mock_client: MagicMock) -> None:
        """Tasks are sorted into waves by dependencies."""
        from cohezion.swarm.execution_orchestrator import ExecutionOrchestrator

        mock_compound = AsyncMock()
        mock_compound.execute_task.return_value = {
            "skill_name": "test",
            "output": "done",
            "tokens": 10,
            "status": "completed",
        }

        orch = ExecutionOrchestrator(compound_executor=mock_compound)

        plan = TeamPlan(
            name="dag-plan",
            intent="Test DAG execution",
            tasks=[
                TaskSpec(id="t1", subject="Research", description="First", tags=["research"]),
                TaskSpec(
                    id="t2",
                    subject="Implement A",
                    description="After research",
                    blocked_by=["t1"],
                    tags=["impl"],
                ),
                TaskSpec(
                    id="t3",
                    subject="Implement B",
                    description="After research",
                    blocked_by=["t1"],
                    tags=["impl"],
                ),
                TaskSpec(
                    id="t4",
                    subject="Integration",
                    description="After both impls",
                    blocked_by=["t2", "t3"],
                    tags=["test"],
                ),
            ],
        )

        report = await orch.execute(plan)
        assert report.status == "completed"
        assert len(report.task_results) == 4
        # All 4 tasks should have been called
        assert mock_compound.execute_task.await_count == 4

    @pytest.mark.asyncio
    @patch("cohezion.swarm.compound_client.get_compound_client")
    async def test_orchestrator_handles_compound_failure(self, mock_client: MagicMock) -> None:
        """A failed compound task results in partial status."""
        from cohezion.swarm.execution_orchestrator import ExecutionOrchestrator

        call_count = 0

        async def side_effect(task):
            nonlocal call_count
            call_count += 1
            if task.id == "t2":
                raise RuntimeError("boom")
            return {
                "skill_name": "test",
                "output": "ok",
                "tokens": 10,
                "status": "completed",
            }

        mock_compound = AsyncMock()
        mock_compound.execute_task.side_effect = side_effect

        orch = ExecutionOrchestrator(compound_executor=mock_compound)
        plan = TeamPlan(
            name="partial-plan",
            intent="Test partial failure",
            tasks=[
                TaskSpec(id="t1", subject="OK task", description="Succeeds", tags=["test"]),
                TaskSpec(id="t2", subject="Bad task", description="Fails", tags=["test"]),
            ],
        )

        report = await orch.execute(plan)
        assert report.status == "partial"
        statuses = {tr.task_id: tr.status for tr in report.task_results}
        assert statuses["t1"] == "completed"
        assert statuses["t2"] == "failed"


# ---------------------------------------------------------------------------
# TeamOrchestrator.execute_team integration test
# ---------------------------------------------------------------------------


class TestTeamOrchestratorExecuteTeam:
    @pytest.mark.asyncio
    @patch("cohezion.swarm.compound_client.get_compound_client")
    async def test_execute_team_end_to_end(self, mock_client: MagicMock) -> None:
        """execute_team generates a plan and runs it through the compound path."""
        from cohezion.swarm.team_orchestrator import TeamOrchestrator

        mock_exec = AsyncMock()
        mock_exec.execute_task.return_value = {
            "skill_name": "test",
            "output": "done",
            "tokens": 10,
            "status": "completed",
        }

        # Mock registry to avoid missing cohezion.registry.capability_registry
        mock_cap = MagicMock()
        mock_cap.name = "TEST_SKILL"
        mock_cap.description = "A test skill"
        mock_cap.type = "skill"
        mock_cap.tags = ["test"]
        mock_registry = MagicMock()
        mock_registry.find.return_value = [mock_cap]

        with patch(
            "cohezion.swarm.team_execution.TeamCompoundExecutor.execute_task",
            mock_exec.execute_task,
        ):
            orch = TeamOrchestrator()
            orch._registry = mock_registry
            report = await orch.execute_team("test intent", max_agents=2)
            assert report.status in ("completed", "partial")
            assert len(report.task_results) > 0


# ---------------------------------------------------------------------------
# WaveMetrics and TeamCompoundMetrics model tests
# ---------------------------------------------------------------------------


class TestMetricsModels:
    def test_wave_metrics_defaults(self) -> None:
        w = WaveMetrics()
        assert w.wave_index == 0
        assert w.task_count == 0
        assert w.tokens == 0
        assert w.model_usage == {}

    def test_team_compound_metrics_defaults(self) -> None:
        m = TeamCompoundMetrics()
        assert m.plan_name == ""
        assert m.total_tasks == 0
        assert m.parallel_efficiency == 0.0
        assert m.timestamp > 0
