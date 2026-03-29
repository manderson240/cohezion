"""Tests for StrategyTracker pivot detection."""

from cohezion.compound.retrospection_summary import StrategyTracker


class TestStrategyTracker:
    def test_plateau_detection_after_threshold(self):
        """3 attempts with <5% improvement triggers pivot recommendation."""
        tracker = StrategyTracker(pivot_threshold=3, improvement_threshold=0.05)
        assert tracker.record_outcome("skill_a", True, 0.01) is None
        assert tracker.record_outcome("skill_a", True, 0.02) is None
        result = tracker.record_outcome("skill_a", True, 0.03)
        assert result is not None
        assert "PIVOT RECOMMENDED" in result
        assert "plateaued" in result

    def test_consecutive_failure_detection(self):
        """3 consecutive failures triggers pivot recommendation."""
        tracker = StrategyTracker(pivot_threshold=3)
        assert tracker.record_outcome("skill_b", False, -0.1) is None
        assert tracker.record_outcome("skill_b", False, -0.2) is None
        result = tracker.record_outcome("skill_b", False, -0.3)
        assert result is not None
        assert "PIVOT RECOMMENDED" in result
        assert "failed" in result

    def test_success_resets_failure_count(self):
        """A success between failures resets the consecutive failure counter."""
        tracker = StrategyTracker(pivot_threshold=3)
        tracker.record_outcome("skill_c", False, -0.1)
        tracker.record_outcome("skill_c", False, -0.1)
        # Success resets the counter
        tracker.record_outcome("skill_c", True, 0.2)
        # Two more failures — still under threshold
        tracker.record_outcome("skill_c", False, -0.1)
        result = tracker.record_outcome("skill_c", False, -0.1)
        assert result is None  # Only 2 consecutive failures, not 3

    def test_below_threshold_no_trigger(self):
        """Fewer attempts than threshold does not trigger pivot."""
        tracker = StrategyTracker(pivot_threshold=3, improvement_threshold=0.05)
        assert tracker.record_outcome("skill_d", True, 0.01) is None
        assert tracker.record_outcome("skill_d", True, 0.02) is None
        # Only 2 attempts — no pivot yet

    def test_reset_clears_tracking(self):
        """Reset removes all state for a skill."""
        tracker = StrategyTracker(pivot_threshold=3)
        tracker.record_outcome("skill_e", False, -0.1)
        tracker.record_outcome("skill_e", False, -0.1)
        tracker.reset("skill_e")
        # After reset, counter starts fresh
        assert tracker.record_outcome("skill_e", False, -0.1) is None
        assert tracker.record_outcome("skill_e", False, -0.1) is None
        result = tracker.record_outcome("skill_e", False, -0.1)
        assert result is not None  # Now 3 consecutive again
