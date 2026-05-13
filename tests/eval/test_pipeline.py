"""Tests for EvalPipeline and RalphLoop."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cohezion.eval.pipeline import (
    EpisodeResult,
    EpisodeStatus,
    EvalPipeline,
    PipelineProgress,
    RalphLoop,
)


class TestRalphLoop:
    """Tests for RalphLoop."""

    @pytest.mark.fast
    def test_check_done_with_done(self):
        """Test DONE keyword detection."""
        ralph = RalphLoop(done_keyword="DONE")
        assert ralph.check_done("Task completed successfully DONE")
        assert ralph.check_done("DONE")
        assert ralph.check_done("done")
        assert ralph.check_done("Done")
        assert not ralph.check_done("Task incomplete")
        assert not ralph.check_done("")

    @pytest.mark.fast
    def test_record_failure_increments_counter(self):
        """Test failure recording."""
        ralph = RalphLoop(escalation_threshold=3)
        assert ralph.consecutive_failures == 0
        ralph.record_failure()
        assert ralph.consecutive_failures == 1
        ralph.record_failure()
        assert ralph.consecutive_failures == 2

    @pytest.mark.fast
    def test_record_success_resets_counter(self):
        """Test success resets failure counter."""
        ralph = RalphLoop(escalation_threshold=3)
        ralph.record_failure()
        ralph.record_failure()
        assert ralph.consecutive_failures == 2
        ralph.record_success()
        assert ralph.consecutive_failures == 0

    @pytest.mark.fast
    def test_escalate_increases_difficulty(self):
        """Test escalation increases difficulty."""
        ralph = RalphLoop(escalation_threshold=3, escalation_factor=2.0)
        ralph.current_difficulty = 2
        initial = ralph.current_difficulty
        new_level = ralph.escalate()
        assert new_level == initial * 2
        assert ralph.current_difficulty == 4

    @pytest.mark.fast
    def test_escalate_resets_failure_counter(self):
        """Test escalation resets failure counter."""
        ralph = RalphLoop(escalation_threshold=3, escalation_factor=1.5)
        ralph.record_failure()
        ralph.record_failure()
        assert ralph.consecutive_failures == 2
        ralph.escalate()
        assert ralph.consecutive_failures == 0

    @pytest.mark.fast
    def test_escalate_caps_at_max(self):
        """Test escalation caps at 10."""
        ralph = RalphLoop(escalation_threshold=3, escalation_factor=2.0)
        ralph.current_difficulty = 9
        new_level = ralph.escalate()
        assert new_level == 10
        assert ralph.current_difficulty == 10

    @pytest.mark.fast
    def test_should_continue(self):
        """Test should_continue logic."""
        ralph = RalphLoop(max_iterations=20)
        assert ralph.should_continue(0)
        assert ralph.should_continue(19)
        assert not ralph.should_continue(20)
        assert not ralph.should_continue(100)

    @pytest.mark.fast
    def test_get_config_returns_current_settings(self):
        """Test config retrieval."""
        ralph = RalphLoop(
            done_keyword="SUCCESS",
            max_iterations=30,
            escalation_threshold=5,
            escalation_factor=2.0,
        )
        config = ralph.get_config()
        assert config.done_keyword == "SUCCESS"
        assert config.max_iterations == 30
        assert config.escalation_threshold == 5
        assert config.escalation_factor == 2.0


class TestEpisodeResult:
    """Tests for EpisodeResult dataclass."""

    @pytest.mark.fast
    def test_episode_result_creation(self):
        """Test EpisodeResult creation."""
        result = EpisodeResult(
            episode_id="test_1",
            status=EpisodeStatus.SUCCESS,
            task_spec=MagicMock(),
            duration_seconds=1.5,
            iterations=5,
        )
        assert result.episode_id == "test_1"
        assert result.status == EpisodeStatus.SUCCESS
        assert result.duration_seconds == 1.5
        assert result.iterations == 5
        assert result.error is None
        assert result.escalation_level == 0


class TestPipelineProgress:
    """Tests for PipelineProgress dataclass."""

    @pytest.mark.fast
    def test_progress_initialization(self):
        """Test PipelineProgress defaults."""
        progress = PipelineProgress()
        assert progress.total_episodes == 0
        assert progress.successful_episodes == 0
        assert progress.failed_episodes == 0
        assert progress.escalated_episodes == 0
        assert progress.current_difficulty == 1
        assert progress.consecutive_failures == 0
        assert progress.total_iterations == 0


class TestEvalPipeline:
    """Tests for EvalPipeline."""

    @pytest.fixture
    def mock_isolation_manager(self):
        """Create mock isolation manager."""
        manager = MagicMock()
        manager.setup_filesystem = MagicMock(return_value=MagicMock())
        manager.cleanup = MagicMock(return_value=MagicMock(success=True))
        return manager

    @pytest.fixture
    def temp_progress_path(self, tmp_path):
        """Create temporary progress path."""
        return tmp_path / "EVAL_PROGRESS.md"

    @pytest.fixture
    def mock_task_spec(self):
        """Create mock task spec."""
        spec = MagicMock()
        spec.archetype = "interruption_recovery"
        spec.horizon = 100
        spec.difficulty = 1
        return spec

    @pytest.mark.fast
    def test_run_single_episode_success(self, mock_isolation_manager, temp_progress_path, mock_task_spec):
        """Test successful episode execution."""
        pipeline = EvalPipeline(
            isolation_manager=mock_isolation_manager,
            progress_path=temp_progress_path,
            git_auto_commit=False,
        )

        mock_env = MagicMock()
        mock_env.reset.return_value = ({"evo_state": {"coherence": 0.95}}, {})
        mock_env.step.return_value = (
            {"evo_state": {"coherence": 0.95}},
            0.95,
            True,
            False,
            {},
        )

        with patch("cohezion.rl.environment.FlumeNavEnv", return_value=mock_env):
            results = pipeline.run(task_spec=mock_task_spec, n_episodes=1)

        assert len(results) == 1
        assert results[0].status == EpisodeStatus.SUCCESS

    @pytest.mark.fast
    def test_run_updates_progress(self, mock_isolation_manager, temp_progress_path, mock_task_spec):
        """Test that run updates progress."""
        pipeline = EvalPipeline(
            isolation_manager=mock_isolation_manager,
            progress_path=temp_progress_path,
            git_auto_commit=False,
        )

        mock_env = MagicMock()
        mock_env.reset.return_value = ({"evo_state": {"coherence": 0.95}}, {})
        mock_env.step.return_value = (
            {"evo_state": {"coherence": 0.95}},
            0.95,
            True,
            False,
            {},
        )

        with patch("cohezion.rl.environment.FlumeNavEnv", return_value=mock_env):
            pipeline.run(task_spec=mock_task_spec, n_episodes=1)

        assert pipeline.progress.total_episodes == 1
        assert pipeline.progress.successful_episodes == 1

    @pytest.mark.fast
    def test_success_rate_calculation(self, mock_isolation_manager, temp_progress_path):
        """Test success rate calculation."""
        pipeline = EvalPipeline(
            isolation_manager=mock_isolation_manager,
            progress_path=temp_progress_path,
            git_auto_commit=False,
        )

        assert pipeline._success_rate() == 0.0

        pipeline.progress.total_episodes = 4
        pipeline.progress.successful_episodes = 2
        assert pipeline._success_rate() == 0.5

        pipeline.progress.successful_episodes = 4
        assert pipeline._success_rate() == 1.0

    @pytest.mark.fast
    def test_write_progress_creates_file(self, mock_isolation_manager, temp_progress_path):
        """Test progress file creation."""
        pipeline = EvalPipeline(
            isolation_manager=mock_isolation_manager,
            progress_path=temp_progress_path,
            git_auto_commit=False,
        )

        pipeline._write_progress()

        assert temp_progress_path.exists()
        content = temp_progress_path.read_text()
        assert "EVAL_PROGRESS.md" in content
        assert "Summary" in content
        assert "Total Episodes" in content

    @pytest.mark.fast
    def test_get_progress_returns_current_state(self, mock_isolation_manager, temp_progress_path):
        """Test progress retrieval."""
        pipeline = EvalPipeline(
            isolation_manager=mock_isolation_manager,
            progress_path=temp_progress_path,
            git_auto_commit=False,
        )

        progress = pipeline.get_progress()

        assert isinstance(progress, PipelineProgress)
        assert progress.total_episodes == 0


class TestRalphLoopIntegration:
    """Integration tests for RalphLoop pattern."""

    @pytest.mark.fast
    def test_full_iteration_cycle(self):
        """Test complete iteration cycle with failures and escalation."""
        ralph = RalphLoop(
            done_keyword="DONE",
            max_iterations=10,
            escalation_threshold=3,
            escalation_factor=2.0,
        )

        assert ralph.should_continue(0)

        ralph.record_failure()
        assert ralph.consecutive_failures == 1

        ralph.record_failure()
        assert ralph.consecutive_failures == 2

        ralph.record_failure()
        assert ralph.consecutive_failures == 0
        assert ralph.current_difficulty == 2

    @pytest.mark.fast
    def test_donkey_pattern_success(self):
        """Test RalphLoop terminates on DONE."""
        ralph = RalphLoop(done_keyword="DONE", max_iterations=20)

        outputs = [
            "Working...",
            "Still going...",
            "Almost there...",
            "Task completed successfully DONE",
        ]

        for _i, output in enumerate(outputs):
            if ralph.check_done(output):
                ralph.record_success()
                break
            ralph.record_failure()
        else:
            pytest.fail("RalphLoop did not detect DONE")

        assert ralph.consecutive_failures == 0
