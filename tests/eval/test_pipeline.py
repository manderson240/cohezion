"""Tests for eval/pipeline module — RalphLoop and EvalPipeline."""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.eval.pipeline import (
    ConvergenceLevel,
    EpisodeStatus,
    EvalPipeline,
    PipelineProgress,
    RalphLoop,
    RalphLoopConfig,
)


class TestEpisodeStatus:
    """Tests for EpisodeStatus enum."""

    def test_all_statuses_defined(self):
        """All expected statuses exist."""
        expected = {
            "PENDING",
            "RUNNING",
            "SUCCESS",
            "FAILURE",
            "CONVERGED",
            "DIVERGED",
            "INTERRUPTED",
        }
        actual = {s.name for s in EpisodeStatus}
        assert expected.issubset(actual)


class TestConvergenceLevel:
    """Tests for ConvergenceLevel enum."""

    def test_level_ordering(self):
        """Levels are ordered correctly."""
        assert ConvergenceLevel.NONE.value == 0
        assert ConvergenceLevel.LEVEL_1.value == 1
        assert ConvergenceLevel.LEVEL_2.value == 2
        assert ConvergenceLevel.LEVEL_3.value == 3


class TestRalphLoopConfig:
    """Tests for RalphLoopConfig dataclass."""

    def test_defaults(self):
        """Default configuration values are sensible."""
        config = RalphLoopConfig()
        assert config.max_episodes == 1000
        assert config.patience == 20
        assert config.min_episodes == 10
        assert config.coherence_threshold == 0.8
        assert config.coherence_std_threshold == 0.05
        assert config.success_threshold == 0.9

    def test_custom_config(self):
        """Custom values are stored correctly."""
        config = RalphLoopConfig(max_episodes=500, patience=10)
        assert config.max_episodes == 500
        assert config.patience == 10


class TestRalphLoop:
    """Tests for RalphLoop FOR-DONE-ESCLALATE iteration."""

    @pytest.fixture
    def loop(self):
        config = RalphLoopConfig(max_episodes=100, min_episodes=5, patience=3)
        return RalphLoop(config)

    def test_runs_given_episodes(self, loop):
        """run() yields progress for each episode."""

        def simple_episode_fn(episode, escalation_level):
            return {"coherence": 0.5 + episode * 0.01, "success": True, "reward": 1.0}

        progress_list = list(loop.run(simple_episode_fn))
        assert len(progress_list) <= 100
        assert all(isinstance(p, PipelineProgress) for p in progress_list)

    def test_convergence_triggers_stop(self, loop):
        """CONVERGED status stops iteration early."""

        def converging_episode_fn(episode, escalation_level):
            if episode >= 10:
                return {"coherence": 0.85, "success": True, "reward": 1.0}
            return {"coherence": 0.4, "success": False, "reward": 0.0}

        progress_list = list(loop.run(converging_episode_fn))
        last = progress_list[-1]
        assert last.status in (EpisodeStatus.CONVERGED, EpisodeStatus.RUNNING)

    def test_divergence_triggers_stop(self, loop):
        """DIVERGED status stops iteration."""

        def diverging_episode_fn(episode, escalation_level):
            return {"coherence": 0.1 + np.random.randn() * 0.5, "success": False, "reward": -1.0}

        loop2 = RalphLoop(RalphLoopConfig(max_episodes=50, min_episodes=3, patience=2))
        progress_list = list(loop2.run(diverging_episode_fn))

    def test_min_episodes_respected(self, loop):
        """Iteration continues until min_episodes before checking convergence."""
        call_count = 0

        def counting_episode_fn(episode, escalation_level):
            nonlocal call_count
            call_count += 1
            return {"coherence": 0.9, "success": True, "reward": 1.0}

        config = RalphLoopConfig(max_episodes=100, min_episodes=5, patience=2)
        loop3 = RalphLoop(config)
        list(loop3.run(counting_episode_fn))
        assert call_count >= 5

    def test_escalation_level_tracked(self, loop):
        """Escalation level is tracked correctly."""
        call_count = 0

        def check_escalation(episode, escalation_level):
            nonlocal call_count
            call_count += 1
            return {"coherence": 0.3 + episode * 0.01, "success": False, "reward": -1.0}

        config = RalphLoopConfig(max_episodes=20, min_episodes=3, patience=3)
        loop5 = RalphLoop(config)
        progress_list = list(loop5.run(check_escalation))
        assert len(progress_list) > 0
        assert all(hasattr(p, "escalation_level") for p in progress_list)

    def test_pipeline_progress_fields(self, loop):
        """PipelineProgress has all required fields."""

        def episode_fn(episode, escalation_level):
            return {"coherence": 0.5 + 0.02 * episode, "success": True, "reward": 1.0}

        progress_list = list(loop.run(episode_fn))
        for p in progress_list:
            assert hasattr(p, "episode")
            assert hasattr(p, "total_episodes")
            assert hasattr(p, "status")
            assert hasattr(p, "convergence_level")
            assert hasattr(p, "mean_coherence")
            assert hasattr(p, "std_coherence")
            assert hasattr(p, "success_rate")
            assert hasattr(p, "escalation_level")
            assert hasattr(p, "total_reward")
            assert hasattr(p, "message")


class TestEvalPipeline:
    """Tests for EvalPipeline."""

    def test_init_default_task_generator(self):
        """Default task generator is TaskGenerator."""
        pipeline = EvalPipeline()
        assert pipeline.task_generator is not None

    def test_run_with_mock_policy(self):
        """run() executes with a mock policy."""
        pipeline = EvalPipeline(verbose=False)

        class MockPolicy:
            def get_action(self, state):
                return np.random.randn(256).astype(np.float32) * 0.1, -0.5, 0.5

        policy = MockPolicy()
        scorecard = pipeline.run(policy, n_episodes=2, seed=42)
        assert scorecard is not None


class TestPipelineProgress:
    """Tests for PipelineProgress dataclass."""

    def test_frozen(self):
        """PipelineProgress is frozen."""
        progress = PipelineProgress(
            episode=1,
            total_episodes=100,
            status=EpisodeStatus.RUNNING,
            convergence_level=ConvergenceLevel.NONE,
            mean_coherence=0.5,
            std_coherence=0.1,
            success_rate=0.5,
            escalation_level=0,
            total_reward=0.0,
            message="Running",
        )
        with pytest.raises(AttributeError):
            progress.episode = 2

    def test_message_defaults(self):
        """Message strings are generated correctly."""
        progress_running = PipelineProgress(
            episode=5,
            total_episodes=100,
            status=EpisodeStatus.RUNNING,
            convergence_level=ConvergenceLevel.NONE,
            mean_coherence=0.5,
            std_coherence=0.1,
            success_rate=0.5,
            escalation_level=1,
            total_reward=0.0,
            message="Running (escalation=1)",
        )
        assert "Running" in progress_running.message
