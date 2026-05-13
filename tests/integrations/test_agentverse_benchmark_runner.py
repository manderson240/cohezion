"""Tests for AgentVerseBenchmarkRunner.

TDD tests for AgentVerseBenchmarkRunner that runs AgentVerse benchmarks
and captures Cohezion coherence metrics for skill enhancement.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestAgentVerseBenchmarkRunner:
    """[P0] Tests for AgentVerseBenchmarkRunner."""

    @pytest.fixture()
    def mock_executor(self):
        """Create mock CompoundExecutor."""
        executor = MagicMock()
        executor.execute_task = MagicMock()
        return executor

    @pytest.fixture()
    def mock_mcp_client(self):
        """Create mock MCP client."""
        client = MagicMock()
        client.query = AsyncMock(return_value=[])
        client.store_node = AsyncMock(return_value={"id": "benchmark_id"})
        return client

    @pytest.fixture()
    def runner(self, mock_executor, mock_mcp_client):
        """Create benchmark runner."""
        from cohezion.integrations.agentverse import AgentVerseBenchmarkRunner

        runner = AgentVerseBenchmarkRunner(
            executor=mock_executor,
            mcp_client=mock_mcp_client,
        )
        return runner

    def test_initialization(self, runner, mock_executor):
        """[P0] Should initialize with executor."""
        assert runner.executor == mock_executor
        assert runner.results == []

    def test_initialization_with_skills(self, mock_executor, mock_mcp_client):
        """[P1] Should accept list of Cohezion skills to test."""
        from cohezion.integrations.agentverse import AgentVerseBenchmarkRunner

        skills = ["python_PRIME", "testing_PRIME", "code_review_PRIME"]
        runner = AgentVerseBenchmarkRunner(
            executor=mock_executor,
            mcp_client=mock_mcp_client,
            cohezion_skills=skills,
        )
        assert runner.cohezion_skills == skills

    def test_run_single_task(self, runner, mock_executor):
        """[P0] Should run a single benchmark task."""
        mock_executor.execute_task.return_value = MagicMock(
            success=True,
            output="task completed",
            metrics={"coherence": 0.8, "alignment": 0.9},
            duration_seconds=2.0,
        )

        result = runner.run_single_task(
            task_description="Write a test function",
            skill_name="testing_PRIME",
        )

        mock_executor.execute_task.assert_called_once()
        assert result.success is True
        assert result.metrics["coherence"] == 0.8

    def test_run_batch_benchmark(self, runner, mock_executor):
        """[P0] Should run batch benchmark across multiple tasks."""
        mock_executor.execute_task.return_value = MagicMock(
            success=True,
            output="done",
            metrics={"coherence": 0.75},
            duration_seconds=1.0,
        )

        tasks = [
            {"task": "task 1", "skill": "python_PRIME"},
            {"task": "task 2", "skill": "testing_PRIME"},
        ]

        results = runner.run_batch_benchmark(tasks)

        assert mock_executor.execute_task.call_count == 2
        assert len(results) == 2

    def test_capture_coherence_metrics(self, runner, mock_executor):
        """[P0] Should capture coherence metrics from each execution."""
        mock_executor.execute_task.return_value = MagicMock(
            success=True,
            output="output",
            metrics={"coherence": 0.85},
            duration_seconds=1.0,
        )

        runner.run_single_task("test task", "test_PRIME")

        assert len(runner.results) == 1
        assert runner.results[0].metrics["coherence"] == 0.85

    def test_capture_alignments(self, runner, mock_executor):
        """[P1] Should capture alignment metrics."""
        mock_executor.execute_task.return_value = MagicMock(
            success=True,
            output="done",
            metrics={"alignment": {"intent_match": 0.9, "constraint_satisfaction": 0.8}},
            duration_seconds=1.0,
        )

        runner.run_single_task("test", "test_PRIME")

        assert "alignment" in runner.results[0].metrics

    def test_detect_refinement_triggers(self, runner, mock_executor):
        """[P1] Should detect when skill refinement should be triggered."""
        mock_executor.execute_task.return_value = MagicMock(
            success=False,
            output="failed",
            metrics={"coherence": 0.3},
            duration_seconds=0.5,
        )

        runner.run_single_task("failing task", "test_PRIME")

        assert runner.should_trigger_refinement(runner.results[0]) is True

    def test_should_trigger_refinement_high_coherence(self, runner):
        """[P1] Should not trigger refinement for high coherence."""
        from cohezion.integrations.agentverse import BenchmarkResult

        result = BenchmarkResult(
            task="test",
            skill="python_PRIME",
            success=True,
            metrics={"coherence": 0.8},
        )

        assert runner.should_trigger_refinement(result) is False


class TestBenchmarkResult:
    """[P0] Tests for BenchmarkResult dataclass."""

    def test_result_creation(self):
        """[P0] Should create benchmark result."""
        from cohezion.integrations.agentverse import BenchmarkResult

        result = BenchmarkResult(
            task="Write a test",
            skill="testing_PRIME",
            success=True,
            metrics={"coherence": 0.85},
        )

        assert result.task == "Write a test"
        assert result.skill == "testing_PRIME"
        assert result.success is True
        assert result.metrics["coherence"] == 0.85

    def test_result_with_duration(self):
        """[P1] Should record duration."""
        from cohezion.integrations.agentverse import BenchmarkResult

        result = BenchmarkResult(
            task="test",
            skill="test_PRIME",
            success=True,
            metrics={},
            duration_seconds=3.5,
        )

        assert result.duration_seconds == 3.5


class TestBenchmarkRunnerAnalysis:
    """[P1] Tests for benchmark analysis capabilities."""

    @pytest.fixture()
    def runner(self):
        """Create runner with mock executor and client."""
        from cohezion.integrations.agentverse import AgentVerseBenchmarkRunner

        runner = AgentVerseBenchmarkRunner(
            executor=MagicMock(),
            mcp_client=MagicMock(),
        )
        return runner

    def test_get_skill_coherence_summary(self, runner):
        """[P1] Should compute per-skill coherence summary."""
        from cohezion.integrations.agentverse import BenchmarkResult

        runner.results = [
            BenchmarkResult(task="t1", skill="python_PRIME", success=True, metrics={"coherence": 0.8}),
            BenchmarkResult(task="t2", skill="python_PRIME", success=True, metrics={"coherence": 0.7}),
            BenchmarkResult(task="t3", skill="testing_PRIME", success=True, metrics={"coherence": 0.9}),
        ]

        summary = runner.get_skill_coherence_summary()

        assert "python_PRIME" in summary
        assert summary["python_PRIME"]["avg_coherence"] == pytest.approx(0.75, rel=0.01)
        assert "testing_PRIME" in summary
        assert summary["testing_PRIME"]["avg_coherence"] == 0.9

    def test_identify_weak_skills(self, runner):
        """[P1] Should identify skills with low coherence."""
        from cohezion.integrations.agentverse import BenchmarkResult

        runner.results = [
            BenchmarkResult(task="t1", skill="python_PRIME", success=True, metrics={"coherence": 0.8}),
            BenchmarkResult(task="t2", skill="weak_skill_PRIME", success=True, metrics={"coherence": 0.35}),
        ]

        weak = runner.identify_weak_skills(threshold=0.5)

        assert len(weak) >= 1

    def test_get_refinement_candidates(self, runner):
        """[P1] Should return skills that need refinement."""
        from cohezion.integrations.agentverse import BenchmarkResult

        runner.results = [
            BenchmarkResult(task="t1", skill="python_PRIME", success=False, metrics={"coherence": 0.3}),
            BenchmarkResult(task="t2", skill="testing_PRIME", success=True, metrics={"coherence": 0.85}),
        ]

        candidates = runner.get_refinement_candidates()

        assert len(candidates) >= 1


class TestBenchmarkRunnerPersistence:
    """[P1] Tests for benchmark result persistence."""

    @pytest.fixture()
    def runner(self):
        """Create runner with mock dependencies."""
        from cohezion.integrations.agentverse import AgentVerseBenchmarkRunner

        mock_client = MagicMock()
        mock_client.vault_write = MagicMock(return_value="ok")
        mock_client.vault_list = MagicMock(return_value=[])
        mock_client.vault_read = MagicMock(return_value="{}")

        runner = AgentVerseBenchmarkRunner(
            executor=MagicMock(),
            mcp_client=mock_client,
        )
        return runner

    def test_persist_results_calls_vault_write(self, runner):
        """[P1] Should call vault_write with correct path."""
        from cohezion.integrations.agentverse import BenchmarkResult

        runner.results = [
            BenchmarkResult(
                task="test",
                skill="test_PRIME",
                success=True,
                metrics={"coherence": 0.8},
            )
        ]

        path = runner.persist_results()
        assert path is not None
        assert "/vault/benchmarks/" in path
        runner.mcp_client.vault_write.assert_called_once()

    def test_persist_results_includes_all_fields(self, runner):
        """[P1] Should include all required fields in persisted data."""
        from cohezion.integrations.agentverse import BenchmarkResult

        runner.results = [
            BenchmarkResult(
                task="task1",
                skill="python_PRIME",
                success=True,
                metrics={"coherence": 0.9},
            ),
            BenchmarkResult(
                task="task2",
                skill="testing_PRIME",
                success=False,
                metrics={"coherence": 0.3},
            ),
        ]

        runner.persist_results()
        call_args = runner.mcp_client.vault_write.call_args
        written_path = call_args[0][0]
        written_content = call_args[0][1]

        assert "/vault/benchmarks/" in written_path
        assert "python_PRIME" in written_content
        assert "testing_PRIME" in written_content

    def test_load_historical_results_returns_list(self, runner):
        """[P1] Should return list from load_historical_results."""
        results = runner.load_historical_results()
        assert isinstance(results, list)

    def test_load_historical_parses_json_files(self, runner):
        """[P1] Should parse JSON files from vault."""
        runner.mcp_client.vault_list.return_value = [
            "/vault/benchmarks/test1.json",
            "/vault/benchmarks/test2.json",
        ]
        runner.mcp_client.vault_read.side_effect = [
            '{"coherence": 0.8, "skill": "python_PRIME"}',
            '{"coherence": 0.6, "skill": "testing_PRIME"}',
        ]

        results = runner.load_historical_results()
        assert len(results) == 2
        assert results[0]["coherence"] == 0.8
        assert results[1]["skill"] == "testing_PRIME"
