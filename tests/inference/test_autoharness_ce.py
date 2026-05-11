"""Unit tests for autoharness_ce — compound engineering optimization components."""

from __future__ import annotations

import pytest

from cohezion.inference.autoharness_ce import TokenBudget


class TestTokenBudget:
    def test_efficiency_gain_zero_when_no_baseline(self):
        """Zero baseline → 0.0 efficiency gain (no division by zero)."""
        tb = TokenBudget(baseline_tokens=0, optimized_tokens=0)
        assert tb.efficiency_gain() == 0.0

    def test_efficiency_gain_matches_our_session(self):
        """Verify the formula against known session values."""
        # Session: 145K baseline → ~15K optimized (90% reduction)
        tb = TokenBudget(baseline_tokens=145312, optimized_tokens=14841)
        gain = tb.efficiency_gain()
        assert 0.85 <= gain <= 0.95, f"Session efficiency: {gain:.3f} (expected ~0.90)"

    def test_efficiency_gain_zero_when_same(self):
        """No change in tokens → 0 gain."""
        tb = TokenBudget(baseline_tokens=1000, optimized_tokens=1000)
        assert tb.efficiency_gain() == 0.0

    def test_efficiency_gain_positive_when_optimized(self):
        """Optimization always improves → gain > 0."""
        tb = TokenBudget(baseline_tokens=100, optimized_tokens=60)
        gain = tb.efficiency_gain()
        assert gain == pytest.approx(0.4)

    def test_efficiency_gain_capped_by_baseline(self):
        """Complete elimination: optimized=0 → gain=1.0."""
        tb = TokenBudget(baseline_tokens=100, optimized_tokens=0)
        assert tb.efficiency_gain() == 1.0

    def test_report_contains_efficiency_pct(self):
        """report() converts gain to percentage."""
        tb = TokenBudget(baseline_tokens=1000, optimized_tokens=700)
        r = tb.report()
        assert "efficiency_gain_pct" in r
        assert r["efficiency_gain_pct"] == pytest.approx(30.0)

    def test_report_includes_all_fields(self):
        tb = TokenBudget(baseline_tokens=5000, optimized_tokens=2000, reference_savings=1500)
        r = tb.report()
        assert r["baseline_tokens"] == 5000
        assert r["optimized_tokens"] == 2000
        assert r["reference_savings"] == 1500

    def test_reference_savings_tracked_separately(self):
        """Reference savings are tracked separately from optimized_tokens."""
        tb = TokenBudget(baseline_tokens=10000, optimized_tokens=3000, reference_savings=2000)
        # efficiency_gain only uses baseline vs optimized
        gain = tb.efficiency_gain()
        assert gain == pytest.approx(0.7)
        assert tb.reference_savings == 2000
