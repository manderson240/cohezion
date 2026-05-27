"""Tests for CompoundScoreWindow."""

from cohezion.compound.compound_score_tracker import CompoundScoreWindow


class TestCompoundScoreWindow:
    def test_empty_window_mean_is_neutral(self):
        w = CompoundScoreWindow()
        assert w.mean == 0.5

    def test_single_score(self):
        w = CompoundScoreWindow()
        w.record(0.8)
        assert w.mean == 0.8

    def test_mean_of_multiple_scores(self):
        w = CompoundScoreWindow()
        for s in [0.5, 0.7, 0.9]:
            w.record(s)
        assert abs(w.mean - 0.7) < 0.001

    def test_window_respects_max_size(self):
        w = CompoundScoreWindow(window_size=5)
        for i in range(10):
            w.record(float(i) / 10)
        assert len(w._scores) == 5

    def test_improving_trend(self):
        w = CompoundScoreWindow(window_size=10)
        # First half: low scores, second half: high scores
        for s in [0.3, 0.3, 0.3, 0.3, 0.3]:
            w.record(s)
        for s in [0.8, 0.8, 0.8, 0.8, 0.8]:
            w.record(s)
        assert w.is_improving is True
        assert w.trend > 0.1

    def test_degrading_trend(self):
        w = CompoundScoreWindow(window_size=10)
        for s in [0.8, 0.8, 0.8, 0.8, 0.8]:
            w.record(s)
        for s in [0.3, 0.3, 0.3, 0.3, 0.3]:
            w.record(s)
        assert w.is_degrading is True
        assert w.trend < -0.1

    def test_stable_trend(self):
        w = CompoundScoreWindow()
        for _ in range(10):
            w.record(0.7)
        assert not w.is_improving
        assert not w.is_degrading

    def test_summary_has_all_keys(self):
        w = CompoundScoreWindow()
        w.record(0.8)
        summary = w.summary()
        assert "n" in summary
        assert "mean" in summary
        assert "trend" in summary
        assert "improving" in summary
        assert "degrading" in summary
