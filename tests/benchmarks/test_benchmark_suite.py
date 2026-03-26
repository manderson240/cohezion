"""Tests for benchmark_suite module — LM Evaluation Harness-style benchmark suite."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from cohezion.benchmarks.benchmark_suite import (
    BenchmarkResult,
    BenchmarkSuite,
    BenchmarkTask,
    HIHOBasinEasy,
    TaskResult,
    TRIUNEBalanceEasy,
)


class MockPolicy:
    """Mock policy for testing."""

    def __init__(self, coherence: float = 0.75):
        self.coherence = coherence
        self._call_count = 0

    def get_action(self, state: np.ndarray):
        self._call_count += 1
        action = np.random.randn(256).astype(np.float32) * 0.1
        return action, -0.5, 0.5


class TestBenchmarkTask:
    """Tests for BenchmarkTask abstract base class."""

    def test_is_success_abstract_method(self):
        """BenchmarkTask.is_success is abstract and must be implemented."""
        task = HIHOBasinEasy()
        assert callable(task.is_success)

    def test_default_max_steps(self):
        """Default max_steps is 200 on concrete subclass."""
        task = HIHOBasinEasy()
        assert task.max_steps == 200


class TestHIHOBasinEasy:
    """Tests for HIHO Basin Easy task."""

    def test_is_success_high_coherence(self):
        """High coherence + close HIHO distance = success."""
        task = HIHOBasinEasy()
        task._final_state = np.array([0.51] * 256, dtype=np.float32)
        mock_evo = MagicMock()
        mock_evo.coherence = 0.8

        assert task.is_success(task, mock_evo)

    def test_is_success_low_coherence(self):
        """Low coherence = failure."""
        task = HIHOBasinEasy()
        task._final_state = np.array([0.5] * 256, dtype=np.float32)
        mock_evo = MagicMock()
        mock_evo.coherence = 0.4

        assert not task.is_success(task, mock_evo)


class TestTRIUNEBalanceEasy:
    """Tests for TRIUNE Balance Easy task."""

    def test_is_success_balanced(self):
        """Balanced weights = success."""
        task = TRIUNEBalanceEasy()
        mock_env = MagicMock()
        mock_evo = MagicMock()
        mock_evo.doer_weight = 0.35
        mock_evo.thinker_weight = 0.32
        mock_evo.knower_weight = 0.33

        assert task.is_success(mock_env, mock_evo)

    def test_is_success_imbalanced(self):
        """Imbalanced weights = failure."""
        task = TRIUNEBalanceEasy()
        mock_env = MagicMock()
        mock_evo = MagicMock()
        mock_evo.doer_weight = 0.8
        mock_evo.thinker_weight = 0.1
        mock_evo.knower_weight = 0.1

        assert not task.is_success(mock_env, mock_evo)


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    def test_to_dict_without_biography(self):
        """to_dict excludes biography by default."""
        result = TaskResult(
            task_name="test",
            episode_id="123",
            episode_reward=1.5,
            mean_coherence=0.75,
            final_coherence=0.8,
            steps=100,
            success=True,
            duration_seconds=2.5,
            metrics={"coherence": {"mean": 0.75}},
            biography=[{"step": 1}],
        )
        d = result.to_dict(include_biography=False)
        assert "biography" not in d
        assert d["task_name"] == "test"
        assert d["episode_reward"] == 1.5

    def test_to_dict_with_biography(self):
        """to_dict includes biography when requested."""
        result = TaskResult(
            task_name="test",
            episode_id="123",
            episode_reward=1.5,
            mean_coherence=0.75,
            final_coherence=0.8,
            steps=100,
            success=True,
            duration_seconds=2.5,
            metrics={},
            biography=[{"step": 1}, {"step": 2}],
        )
        d = result.to_dict(include_biography=True)
        assert "biography" in d
        assert len(d["biography"]) == 2


class TestBenchmarkSuite:
    """Tests for BenchmarkSuite."""

    @pytest.fixture
    def suite(self):
        return BenchmarkSuite()

    def test_register_task(self, suite):
        """register_task adds task to registry."""

        class CustomTask(BenchmarkTask):
            name = "custom/test"
            archetype = "HIHO_BASIN"

            def is_success(self, env, evo):
                return evo.coherence > 0.9

        suite.register_task("custom/test", CustomTask)
        assert "custom/test" in suite._tasks

    def test_register_default_tasks(self, suite):
        """Default tasks are registered on init."""
        assert len(suite._tasks) >= 15
        assert "cohezion/hiho_basin_easy" in suite._tasks

    def test_format_results(self, suite):
        """format_results produces non-empty string."""
        result = BenchmarkResult(
            task_name="cohezion/hiho_basin_easy",
            num_episodes=10,
            mean_reward=1.2,
            std_reward=0.3,
            mean_coherence=0.75,
            success_rate=0.8,
            mean_steps=150.0,
            total_duration_seconds=30.0,
            per_episode=[],
            aggregate_metrics={},
        )
        output = suite.format_results({"cohezion/hiho_basin_easy": result})
        assert "FLUME EVO PHYSICS BENCHMARK" in output
        assert "cohezion/hiho_basin_easy" in output

    def test_aggregate_metrics(self, suite):
        """_aggregate_metrics computes correct statistics."""
        biographies = [
            [
                {
                    "coherence": 0.5,
                    "doer_weight": 0.33,
                    "thinker_weight": 0.33,
                    "knower_weight": 0.34,
                    "exotic_charge_density": 0.1,
                    "phase": 0.0,
                },
                {
                    "coherence": 0.6,
                    "doer_weight": 0.34,
                    "thinker_weight": 0.33,
                    "knower_weight": 0.33,
                    "exotic_charge_density": 0.2,
                    "phase": 0.1,
                },
            ]
        ]
        agg = suite._aggregate_metrics(biographies)
        assert "coherence" in agg
        assert agg["coherence"]["n"] == 2

    def test_aggregate_metrics_empty(self, suite):
        """Empty biographies returns empty dict."""
        agg = suite._aggregate_metrics([])
        assert agg == {}

    def test_run_unknown_task_skipped(self, suite):
        """Unknown tasks are skipped with warning."""
        policy = MockPolicy()
        results = suite.run(policy, tasks=["unknown/task"], num_episodes=2, verbose=False)
        assert "unknown/task" not in results

    def test_run_with_mock_policy(self, suite):
        """run() executes episodes with a mock policy."""
        policy = MockPolicy(coherence=0.8)
        results = suite.run(
            policy,
            tasks=["cohezion/hiho_basin_easy"],
            num_episodes=2,
            verbose=False,
            seed=42,
        )
        assert "cohezion/hiho_basin_easy" in results
        result = results["cohezion/hiho_basin_easy"]
        assert result.num_episodes == 2
        assert isinstance(result.mean_reward, float)

    def test_run_with_output_path(self, suite, tmp_path):
        """run() writes JSONL to output path."""
        policy = MockPolicy()
        results = suite.run(
            policy,
            tasks=["cohezion/hiho_basin_easy"],
            num_episodes=2,
            output_path=tmp_path,
            verbose=False,
            seed=42,
        )
        jsonl_files = list(tmp_path.glob("*.jsonl"))
        assert len(jsonl_files) == 1

    def test_run_respects_max_steps(self, suite):
        """run() respects task max_steps."""
        policy = MockPolicy()
        suite.run(
            policy,
            tasks=["cohezion/hiho_basin_easy"],
            num_episodes=1,
            verbose=False,
            seed=42,
        )

    def test_format_results_empty(self, suite):
        """format_results handles empty results."""
        output = suite.format_results({})
        assert "FLUME EVO PHYSICS BENCHMARK" in output

    def test_benchmark_result_to_dict(self):
        """BenchmarkResult.to_dict is JSON serializable."""
        result = BenchmarkResult(
            task_name="test",
            num_episodes=5,
            mean_reward=1.0,
            std_reward=0.2,
            mean_coherence=0.75,
            success_rate=0.8,
            mean_steps=100.0,
            total_duration_seconds=10.0,
            per_episode=[],
            aggregate_metrics={},
        )
        d = result.to_dict()
        assert d["task_name"] == "test"
        assert d["num_episodes"] == 5
        assert isinstance(d["mean_reward"], float)


class TestBenchmarkSuitePolicyProtocol:
    """Tests for Policy protocol compliance."""

    def test_policy_protocol_get_action(self):
        """Policy must implement get_action returning correct shapes."""
        policy = MockPolicy()
        state = np.random.randn(256).astype(np.float32)
        action, log_prob, value = policy.get_action(state)
        assert action.shape == (256,)
        assert isinstance(log_prob, float)
        assert isinstance(value, float)

    def test_benchmark_suite_run_multiple_tasks(self):
        """run() accepts multiple task names."""
        suite = BenchmarkSuite()
        policy = MockPolicy()
        results = suite.run(
            policy,
            tasks=["cohezion/hiho_basin_easy", "cohezion/triune_balance_easy"],
            num_episodes=2,
            verbose=False,
            seed=42,
        )
        assert len(results) == 2
        assert "cohezion/hiho_basin_easy" in results
        assert "cohezion/triune_balance_easy" in results
