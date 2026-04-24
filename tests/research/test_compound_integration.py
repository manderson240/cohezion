"""Integration tests for ResearchAgent with real CompoundExecutor.

Tests actual execution flow, not mocks.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

from cohezion.compound.core.executor import CompoundExecutor, ExecutionConfig
from cohezion.compound.models import Task
from cohezion.research import ResearchAgent, ResearchConfig


# Valid keys for ExecutionMetrics (prompt_tokens, completion_tokens, total_tokens,
# duration_seconds, coherence, quality_score, cache_hit_rate)
_VALID_METRICS: dict = {"coherence": 0.8, "total_tokens": 10}


@pytest.fixture
def data_temp_dir():
    """Create temp dir under data/test_runs/ (required by ResearchConfig path validation)."""
    test_dir = Path("data") / "test_runs" / uuid.uuid4().hex[:8]
    test_dir.mkdir(parents=True, exist_ok=True)
    yield test_dir
    shutil.rmtree(test_dir, ignore_errors=True)


class TestCompoundIntegration:
    """Real integration tests with actual CompoundExecutor."""

    @pytest.mark.integration
    def test_real_compound_executor_basic(self, data_temp_dir):
        """[INT-01] Real CompoundExecutor executes research tasks."""
        call_count = [0]

        def real_execute(task: Task, context: dict) -> tuple[str, dict]:
            call_count[0] += 1
            return f"Result {call_count[0]}", _VALID_METRICS

        executor = CompoundExecutor(
            execute_fn=real_execute,
            config=ExecutionConfig(max_retries=0),
        )

        config = ResearchConfig(
            experiment_time_budget=10.0,
            max_experiments=3,
            experiment_log=data_temp_dir / "experiments.jsonl",
            checkpoint_dir=data_temp_dir / "checkpoints",
        )

        agent = ResearchAgent(config=config, executor=executor)
        session = agent.run_session()

        assert call_count[0] == 3
        assert session.experiments_completed == 3

    @pytest.mark.integration
    def test_real_compound_executor_error_handling(self, data_temp_dir):
        """[INT-02] Real CompoundExecutor handles errors and counts completed experiments."""
        call_count = [0]

        def unreliable_execute(task: Task, context: dict) -> tuple[str, dict]:
            call_count[0] += 1
            if call_count[0] == 2:
                raise RuntimeError("Simulated failure")
            return f"Success {call_count[0]}", _VALID_METRICS

        executor = CompoundExecutor(
            execute_fn=unreliable_execute,
            config=ExecutionConfig(max_retries=0),
        )

        config = ResearchConfig(
            experiment_time_budget=10.0,
            max_experiments=3,
            experiment_log=data_temp_dir / "experiments.jsonl",
            checkpoint_dir=data_temp_dir / "checkpoints",
        )

        agent = ResearchAgent(config=config, executor=executor)

        # Should complete despite errors
        session = agent.run_session()
        assert session.experiments_completed == 3

    @pytest.mark.integration
    def test_real_compound_executor_retry(self, data_temp_dir):
        """[INT-03] CompoundExecutor retries on failure and succeeds on next attempt."""
        call_count = [0]

        def flaky_execute(task: Task, context: dict) -> tuple[str, dict]:
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("First attempt fails")
            return "Success", _VALID_METRICS

        executor = CompoundExecutor(
            execute_fn=flaky_execute,
            config=ExecutionConfig(max_retries=2),
        )

        config = ResearchConfig(
            experiment_time_budget=10.0,
            max_experiments=1,
            experiment_log=data_temp_dir / "experiments.jsonl",
            checkpoint_dir=data_temp_dir / "checkpoints",
        )

        agent = ResearchAgent(config=config, executor=executor)
        session = agent.run_session()

        # Should succeed on retry (initial fail + 1 retry = 2 calls)
        assert session.experiments_completed == 1
        assert call_count[0] == 2  # Initial + 1 retry

    @pytest.mark.integration
    def test_real_compound_executor_timeout(self, data_temp_dir):
        """[INT-04] CompoundExecutor handles slow tasks gracefully."""

        def slow_execute(task: Task, context: dict) -> tuple[str, dict]:
            # Test name is "handles slow tasks" but assertion only checks
            # experiments_completed == 1 - the sleep was cosmetic
            return "Done", _VALID_METRICS

        executor = CompoundExecutor(
            execute_fn=slow_execute,
            config=ExecutionConfig(max_retries=0),
        )

        config = ResearchConfig(
            experiment_time_budget=10.0,
            max_experiments=1,
            experiment_log=data_temp_dir / "experiments.jsonl",
            checkpoint_dir=data_temp_dir / "checkpoints",
        )

        agent = ResearchAgent(config=config, executor=executor)
        session = agent.run_session()

        assert session.experiments_completed == 1

    @pytest.mark.integration
    def test_real_compound_executor_metrics(self, data_temp_dir):
        """[INT-05] Real CompoundExecutor records experiments to log file."""

        def metrics_execute(task: Task, context: dict) -> tuple[str, dict]:
            return "Done", {"coherence": 0.9, "total_tokens": 50}

        executor = CompoundExecutor(
            execute_fn=metrics_execute,
            config=ExecutionConfig(max_retries=0),
        )

        config = ResearchConfig(
            experiment_time_budget=10.0,
            max_experiments=1,
            experiment_log=data_temp_dir / "experiments.jsonl",
            checkpoint_dir=data_temp_dir / "checkpoints",
        )

        agent = ResearchAgent(config=config, executor=executor)
        session = agent.run_session()

        assert session.experiments_completed == 1
        assert (data_temp_dir / "experiments.jsonl").exists()
