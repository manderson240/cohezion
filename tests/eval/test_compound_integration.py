"""Tests for compound_integration module."""

from __future__ import annotations

import pytest


class TestCurriculumState:
    """Tests for CurriculumState enum."""

    @pytest.mark.fast
    def test_curriculum_states(self):
        """Test all curriculum states exist."""
        from cohezion.eval.compound_integration import CurriculumState

        assert CurriculumState.INITIAL is not None
        assert CurriculumState.WARMING is not None
        assert CurriculumState.IMPROVING is not None
        assert CurriculumState.PLATEAUED is not None
        assert CurriculumState.MASTERED is not None


class TestBenchmarkSessionManager:
    """Tests for BenchmarkSessionManager."""

    @pytest.mark.fast
    def test_initialization(self):
        """Test BenchmarkSessionManager initializes."""
        from cohezion.eval.compound_integration import BenchmarkSessionManager

        mgr = BenchmarkSessionManager()
        assert mgr.scorecard is None
        assert mgr.run_history == {}
        assert mgr._current_run_id is None

    @pytest.mark.fast
    def test_start_session(self):
        """Test starting a session."""
        from cohezion.eval.compound_integration import BenchmarkSessionManager

        mgr = BenchmarkSessionManager()
        run_id = mgr.start_session()
        assert run_id is not None
        assert mgr.scorecard is not None
        assert mgr._current_run_id is not None

    @pytest.mark.fast
    def test_start_session_with_id(self):
        """Test starting a session with custom ID."""
        from cohezion.eval.compound_integration import BenchmarkSessionManager

        mgr = BenchmarkSessionManager()
        run_id = mgr.start_session("custom_run_001")
        assert run_id == "custom_run_001"

    @pytest.mark.fast
    def test_record_episode(self):
        """Test recording an episode."""
        from cohezion.eval.compound_integration import BenchmarkSessionManager

        mgr = BenchmarkSessionManager()
        mgr.start_session("test_run")
        mgr.record_episode(
            episode_id=1,
            coherence=0.8,
            reward=1.0,
            success=True,
            biography=[],
        )
        assert mgr.scorecard is not None

    @pytest.mark.fast
    def test_record_episode_without_session(self):
        """Test recording without session raises."""
        from cohezion.eval.compound_integration import BenchmarkSessionManager

        mgr = BenchmarkSessionManager()
        with pytest.raises(RuntimeError, match="Session not started"):
            mgr.record_episode(
                episode_id=1,
                coherence=0.8,
                reward=1.0,
                success=True,
                biography=[],
            )

    @pytest.mark.fast
    def test_end_session(self):
        """Test ending a session."""
        from cohezion.eval.compound_integration import BenchmarkSessionManager

        mgr = BenchmarkSessionManager()
        mgr.start_session("test_run")
        summary = mgr.end_session()
        assert "run_id" in summary
        assert summary["run_id"] == "test_run"
        assert "completed_at" in summary
        assert "report" in summary

    @pytest.mark.fast
    def test_end_session_without_session(self):
        """Test ending without session raises."""
        from cohezion.eval.compound_integration import BenchmarkSessionManager

        mgr = BenchmarkSessionManager()
        with pytest.raises(RuntimeError, match="Session not started"):
            mgr.end_session()


class TestSelfImprovingBenchmarkLoop:
    """Tests for SelfImprovingBenchmarkLoop."""

    @pytest.mark.fast
    def test_initialization(self):
        """Test SelfImprovingBenchmarkLoop initializes."""
        from cohezion.benchmarks.benchmark_suite import BenchmarkSuite
        from cohezion.eval.compound_integration import (
            BenchmarkSessionManager,
            CurriculumState,
            SelfImprovingBenchmarkLoop,
        )

        suite = BenchmarkSuite()
        session_mgr = BenchmarkSessionManager()
        loop = SelfImprovingBenchmarkLoop(suite=suite, session_manager=session_mgr)

        assert loop.suite is suite
        assert loop.session_manager is session_mgr
        assert loop.curriculum_state == CurriculumState.INITIAL
        assert "easy" in loop.difficulty_weights
        assert "medium" in loop.difficulty_weights
        assert "hard" in loop.difficulty_weights

    @pytest.mark.fast
    def test_select_tasks(self):
        """Test task selection based on difficulty weights."""
        from cohezion.benchmarks.benchmark_suite import BenchmarkSuite
        from cohezion.eval.compound_integration import (
            BenchmarkSessionManager,
            SelfImprovingBenchmarkLoop,
        )

        suite = BenchmarkSuite()
        session_mgr = BenchmarkSessionManager()
        loop = SelfImprovingBenchmarkLoop(suite=suite, session_manager=session_mgr)

        tasks = loop._select_tasks()
        assert isinstance(tasks, list)

    @pytest.mark.fast
    def test_update_curriculum_with_none(self):
        """Test update_curriculum returns False when axes are None."""
        from cohezion.benchmarks.benchmark_suite import BenchmarkSuite
        from cohezion.eval.compound_integration import (
            BenchmarkSessionManager,
            SelfImprovingBenchmarkLoop,
        )

        suite = BenchmarkSuite()
        session_mgr = BenchmarkSessionManager()
        loop = SelfImprovingBenchmarkLoop(suite=suite, session_manager=session_mgr)

        changed = loop._update_curriculum(None, None)
        assert changed is False

    @pytest.mark.fast
    def test_update_curriculum_improving(self):
        """Test curriculum moves to IMPROVING when weak coherence."""
        from cohezion.benchmarks.benchmark_suite import BenchmarkSuite
        from cohezion.eval.compound_integration import (
            BenchmarkSessionManager,
            CurriculumState,
            SelfImprovingBenchmarkLoop,
        )

        suite = BenchmarkSuite()
        session_mgr = BenchmarkSessionManager()
        loop = SelfImprovingBenchmarkLoop(suite=suite, session_manager=session_mgr)

        changed = loop._update_curriculum("coherence", "stability")
        assert changed is True
        assert loop.curriculum_state == CurriculumState.IMPROVING
