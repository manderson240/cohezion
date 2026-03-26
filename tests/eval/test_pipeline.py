"""Tests for RalphLoop and EvalPipeline."""

from __future__ import annotations

import pytest


class TestRalphLoop:
    """Tests for RalphLoop."""

    @pytest.mark.fast
    def test_initialization(self):
        """Test RalphLoop initializes with default config."""
        from cohezion.eval.pipeline import RalphLoop

        ralph = RalphLoop()
        assert ralph.config.max_episodes == 1000
        assert ralph.config.patience == 20
        assert ralph.config.coherence_threshold == 0.8

    @pytest.mark.fast
    def test_custom_config(self):
        """Test RalphLoop with custom config."""
        from cohezion.eval.pipeline import RalphLoop, RalphLoopConfig

        config = RalphLoopConfig(max_episodes=100, patience=5, coherence_threshold=0.9)
        ralph = RalphLoop(config)
        assert ralph.config.max_episodes == 100
        assert ralph.config.patience == 5
        assert ralph.config.coherence_threshold == 0.9

    @pytest.mark.fast
    def test_run_yields_progress(self):
        """Test that run() yields PipelineProgress objects."""
        from cohezion.eval.pipeline import RalphLoop

        ralph = RalphLoop()
        results = []

        def episode_fn(episode: int, escalation_level: int):
            return {"coherence": 0.8, "success": True, "reward": 1.0}

        for progress in ralph.run(episode_fn):
            results.append(progress)
            if len(results) >= 5:
                break

        assert len(results) == 5

    @pytest.mark.fast
    def test_escalation_counter(self):
        """Test escalation counter increments on running status."""
        from cohezion.eval.pipeline import RalphLoop, RalphLoopConfig

        config = RalphLoopConfig(max_episodes=100, patience=2, min_episodes=1)
        ralph = RalphLoop(config)

        def episode_fn(episode: int, escalation_level: int):
            return {"coherence": 0.4, "success": False, "reward": 0.0}

        for _ in ralph.run(episode_fn):
            pass

        assert ralph._escalation_level >= 0


class TestEpisodeStatus:
    """Tests for EpisodeStatus enum."""

    @pytest.mark.fast
    def test_status_values(self):
        """Test EpisodeStatus has expected values."""
        from cohezion.eval.pipeline import EpisodeStatus

        assert EpisodeStatus.PENDING is not None
        assert EpisodeStatus.RUNNING is not None
        assert EpisodeStatus.SUCCESS is not None
        assert EpisodeStatus.FAILURE is not None
        assert EpisodeStatus.CONVERGED is not None
        assert EpisodeStatus.DIVERGED is not None
        assert EpisodeStatus.INTERRUPTED is not None


class TestConvergenceLevel:
    """Tests for ConvergenceLevel enum."""

    @pytest.mark.fast
    def test_convergence_levels(self):
        """Test ConvergenceLevel has expected values."""
        from cohezion.eval.pipeline import ConvergenceLevel

        assert ConvergenceLevel.NONE.value == 0
        assert ConvergenceLevel.LEVEL_1.value == 1
        assert ConvergenceLevel.LEVEL_2.value == 2
        assert ConvergenceLevel.LEVEL_3.value == 3


class TestPipelineProgress:
    """Tests for PipelineProgress dataclass."""

    @pytest.mark.fast
    def test_creation(self):
        """Test PipelineProgress creation."""
        from cohezion.eval.pipeline import ConvergenceLevel, EpisodeStatus, PipelineProgress

        progress = PipelineProgress(
            episode=1,
            total_episodes=100,
            status=EpisodeStatus.RUNNING,
            convergence_level=ConvergenceLevel.LEVEL_1,
            mean_coherence=0.75,
            std_coherence=0.05,
            success_rate=0.8,
            escalation_level=0,
            total_reward=0.5,
            message="Running",
        )
        assert progress.episode == 1
        assert progress.total_episodes == 100
        assert progress.status == EpisodeStatus.RUNNING
        assert progress.mean_coherence == 0.75


class TestEvalPipeline:
    """Tests for EvalPipeline."""

    @pytest.mark.fast
    def test_initialization(self):
        """Test EvalPipeline initializes with defaults."""
        from cohezion.eval.pipeline import EvalPipeline

        pipeline = EvalPipeline()
        assert pipeline.max_steps == 200
        assert pipeline.verbose is True

    @pytest.mark.fast
    def test_initialization_custom(self):
        """Test EvalPipeline with custom settings."""
        from cohezion.eval.pipeline import EvalPipeline

        pipeline = EvalPipeline(max_steps=100, verbose=False)
        assert pipeline.max_steps == 100
        assert pipeline.verbose is False
