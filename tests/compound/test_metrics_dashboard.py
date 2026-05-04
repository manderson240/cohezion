"""TDD tests for compound metrics dashboard rendering.

These tests drive the render_dashboard() method on SessionMetricsAggregator.
"""

import pytest

from cohezion.compound.session_metrics_aggregator import SessionMetricsAggregator


class TestRenderDashboardEmpty:
    """Dashboard with no experiments recorded."""

    def test_returns_string(self):
        agg = SessionMetricsAggregator()
        result = agg.render_dashboard()
        assert isinstance(result, str)

    def test_contains_header(self):
        agg = SessionMetricsAggregator()
        result = agg.render_dashboard()
        assert "Compound Session Dashboard" in result

    def test_shows_zero_experiments(self):
        agg = SessionMetricsAggregator()
        result = agg.render_dashboard()
        assert "0" in result


class TestRenderDashboardWithData:
    """Dashboard with recorded experiments."""

    @pytest.fixture
    def populated_agg(self):
        agg = SessionMetricsAggregator()
        agg.record("E71_compound_score", delta=0.05, coherence=0.72)
        agg.record("E72_flume_encoding", delta=0.12, coherence=0.68)
        agg.record("E73_hiho_calibration", delta=-0.03, coherence=0.55)
        agg.record("E74_voice_weight", delta=0.09, coherence=0.80)
        agg.record("E75_temporal_encoding", delta=-0.01, coherence=0.50)
        return agg

    def test_shows_experiment_count(self, populated_agg):
        result = populated_agg.render_dashboard()
        assert "5" in result

    def test_shows_hiho_balance(self, populated_agg):
        result = populated_agg.render_dashboard()
        assert "HIHO" in result

    def test_shows_keep_rate(self, populated_agg):
        result = populated_agg.render_dashboard()
        assert "keep" in result.lower() or "Keep" in result

    def test_shows_mean_delta(self, populated_agg):
        result = populated_agg.render_dashboard()
        assert "delta" in result.lower() or "Delta" in result

    def test_top_experiment_appears(self, populated_agg):
        result = populated_agg.render_dashboard()
        # E72 has highest delta (0.12) — must appear
        assert "E72_flume_encoding" in result

    def test_top_experiments_ordered_by_delta(self, populated_agg):
        result = populated_agg.render_dashboard()
        pos_e72 = result.find("E72_flume_encoding")
        pos_e71 = result.find("E71_compound_score")
        assert pos_e72 < pos_e71, "E72 (delta=0.12) must appear before E71 (delta=0.05)"


class TestRenderDashboardMode:
    """Dashboard mode indicator (exploit vs explore)."""

    def test_exploit_mode_when_high_coherence(self):
        agg = SessionMetricsAggregator()
        agg.record("E_a", delta=0.1, coherence=0.8)
        agg.record("E_b", delta=0.2, coherence=0.9)
        result = agg.render_dashboard()
        assert "exploit" in result.lower()

    def test_explore_mode_when_low_coherence(self):
        agg = SessionMetricsAggregator()
        agg.record("E_a", delta=-0.1, coherence=0.2)
        agg.record("E_b", delta=-0.2, coherence=0.3)
        result = agg.render_dashboard()
        assert "explore" in result.lower()

    def test_mode_boundary_at_threshold(self):
        agg = SessionMetricsAggregator()
        # Exactly at threshold (0.5) → exploit
        agg.record("E_a", delta=0.0, coherence=0.5)
        result = agg.render_dashboard()
        assert "exploit" in result.lower()


class TestRenderDashboardFormat:
    """Dashboard formatting guarantees."""

    def test_multiline_output(self):
        agg = SessionMetricsAggregator()
        agg.record("E_a", delta=0.1, coherence=0.7)
        result = agg.render_dashboard()
        assert "\n" in result

    def test_no_exception_with_single_record(self):
        agg = SessionMetricsAggregator()
        agg.record("solo_experiment", delta=0.5, coherence=0.6)
        result = agg.render_dashboard()
        assert "solo_experiment" in result

    def test_title_line_appears_first(self):
        agg = SessionMetricsAggregator()
        result = agg.render_dashboard()
        first_line = result.split("\n")[0]
        assert (
            "Dashboard" in first_line
            or "COMPOUND" in first_line.upper()
            or "Compound" in first_line
        )
