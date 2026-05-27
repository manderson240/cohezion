"""Tests for compound loop ASCII visualizer."""

from cohezion.compound.loop_visualizer import (
    render_experiment_table,
    render_hiho_bar,
    render_session_summary,
)


class TestHIHOBar:
    def test_exploit_mode_label(self):
        bar = render_hiho_bar(0.8)
        assert "EXPLOIT" in bar
        assert "0.80" in bar

    def test_explore_mode_label(self):
        bar = render_hiho_bar(0.3)
        assert "EXPLORE" in bar

    def test_exact_threshold_is_exploit(self):
        bar = render_hiho_bar(0.5)
        assert "EXPLOIT" in bar

    def test_bar_length_consistent(self):
        bar1 = render_hiho_bar(0.0, width=10)
        bar2 = render_hiho_bar(1.0, width=10)
        # Both should have same structure |...|
        assert bar1.startswith("|") and bar1.count("|") == 2
        assert bar2.startswith("|") and bar2.count("|") == 2


class TestExperimentTable:
    def test_empty_stats(self):
        table = render_experiment_table({})
        assert "Experiment" in table  # Header still present

    def test_shows_experiment_name(self):
        stats = {
            "E63": {"total": 100, "keep_rate": 1.0, "mean_metric": 0.15, "cv": 0.05, "n_keeps": 100}
        }
        table = render_experiment_table(stats)
        assert "E63" in table

    def test_retirement_candidate_labeled(self):
        stats = {
            "E50": {"total": 50, "keep_rate": 1.0, "mean_metric": 0.125, "cv": 0.0, "n_keeps": 50}
        }
        table = render_experiment_table(stats, retirement_candidates=["E50"])
        assert "RETIRE" in table

    def test_active_experiment_labeled(self):
        stats = {
            "E63": {"total": 50, "keep_rate": 0.9, "mean_metric": 0.15, "cv": 0.06, "n_keeps": 45}
        }
        table = render_experiment_table(stats, retirement_candidates=[])
        assert "active" in table


class TestSessionSummary:
    def test_basic_summary(self):
        summary = render_session_summary(
            n_experiments=100,
            hiho_balance=0.8,
            mean_delta=0.15,
            keep_rate=0.95,
            retirement_candidates=["E50"],
        )
        assert "COMPOUND ENGINEERING" in summary
        assert "HIHO" in summary
        assert "E50" in summary

    def test_score_trend_shown_when_provided(self):
        summary = render_session_summary(
            n_experiments=50,
            hiho_balance=0.7,
            mean_delta=0.1,
            keep_rate=0.9,
            retirement_candidates=[],
            score_trend={"mean": 0.73, "improving": True, "degrading": False},
        )
        assert "Score Trend" in summary
        assert "▲" in summary  # Improving arrow
