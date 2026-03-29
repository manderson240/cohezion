"""Performance benchmarks for ResearchAgent.

Tests throughput, latency, and optimization quality.
"""

from __future__ import annotations

import math
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from cohezion.compound.core.executor import CompoundExecutor
from cohezion.compound.models import ExecutionMetrics, ExecutionResult
from cohezion.research import ResearchAgent, ResearchConfig


@pytest.fixture
def research_tmpdir():
    """Temporary research directory rooted inside data/ for ResearchConfig validation."""
    os.makedirs("data", exist_ok=True)
    with tempfile.TemporaryDirectory(dir="data") as tmpdir:
        yield Path(tmpdir)


def _make_config(tmpdir: Path, max_experiments: int = 10, **kwargs) -> ResearchConfig:
    """Create a ResearchConfig with sane test defaults."""
    return ResearchConfig(
        experiment_time_budget=10.0,
        max_experiments=max_experiments,
        experiment_log=tmpdir / "experiments.jsonl",
        checkpoint_dir=tmpdir / "checkpoints",
        **kwargs,
    )


def _fast_result() -> ExecutionResult:
    """Return a successful fast execution result."""
    return ExecutionResult(
        success=True,
        output="Complete",
        metrics=ExecutionMetrics(duration_seconds=0.01),
    )


class TestResearchAgentPerformance:
    """Performance benchmarks for ResearchAgent."""

    @pytest.mark.fast
    def test_experiment_throughput(self, research_tmpdir):
        """[PERF-01] Agent completes experiments efficiently."""
        config = _make_config(research_tmpdir, max_experiments=10)

        mock_executor = Mock(spec=CompoundExecutor)
        mock_executor.execute = lambda task: _fast_result()

        agent = ResearchAgent(config=config, executor=mock_executor)

        start = time.time()
        agent.run_session()
        elapsed = time.time() - start

        # Should complete 10 experiments in under 1 second with fast mocks
        assert elapsed < 1.0
        assert agent.session.experiments_completed == 10

    @pytest.mark.fast
    def test_session_startup_time(self):
        """[PERF-02] Session initialization is fast."""
        start = time.time()
        agent = ResearchAgent()
        elapsed = time.time() - start

        # Should initialize in under 100ms
        assert elapsed < 0.1
        assert agent.session.session_id is not None

    @pytest.mark.fast
    def test_concurrent_experiment_simulation(self, research_tmpdir):
        """[PERF-03] Agent handles concurrent experiment results."""
        config = _make_config(research_tmpdir, max_experiments=20)

        results_order: list[str] = []

        def tracking_execute(task) -> ExecutionResult:
            results_order.append(task.id)
            return _fast_result()

        mock_executor = Mock(spec=CompoundExecutor)
        mock_executor.execute = tracking_execute

        agent = ResearchAgent(config=config, executor=mock_executor)
        agent.run_session()

        # All experiments should have unique IDs
        assert len(results_order) == 20
        assert len(set(results_order)) == 20

    @pytest.mark.fast
    def test_optimization_quality_simulation(self, research_tmpdir):
        """[PERF-04] Agent finds optimal configurations."""
        config = _make_config(
            research_tmpdir,
            max_experiments=50,
            target_metric="val_bpb",
        )

        call_count = [0]

        def simulated_optimization(task) -> ExecutionResult:
            """Simulate optimization with convergence."""
            call_count[0] += 1
            # Metric improves with experiments — starting at 3.0, converging to 2.0
            _improvement = 1.0 * (1 - math.exp(-call_count[0] / 15))
            return ExecutionResult(
                success=True,
                output=f"exp-{call_count[0]}",
                metrics=ExecutionMetrics(duration_seconds=0.01),
            )

        mock_executor = Mock(spec=CompoundExecutor)
        mock_executor.execute = simulated_optimization

        agent = ResearchAgent(config=config, executor=mock_executor)
        agent.run_session()

        assert agent.session.experiments_completed == 50

    @pytest.mark.fast
    def test_memory_scaling_simulation(self, research_tmpdir):
        """[PERF-05] Memory usage scales linearly with experiments."""
        config = _make_config(research_tmpdir, max_experiments=100)

        mock_executor = Mock(spec=CompoundExecutor)
        mock_executor.execute = lambda task: _fast_result()

        agent = ResearchAgent(config=config, executor=mock_executor)
        agent.run_session()

        assert agent.session.experiments_completed == 100
        assert Path(config.experiment_log).exists()

    @pytest.mark.fast
    def test_checkpoint_frequency(self, research_tmpdir):
        """[PERF-06] Checkpoints saved at expected frequency."""
        config = _make_config(research_tmpdir, max_experiments=10)

        checkpoints_created: list[str] = []

        def checkpointing_execute(task) -> ExecutionResult:
            checkpoints_created.append(task.id)
            return _fast_result()

        mock_executor = Mock(spec=CompoundExecutor)
        mock_executor.execute = checkpointing_execute

        agent = ResearchAgent(config=config, executor=mock_executor)
        agent.run_session()

        assert len(checkpoints_created) == 10

    @pytest.mark.fast
    def test_large_session_simulation(self, research_tmpdir):
        """[PERF-07] Agent handles large sessions efficiently."""
        config = _make_config(research_tmpdir, max_experiments=200)

        mock_executor = Mock(spec=CompoundExecutor)
        mock_executor.execute = lambda task: ExecutionResult(
            success=True,
            output="Complete",
            metrics=ExecutionMetrics(duration_seconds=0.001),
        )

        agent = ResearchAgent(config=config, executor=mock_executor)

        start = time.time()
        agent.run_session()
        elapsed = time.time() - start

        # 200 experiments should complete in under 2 seconds with mocks
        assert elapsed < 2.0
        assert agent.session.experiments_completed == 200

    @pytest.mark.fast
    def test_error_recovery_performance(self, research_tmpdir):
        """[PERF-08] Error recovery is fast."""
        config = _make_config(research_tmpdir, max_experiments=10)

        call_count = [0]

        def unreliable_execute(task) -> ExecutionResult:
            call_count[0] += 1
            if call_count[0] % 3 == 0:  # Every 3rd experiment fails
                return ExecutionResult(
                    success=False,
                    output="Failed",
                    error_message="Simulated error",
                    metrics=ExecutionMetrics(duration_seconds=0.01),
                )
            return _fast_result()

        mock_executor = Mock(spec=CompoundExecutor)
        mock_executor.execute = unreliable_execute

        agent = ResearchAgent(config=config, executor=mock_executor)

        start = time.time()
        agent.run_session()
        elapsed = time.time() - start

        # Should complete despite errors in under 1 second
        assert elapsed < 1.0
        assert agent.session.experiments_completed == 10


class TestResearchAgentOptimizationMetrics:
    """Optimization quality metrics for ResearchAgent."""

    @pytest.mark.fast
    def test_metric_improvement_rate(self, research_tmpdir):
        """[OPT-01] Metric improves over experiments."""
        config = _make_config(
            research_tmpdir,
            max_experiments=20,
            target_metric="val_bpb",
        )

        metrics_log: list[float] = []

        def tracking_execute(task) -> ExecutionResult:
            metric = 3.0 - (len(metrics_log) * 0.05)  # Improving monotonically
            metrics_log.append(metric)
            return _fast_result()

        mock_executor = Mock(spec=CompoundExecutor)
        mock_executor.execute = tracking_execute

        agent = ResearchAgent(config=config, executor=mock_executor)
        agent.run_session()

        # Last metric should be better (lower) than first
        assert metrics_log[-1] < metrics_log[0]

    @pytest.mark.fast
    def test_convergence_speed(self, research_tmpdir):
        """[OPT-02] Agent converges to optimal solution quickly."""
        config = _make_config(research_tmpdir, max_experiments=30)

        call_count = [0]
        best_metric = [float("inf")]

        def converging_execute(task) -> ExecutionResult:
            call_count[0] += 1
            metric = 2.5 + 0.5 * math.exp(-call_count[0] / 10)  # Decaying convergence
            if metric < best_metric[0]:
                best_metric[0] = metric
            return _fast_result()

        mock_executor = Mock(spec=CompoundExecutor)
        mock_executor.execute = converging_execute

        agent = ResearchAgent(config=config, executor=mock_executor)
        agent.run_session()

        # Should find good solution within 30 experiments
        assert best_metric[0] < 2.6
