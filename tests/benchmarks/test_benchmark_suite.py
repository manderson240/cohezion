"""Tests for BenchmarkSuite and BenchmarkTask classes."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class TestBenchmarkSuite:
    """Tests for BenchmarkSuite."""

    @pytest.mark.fast
    def test_initialization(self):
        """Test BenchmarkSuite initializes with default tasks."""
        from cohezion.benchmarks.benchmark_suite import BenchmarkSuite

        suite = BenchmarkSuite()
        assert len(suite._tasks) == 15

    @pytest.mark.fast
    def test_run_empty_tasks(self):
        """Test run with empty task list."""
        from cohezion.benchmarks.benchmark_suite import BenchmarkSuite

        suite = BenchmarkSuite()
        mock_policy = MagicMock()
        mock_policy.get_action.return_value = (MagicMock(), 0.0, 0.0)
        results = suite.run(mock_policy, tasks=[], num_episodes=1)
        assert results == {}

    @pytest.mark.fast
    def test_run_unknown_task(self):
        """Test run with unknown task name."""
        from cohezion.benchmarks.benchmark_suite import BenchmarkSuite

        suite = BenchmarkSuite()
        mock_policy = MagicMock()
        mock_policy.get_action.return_value = (MagicMock(), 0.0, 0.0)
        results = suite.run(mock_policy, tasks=["nonexistent/task"], num_episodes=1)
        assert "nonexistent/task" not in results

    @pytest.mark.fast
    def test_register_task(self):
        """Test registering a custom task."""
        from cohezion.benchmarks.benchmark_suite import BenchmarkSuite, BenchmarkTask

        suite = BenchmarkSuite()

        class CustomTask(BenchmarkTask):
            name = "custom/task"
            difficulty = "easy"
            archetype = "CUSTOM"

            def is_success(self, env, evo):
                return True

        suite.register_task("custom/task", CustomTask)
        assert "custom/task" in suite._tasks

    @pytest.mark.fast
    def test_format_results(self):
        """Test format_results returns a string."""
        from cohezion.benchmarks.benchmark_suite import BenchmarkResult, BenchmarkSuite

        suite = BenchmarkSuite()
        mock_result = BenchmarkResult(
            task_name="test/task",
            num_episodes=10,
            mean_reward=1.0,
            std_reward=0.1,
            mean_coherence=0.8,
            success_rate=0.9,
            mean_steps=50.0,
            total_duration_seconds=10.0,
            per_episode=[],
            aggregate_metrics={},
        )
        output = suite.format_results({"test/task": mock_result})
        assert isinstance(output, str)
        assert "test/task" in output


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    @pytest.mark.fast
    def test_creation(self):
        """Test TaskResult creation."""
        from cohezion.benchmarks.benchmark_suite import TaskResult

        result = TaskResult(
            task_name="test",
            episode_id="ep1",
            episode_reward=1.0,
            mean_coherence=0.8,
            final_coherence=0.85,
            steps=100,
            success=True,
            duration_seconds=10.0,
            metrics={},
            biography=[],
        )
        assert result.task_name == "test"
        assert result.episode_id == "ep1"
        assert result.success is True

    @pytest.mark.fast
    def test_to_dict_without_biography(self):
        """Test to_dict without biography."""
        from cohezion.benchmarks.benchmark_suite import TaskResult

        result = TaskResult(
            task_name="test",
            episode_id="ep1",
            episode_reward=1.0,
            mean_coherence=0.8,
            final_coherence=0.85,
            steps=100,
            success=True,
            duration_seconds=10.0,
            metrics={},
            biography=[{"coherence": 0.8}],
        )
        d = result.to_dict(include_biography=False)
        assert "biography" not in d

    @pytest.mark.fast
    def test_to_dict_with_biography(self):
        """Test to_dict with biography."""
        from cohezion.benchmarks.benchmark_suite import TaskResult

        result = TaskResult(
            task_name="test",
            episode_id="ep1",
            episode_reward=1.0,
            mean_coherence=0.8,
            final_coherence=0.85,
            steps=100,
            success=True,
            duration_seconds=10.0,
            metrics={},
            biography=[{"coherence": 0.8}],
        )
        d = result.to_dict(include_biography=True)
        assert "biography" in d
        assert len(d["biography"]) == 1


class TestBenchmarkTask:
    """Tests for BenchmarkTask base class."""

    @pytest.mark.fast
    def test_before_episode_default(self):
        """Test before_episode has default implementation."""
        from cohezion.benchmarks.benchmark_suite import BenchmarkTask

        class DummyTask(BenchmarkTask):
            name = "dummy"
            difficulty = "easy"
            archetype = "DUMMY"

            def is_success(self, env, evo):
                return False

        task = DummyTask()
        mock_env = MagicMock()
        task.before_episode(mock_env)

    @pytest.mark.fast
    def test_after_episode_default(self):
        """Test after_episode returns empty dict."""
        from cohezion.benchmarks.benchmark_suite import BenchmarkTask

        class DummyTask(BenchmarkTask):
            name = "dummy"
            difficulty = "easy"
            archetype = "DUMMY"

            def is_success(self, env, evo):
                return False

        task = DummyTask()
        result = task.after_episode(MagicMock(), MagicMock())
        assert result == {}


class TestBenchmarkTasks:
    """Tests for specific benchmark task implementations."""

    @pytest.mark.fast
    def test_hiho_basin_easy_success(self):
        """Test HIHOBasinEasy success criteria with evo mock only."""
        from unittest.mock import MagicMock

        from cohezion.benchmarks.benchmark_suite import HIHOBasinEasy

        task = HIHOBasinEasy()
        mock_evo = MagicMock()
        mock_evo.coherence_amplitude = 0.75
        mock_evo.doer_state = [0.5]
        result = task.is_success(MagicMock(), mock_evo)
        assert result is True

    @pytest.mark.fast
    def test_hiho_basin_easy_failure(self):
        """Test HIHOBasinEasy failure when coherence too low."""
        from cohezion.benchmarks.benchmark_suite import HIHOBasinEasy

        task = HIHOBasinEasy()
        mock_env = MagicMock()
        mock_evo = MagicMock()
        mock_evo.coherence_amplitude = 0.5
        assert task.is_success(mock_env, mock_evo) is False

    @pytest.mark.fast
    def test_triune_balance_easy(self):
        """Test TRIUNEBalanceEasy success criteria."""
        from cohezion.benchmarks.benchmark_suite import TRIUNEBalanceEasy

        task = TRIUNEBalanceEasy()
        mock_evo = MagicMock()
        mock_evo.doer_state = MagicMock()
        mock_evo.doer_state.__float__ = MagicMock(return_value=0.5)
        mock_evo.doer_state.__getitem__ = MagicMock(side_effect=lambda i: 0.5)
        mock_evo.thinker_state.__getitem__ = MagicMock(side_effect=lambda i: 0.5)
        mock_evo.knower_state.__getitem__ = MagicMock(side_effect=lambda i: 0.5)
        result = task.is_success(MagicMock(), mock_evo)
        assert isinstance(result, bool)

    @pytest.mark.fast
    def test_exotic_charge_easy(self):
        """Test ExoticChargeEasy success criteria."""
        from cohezion.benchmarks.benchmark_suite import ExoticChargeEasy

        task = ExoticChargeEasy()
        mock_evo = MagicMock()
        mock_evo.exotic_charge_density = 0.85
        assert task.is_success(MagicMock(), mock_evo) is True

    @pytest.mark.fast
    def test_exotic_charge_easy_failure(self):
        """Test ExoticChargeEasy failure."""
        from cohezion.benchmarks.benchmark_suite import ExoticChargeEasy

        task = ExoticChargeEasy()
        mock_evo = MagicMock()
        mock_evo.exotic_charge_density = 0.5
        assert task.is_success(MagicMock(), mock_evo) is False

    @pytest.mark.fast
    def test_kordylewski_orbit_easy(self):
        """Test KordylewskiOrbitEasy success criteria."""
        from cohezion.benchmarks.benchmark_suite import KordylewskiOrbitEasy

        task = KordylewskiOrbitEasy()
        mock_env = MagicMock()
        mock_evo = MagicMock()
        result = task.is_success(mock_env, mock_evo)
        assert isinstance(result, bool)

    @pytest.mark.fast
    def test_interruption_recovery_easy(self):
        """Test InterruptionRecoveryEasy success criteria."""
        from cohezion.benchmarks.benchmark_suite import InterruptionRecoveryEasy

        task = InterruptionRecoveryEasy()
        mock_evo = MagicMock()
        mock_evo.coherence_amplitude = 0.65
        assert task.is_success(MagicMock(), mock_evo) is True
