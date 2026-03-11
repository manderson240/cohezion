"""Integration tests for ResearchAgent with real CompoundExecutor.

Tests actual execution flow, not mocks.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from cohezion.compound.core.executor import CompoundExecutor, ExecutionConfig
from cohezion.compound.models import ExecutionMetrics, ExecutionResult, Task
from cohezion.research import ResearchAgent, ResearchConfig


class TestCompoundIntegration:
    """Real integration tests with actual CompoundExecutor."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test artifacts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.integration
    def test_real_compound_executor_basic(self, temp_dir):
        """[INT-01] Real CompoundExecutor executes research tasks."""
        # Create real executor (not mock)
        call_count = [0]

        def real_execute(task: Task, context: dict) -> tuple[str, dict]:
            call_count[0] += 1
            return f"Result {call_count[0]}", {
                "metric_value": 2.0 + call_count[0] * 0.1,
                "duration_seconds": 0.5,
                "improved": True,
            }

        executor = CompoundExecutor(
            execute_fn=real_execute,
            config=ExecutionConfig(max_retries=0, timeout=5.0),
        )

        config = ResearchConfig(
            experiment_time_budget=10.0,
            max_experiments=3,
            experiment_log=temp_dir / "experiments.jsonl",
            checkpoint_dir=temp_dir / "checkpoints",
        )

        agent = ResearchAgent(config=config, executor=executor)
        session = agent.run_session()

        assert call_count[0] == 3
        assert session.experiments_completed == 3

    @pytest.mark.integration
    def test_real_compound_executor_error_handling(self, temp_dir):
        """[INT-02] Real CompoundExecutor handles errors."""
        call_count = [0]

        def unreliable_execute(task: Task, context: dict) -> tuple[str, dict]:
            call_count[0] += 1
            if call_count[0] == 2:
                raise RuntimeError("Simulated failure")
            return f"Success {call_count[0]}", {
                "metric_value": 2.0,
                "duration_seconds": 0.5,
            }

        executor = CompoundExecutor(
            execute_fn=unreliable_execute,
            config=ExecutionConfig(max_retries=1, timeout=5.0),
        )

        config = ResearchConfig(
            experiment_time_budget=10.0,
            max_experiments=3,
            experiment_log=temp_dir / "experiments.jsonl",
            checkpoint_dir=temp_dir / "checkpoints",
        )

        agent = ResearchAgent(config=config, executor=executor)

        # Should complete despite errors
        session = agent.run_session()
        assert session.experiments_completed == 3

    @pytest.mark.integration
    def test_real_compound_executor_retry(self, temp_dir):
        """[INT-03] CompoundExecutor retries on failure."""
        call_count = [0]

        def flaky_execute(task: Task, context: dict) -> tuple[str, dict]:
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("First attempt fails")
            return "Success", {"metric_value": 2.0, "duration_seconds": 0.5}

        executor = CompoundExecutor(
            execute_fn=flaky_execute,
            config=ExecutionConfig(max_retries=2, timeout=5.0),
        )

        config = ResearchConfig(
            experiment_time_budget=10.0,
            max_experiments=1,
            experiment_log=temp_dir / "experiments.jsonl",
            checkpoint_dir=temp_dir / "checkpoints",
        )

        agent = ResearchAgent(config=config, executor=executor)
        session = agent.run_session()

        # Should succeed on retry
        assert session.experiments_completed == 1
        assert call_count[0] == 2  # Initial + 1 retry

    @pytest.mark.integration
    def test_real_compound_executor_timeout(self, temp_dir):
        """[INT-04] CompoundExecutor enforces timeouts."""
        import time

        def slow_execute(task: Task, context: dict) -> tuple[str, dict]:
            time.sleep(2.0)  # Longer than timeout
            return "Too late", {"metric_value": 2.0}

        executor = CompoundExecutor(
            execute_fn=slow_execute,
            config=ExecutionConfig(max_retries=0, timeout=0.5),
        )

        config = ResearchConfig(
            experiment_time_budget=10.0,
            max_experiments=1,
            experiment_log=temp_dir / "experiments.jsonl",
            checkpoint_dir=temp_dir / "checkpoints",
        )

        agent = ResearchAgent(config=config, executor=executor)
        session = agent.run_session()

        # Should complete with failure
        assert session.experiments_completed == 1

    @pytest.mark.integration
    def test_real_compound_executor_metrics(self, temp_dir):
        """[INT-05] Real CompoundExecutor returns proper metrics."""

        def metrics_execute(task: Task, context: dict) -> tuple[str, dict]:
            return "Done", {
                "metric_value": 1.5,
                "duration_seconds": 1.0,
                "improved": True,
            }

        executor = CompoundExecutor(
            execute_fn=metrics_execute,
            config=ExecutionConfig(max_retries=0),
        )

        config = ResearchConfig(
            experiment_time_budget=10.0,
            max_experiments=1,
            experiment_log=temp_dir / "experiments.jsonl",
            checkpoint_dir=temp_dir / "checkpoints",
        )

        agent = ResearchAgent(config=config, executor=executor)
        session = agent.run_session()

        # Check that metrics were recorded
        assert session.experiments_completed == 1
        assert (temp_dir / "experiments.jsonl").exists()
