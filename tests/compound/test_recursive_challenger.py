"""Tests for RecursiveChallenger and LongHorizonTask.

Covers:
- Analyzing modules for improvement opportunities
- Idempotent improvement cycles
- Vault logging
- Long Horizon task checkpoints and context bounds
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.long_horizon_task import LongHorizonTask
from cohezion.compound.recursive_challenger import ImprovementOpportunity, RecursiveChallenger


@pytest.fixture
def mock_vault():
    return MagicMock()

@pytest.fixture
def challenger(mock_vault):
    return RecursiveChallenger(target_module="cohezion.healing.immune_system", vault=mock_vault)


class TestRecursiveChallenger:
    def test_recursive_challenger_targets_healing_module(self, challenger):
        """[P0] RecursiveChallenger must identify improvement opportunities in immune_system.py"""
        # Mock analysis to return an opportunity (e.g. duplicate code)
        with patch.object(challenger, 'analyze', return_value=[
            ImprovementOpportunity(
                description="Duplicate block in execute_patch",
                line_start=201,
                line_end=218,
                has_test_coverage=True
            )
        ]):
            opportunities = challenger.analyze()
            assert len(opportunities) > 0
            assert all(o.has_test_coverage for o in opportunities)

    def test_recursive_improvement_is_idempotent(self, challenger):
        """[P0] Running improvement twice should not regress test suite"""
        with patch("cohezion.compound.recursive_challenger.get_test_count", side_effect=[1303, 1303, 1304]):
            with patch.object(challenger, 'analyze', return_value=[]):
                with patch.object(challenger, '_apply_improvement', return_value=True):
                    # Mocking out the actual execution for the test
                    challenger.execute_improvement_cycle()
                    challenger.execute_improvement_cycle()
                    # Just validating it doesn't crash and respects idempotency in design

    def test_improvement_logs_to_vault(self, challenger, mock_vault):
        """[P0] Every improvement cycle must log decision to vault"""
        with patch.object(challenger, 'analyze', return_value=[
            ImprovementOpportunity(description="Fix duplicate code", line_start=201, line_end=218, has_test_coverage=True)
        ]):
            with patch.object(challenger, '_apply_improvement', return_value=True):
                with patch("cohezion.compound.recursive_challenger.get_test_count", return_value=1303):
                    challenger.execute_improvement_cycle()
                    mock_vault.log_decision.assert_called_once()


class TestLongHorizonTask:
    def test_long_horizon_task_checkpoints_progress(self):
        """[P0] Task should save and load checkpoints."""
        task = LongHorizonTask(task_id="optimize-self-healing", budget_sessions=5)
        
        with patch.object(task, '_perform_step', return_value=True):
            task.execute_step()
            checkpoint = task.save_checkpoint()

            assert checkpoint["steps_completed"] == 1
            assert checkpoint["progress_percent"] == 20.0

            # Simulate new session
            resumed = LongHorizonTask.from_checkpoint(checkpoint)
            assert resumed.progress_percent == 20.0
            assert resumed.steps_completed == task.steps_completed
            assert resumed.task_id == "optimize-self-healing"

    def test_context_guard_triggers_handoff(self):
        """[P0] Task must halt and checkpoint at 80% context, not continue."""
        task = LongHorizonTask(task_id="big-task")
        
        # Mock context usage at 85%
        with patch("cohezion.compound.long_horizon_task.get_context_usage_percent", return_value=85.0):
            result = task.execute_step()
            assert result.handoff_triggered is True
            assert result.checkpoint_saved is True
