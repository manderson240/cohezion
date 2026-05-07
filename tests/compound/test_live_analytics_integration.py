"""Integration tests using live autoresearch.jsonl data.

These tests use the actual autoresearch.jsonl file from the running
overnight EVO loop. They verify that the analytics pipeline produces
meaningful results on real data.
"""
from pathlib import Path

import pytest


JSONL_PATH = Path(__file__).parent.parent.parent / "autoresearch.jsonl"

pytestmark = pytest.mark.skipif(
    not JSONL_PATH.exists() or JSONL_PATH.stat().st_size < 1000,
    reason="autoresearch.jsonl not available or too small for live analytics",
)


class TestLiveAnalyticsIntegration:
    """Uses live autoresearch.jsonl data."""

    def test_can_load_records(self):
        from cohezion.compound.experiment_analytics import load_experiment_records
        records = load_experiment_records(n=100)
        assert len(records) > 0
        assert all("asi" in r or "experiment" in r for r in records[:5])

    def test_stats_have_required_fields(self):
        from cohezion.compound.experiment_analytics import (
            load_experiment_records, compute_experiment_stats
        )
        records = load_experiment_records(n=500)
        stats = compute_experiment_stats(records)
        for _exp, d in stats.items():
            assert "total" in d
            assert "keep_rate" in d
            assert "mean_metric" in d
            assert "cv" in d

    def test_hiho_balance_in_range(self):
        from cohezion.compound.experiment_analytics import (
            load_experiment_records, compute_hiho_balance
        )
        records = load_experiment_records(n=1000)
        hiho = compute_hiho_balance(records)
        assert 0.0 <= hiho <= 1.0, f"HIHO balance {hiho} out of range"

    def test_retirement_candidates_are_known_experiments(self):
        from cohezion.compound.experiment_analytics import (
            load_experiment_records, compute_experiment_stats,
            find_retirement_candidates
        )
        records = load_experiment_records(n=2000)
        stats = compute_experiment_stats(records)
        retired = find_retirement_candidates(stats)
        # All retirement candidates should be in our known experiment set
        known_exps = set(stats.keys())
        for r in retired:
            assert r in known_exps

    def test_get_analytics_report_structure(self):
        from cohezion.compound.experiment_analytics import get_analytics_report
        report = get_analytics_report(n=1000)
        assert "n_records" in report
        assert "hiho_balance" in report
        assert "retirement_candidates" in report
        assert "top_experiments" in report
        assert "per_experiment" in report

    def test_visualizer_renders_live_data(self):
        from cohezion.compound.experiment_analytics import get_analytics_report
        from cohezion.compound.loop_visualizer import (
            render_experiment_table, render_hiho_bar
        )
        report = get_analytics_report(n=500)
        bar = render_hiho_bar(report["hiho_balance"])
        assert "|" in bar
        assert "EXPLOIT" in bar or "EXPLORE" in bar

        table = render_experiment_table(
            report["per_experiment"],
            retirement_candidates=report["retirement_candidates"]
        )
        assert "Experiment" in table  # Header present
