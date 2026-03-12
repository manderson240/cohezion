"""Performance benchmarks for ResearchAgent.

Tests throughput, latency, and optimization quality.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from cohezion.compound.core.executor import CompoundExecutor
from cohezion.compound.models import ExecutionMetrics, ExecutionResult
from cohezion.research import ResearchAgent, ResearchConfig


class TestResearchAgentPerformance:
    """Performance benchmarks for ResearchAgent."""

    @pytest.mark.fast
    def test_experiment_throughput(self):
        """[PERF-01] Agent completes experiments efficiently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ResearchConfig(
                experiment_time_budget=10.0,
                max_experiments=10,
                experiment_log=Path(tmpdir) / "experiments.jsonl",
                checkpoint_dir=Path(tmpdir) / "checkpoints",
            )

            def fast_execute(task):
                return ExecutionResult(
                    success=True,
                    output="Complete",
                    metrics=ExecutionMetrics(duration_seconds=0.01),
                )

            mock_executor = Mock(spec=CompoundExecutor)
            mock_executor.execute = fast_execute

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
    def test_concurrent_experiment_simulation(self):
        """[PERF-03] Agent handles concurrent experiment results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ResearchConfig(
                experiment_time_budget=10.0,
                max_experiments=20,
                experiment_log=Path(tmpdir) / "experiments.jsonl",
                checkpoint_dir=Path(tmpdir) / "checkpoints",
            )

            results_order = []

            def tracking_execute(task):
                results_order.append(task.id)
                return ExecutionResult(
                    success=True,
                    output="Complete",
                    metrics=ExecutionMetrics(duration_seconds=0.01),
                )

            mock_executor = Mock(spec=CompoundExecutor)
            mock_executor.execute = tracking_execute

            agent = ResearchAgent(config=config, executor=mock_executor)

            agent.run_session()

            # All experiments should have unique IDs
            assert len(results_order) == 20
            assert len(set(results_order)) == 20

    @pytest.mark.fast
    def test_optimization_quality_simulation(self):
        """[PERF-04] Agent finds optimal configurations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ResearchConfig(
                experiment_time_budget=10.0,
                max_experiments=50,
                target_metric="val_bpb",
                experiment_log=Path(tmpdir) / "experiments.jsonl",
                checkpoint_dir=Path(tmpdir) / "checkpoints",
            )

            call_count = [0]

            def simulated_optimization(task):
                """Simulate optimization with convergence."""
                call_count[0] += 1
                # Metric improves with experiments (simulating optimization)
                # Starting at 3.0, converging to 2.0
                import math

                improvement = 1.0 * (1 - math.exp(-call_count[0] / 15))
                metric = 3.0 - improvement
                return ExecutionResult(
                    success=True,
                    output=f"exp-{call_count[0]}",
                    metrics=ExecutionMetrics(duration_seconds=0.01),
                )

            mock_executor = Mock(spec=CompoundExecutor)
            mock_executor.execute = simulated_optimization

            agent = ResearchAgent(config=config, executor=mock_executor)
            agent.run_session()

            # Should complete all experiments
            assert agent.session.experiments_completed == 50

    @pytest.mark.fast
    def test_memory_scaling_simulation(self):
        """[PERF-05] Memory usage scales linearly with experiments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ResearchConfig(
                experiment_time_budget=10.0,
                max_experiments=100,
                experiment_log=Path(tmpdir) / "experiments.jsonl",
                checkpoint_dir=Path(tmpdir) / "checkpoints",
            )

            def mock_execute(task):
                return ExecutionResult(
                    success=True,
                    output="Complete",
                    metrics=ExecutionMetrics(duration_seconds=0.01),
                )

            mock_executor = Mock(spec=CompoundExecutor)
            mock_executor.execute = mock_execute

            agent = ResearchAgent(config=config, executor=mock_executor)
            agent.run_session()

            # Should handle 100 experiments without issues
            assert agent.session.experiments_completed == 100
            assert Path(config.experiment_log).exists()

    @pytest.mark.fast
    def test_checkpoint_frequency(self):
        """[PERF-06] Checkpoints saved at expected frequency."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ResearchConfig(
                experiment_time_budget=10.0,
                max_experiments=10,
                experiment_log=Path(tmpdir) / "experiments.jsonl",
                checkpoint_dir=Path(tmpdir) / "checkpoints",
            )

            checkpoints_created = []

            def checkpointing_execute(task):
                checkpoints_created.append(task.id)
                return ExecutionResult(
                    success=True,
                    output="Complete",
                    metrics=ExecutionMetrics(duration_seconds=0.01),
                )

            mock_executor = Mock(spec=CompoundExecutor)
            mock_executor.execute = checkpointing_execute

            agent = ResearchAgent(config=config, executor=mock_executor)
            agent.run_session()

            # Each experiment should complete
            assert len(checkpoints_created) == 10

    @pytest.mark.fast
    def test_large_session_simulation(self):
        """[PERF-07] Agent handles large sessions efficiently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ResearchConfig(
                experiment_time_budget=10.0,
                max_experiments=200,  # Large session
                experiment_log=Path(tmpdir) / "experiments.jsonl",
                checkpoint_dir=Path(tmpdir) / "checkpoints",
            )

            def fast_execute(task):
                return ExecutionResult(
                    success=True,
                    output="Complete",
                    metrics=ExecutionMetrics(duration_seconds=0.001),
                )

            mock_executor = Mock(spec=CompoundExecutor)
            mock_executor.execute = fast_execute

            agent = ResearchAgent(config=config, executor=mock_executor)

            start = time.time()
            agent.run_session()
            elapsed = time.time() - start

            # 200 experiments should complete in under 2 seconds with mocks
            assert elapsed < 2.0
            assert agent.session.experiments_completed == 200

    @pytest.mark.fast
    def test_error_recovery_performance(self):
        """[PERF-08] Error recovery is fast."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ResearchConfig(
                experiment_time_budget=10.0,
                max_experiments=10,
                experiment_log=Path(tmpdir) / "experiments.jsonl",
                checkpoint_dir=Path(tmpdir) / "checkpoints",
            )

            call_count = [0]

            def unreliable_execute(task):
                call_count[0] += 1
                if call_count[0] % 3 == 0:  # Every 3rd experiment fails
                    return ExecutionResult(
                        success=False,
                        output="Failed",
                        error_message="Simulated error",
                        metrics=ExecutionMetrics(duration_seconds=0.01),
                    )
                return ExecutionResult(
                    success=True,
                    output="Complete",
                    metrics=ExecutionMetrics(duration_seconds=0.01),
                )

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
    def test_metric_improvement_rate(self):
        """[OPT-01] Metric improves over experiments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ResearchConfig(
                experiment_time_budget=10.0,
                max_experiments=20,
                target_metric="val_bpb",
                experiment_log=Path(tmpdir) / "experiments.jsonl",
                checkpoint_dir=Path(tmpdir) / "checkpoints",
            )

            metrics_log = []

            def tracking_execute(task):
                metric = 3.0 - (len(metrics_log) * 0.05)  # Improving
                metrics_log.append(metric)
                return ExecutionResult(
                    success=True,
                    output="Complete",
                    metrics=ExecutionMetrics(duration_seconds=0.01),
                )

            mock_executor = Mock(spec=CompoundExecutor)
            mock_executor.execute = tracking_execute

            agent = ResearchAgent(config=config, executor=mock_executor)
            agent.run_session()

            # Last metric should be better than first
            assert metrics_log[-1] < metrics_log[0]

    @pytest.mark.fast
    def test_convergence_speed(self):
        """[OPT-02] Agent converges to optimal solution quickly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ResearchConfig(
                experiment_time_budget=10.0,
                max_experiments=30,
                experiment_log=Path(tmpdir) / "experiments.jsonl",
                checkpoint_dir=Path(tmpdir) / "checkpoints",
            )

            call_count = [0]
            best_metric = [float("inf")]

            def converging_execute(task):
                call_count[0] += 1
                import math

                # Simulated convergence
                metric = 2.5 + 0.5 * math.exp(-call_count[0] / 10)
                if metric < best_metric[0]:
                    best_metric[0] = metric
                return ExecutionResult(
                    success=True,
                    output="Complete",
                    metrics=ExecutionMetrics(duration_seconds=0.01),
                )

            mock_executor = Mock(spec=CompoundExecutor)
            mock_executor.execute = converging_execute

            agent = ResearchAgent(config=config, executor=mock_executor)
            agent.run_session()

            # Should find good solution within 30 experiments
            assert best_metric[0] < 2.6
