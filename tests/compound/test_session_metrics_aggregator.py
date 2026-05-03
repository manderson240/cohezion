"""Tests for SessionMetricsAggregator."""
import asyncio
from cohezion.compound.session_metrics_aggregator import SessionMetricsAggregator


class TestSessionMetricsAggregator:

    def test_empty_aggregator_returns_neutral(self):
        agg = SessionMetricsAggregator()
        summary = agg.compute_summary()
        assert summary["n_experiments"] == 0
        assert summary["hiho_balance"] == 0.5

    def test_record_increments_count(self):
        agg = SessionMetricsAggregator()
        agg.record("E63", 0.15, 0.8)
        agg.record("E64", 0.12, 0.75)
        assert agg.compute_summary()["n_experiments"] == 2

    def test_all_positive_hiho_balance_is_one(self):
        agg = SessionMetricsAggregator()
        for i in range(5):
            agg.record(f"E{i}", 0.1 + i * 0.01, 0.8)
        assert agg.compute_summary()["hiho_balance"] == 1.0

    def test_all_negative_hiho_balance_is_zero(self):
        agg = SessionMetricsAggregator()
        for i in range(5):
            agg.record(f"E{i}", -0.1, 0.3)
        assert agg.compute_summary()["hiho_balance"] == 0.0

    def test_mixed_hiho_balance_correct_fraction(self):
        agg = SessionMetricsAggregator()
        agg.record("A", 0.1, 0.8)
        agg.record("B", 0.2, 0.7)
        agg.record("C", -0.1, 0.3)
        agg.record("D", -0.05, 0.4)
        summary = agg.compute_summary()
        assert summary["hiho_balance"] == 0.5  # 2/4 positive

    def test_top_experiments_sorted_by_delta(self):
        agg = SessionMetricsAggregator()
        agg.record("low", 0.05, 0.6)
        agg.record("high", 0.20, 0.8)
        agg.record("mid", 0.12, 0.7)
        top = agg.compute_summary()["top_experiments"]
        assert top[0]["label"] == "high"
        assert top[0]["delta"] == 0.2

    def test_suggest_next_returns_list(self):
        agg = SessionMetricsAggregator()
        agg.record("E63", 0.15, 0.8)
        result = asyncio.run(agg.suggest_next(n=3))
        assert len(result) == 3
        assert all("hypothesis" in e for e in result)

