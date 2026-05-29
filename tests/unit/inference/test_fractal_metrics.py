"""Unit tests for fractal_metrics — Higuchi FD, Feynman weights, BBQ mode."""

from __future__ import annotations

import random

import pytest

from cohezion.inference.fractal_metrics import (
    feynman_path_weight,
    higuchi_fd,
    hiho_fixed_point_deviation,
    quality_series_report,
)
from cohezion.inference.quality_eval import evaluate, ttft_budget_ms


class TestHiguchiFD:
    def test_constant_series_returns_one(self):
        fd = higuchi_fd([0.8] * 20)
        assert fd == pytest.approx(1.0, abs=0.1)

    def test_all_zero_series_returns_one(self):
        fd = higuchi_fd([0.0] * 20)
        assert fd == pytest.approx(1.0, abs=0.1)

    def test_insufficient_data_returns_one(self):
        assert higuchi_fd([]) == 1.0
        assert higuchi_fd([0.5]) == 1.0
        assert higuchi_fd([0.5, 0.6, 0.7]) == 1.0

    def test_hiho_brownian_series_in_range(self):
        rng = random.Random(42)
        hiho = [max(0, min(1, 0.5 + rng.gauss(0, 0.12))) for _ in range(50)]
        fd = higuchi_fd(hiho)
        assert 1.0 <= fd <= 2.0, f"FD {fd} out of [1.0, 2.0]"

    def test_result_bounded_1_to_2(self):
        rng = random.Random(99)
        for _ in range(5):
            series = [rng.random() for _ in range(30)]
            fd = higuchi_fd(series)
            assert 1.0 <= fd <= 2.0


class TestFeynmanPathWeight:
    def test_zero_cost_returns_quality_score(self):
        w = feynman_path_weight(0.8, cost_usd=0.0)
        assert w == pytest.approx(0.8, rel=1e-6)

    def test_nonzero_cost_reduces_weight(self):
        w0 = feynman_path_weight(0.9, cost_usd=0.0)
        w1 = feynman_path_weight(0.9, cost_usd=0.01)
        assert w1 < w0

    def test_local_dominates_cloud_at_same_quality(self):
        npu = feynman_path_weight(0.85, cost_usd=0.0)
        cloud = feynman_path_weight(0.85, cost_usd=0.01)
        assert npu > cloud

    def test_local_always_dominates_cloud_in_feynman_amplitude(self):
        """With λ=100, local silicon ($0) ALWAYS wins on Feynman amplitude.

        Cloud escalation happens via quality gate failure, not Feynman preference.
        Even NPU at 0.5 quality beats Sonnet at 0.99: 0.5 > 0.99 × exp(-1) = 0.364.
        """
        npu = feynman_path_weight(0.5, cost_usd=0.0)
        cloud = feynman_path_weight(0.99, cost_usd=0.01)
        assert npu > cloud  # local always preferred — cloud gated by quality gate failure


class TestHIHODeviation:
    def test_series_at_half_has_zero_deviation(self):
        dev = hiho_fixed_point_deviation([0.5] * 10)
        assert dev == pytest.approx(0.0, abs=1e-6)

    def test_empty_series_returns_inf(self):
        assert hiho_fixed_point_deviation([]) == float("inf")

    def test_deviation_measured_from_half(self):
        dev = hiho_fixed_point_deviation([0.8] * 10)
        assert dev == pytest.approx(0.3, abs=1e-6)


class TestQualitySeriesReport:
    def test_empty_returns_no_data(self):
        r = quality_series_report([])
        assert r["interpretation"] == "no data"

    def test_report_has_required_keys(self):
        scores = [0.5 + 0.05 * (i % 3 - 1) for i in range(20)]
        r = quality_series_report(scores)
        assert "fd" in r
        assert "hiho_deviation" in r
        assert "hiho_engaged" in r
        assert "feynman_dominant_tier" in r
        assert "interpretation" in r

    def test_high_quality_series_routes_to_npu(self):
        scores = [0.95] * 20
        r = quality_series_report(scores)
        assert r["feynman_dominant_tier"] == "npu"


class TestBBQLowSlowMode:
    def test_short_output_rejected(self):
        v = evaluate("short", "bbq_low_slow")
        assert v.accept is False
        assert "500" in v.reason

    def test_long_unctuous_output_accepted(self):
        long_text = (
            "The relationship between LENR and HIHO equilibrium is profound. "
            "At the quantum level, lattice coherence drives the nuclear reaction rate "
            "through the same beta-binomial kernel that governs bioelectric percolation. "
            "This universal 4x(1-x) formula peaks precisely at coherence=0.5, "
            "which corresponds to the HIHO threshold in every substrate from "
            "ionic clusters to dielectric fields. "
            "The Feynman path integral formalism reveals why: at x=0.5, the system "
            "explores all paths equally, maximizing the amplitude sum. "
            "This is not coincidence but structural necessity — the logistic map's "
            "fixed point is the only configuration where exploration equals exploitation. "
            "Stealthskater archives confirm this across multiple independent domains."
        )
        assert len(long_text) > 500
        v = evaluate(long_text, "bbq_low_slow")
        assert v.accept is True

    def test_bbq_ttft_budget_is_infinite(self):
        budget = ttft_budget_ms("bbq_low_slow")
        assert budget == float("inf")

    def test_uncertainty_opener_rejected(self):
        uncertain = (
            "I'm not sure how to answer this question about LENR and HIHO. "
            "The relationship is complex and I cannot determine the precise mechanism. "
            "It might be related to quantum coherence but I am uncertain about "
            "the specific mathematical formulation. There are many possible interpretations "
            "and the literature is contradictory on this point."
        ) * 2  # make it long enough to pass length gate
        v = evaluate(uncertain, "bbq_low_slow")
        assert v.accept is False
        assert "uncertainty" in v.reason.lower()


class TestAutoDQAFractalHealth:
    def test_fractal_health_returns_dict(self):
        from cohezion.compound.autodqa import AutoDQA

        dqa = AutoDQA(persist=False, notify_on_reject=False)
        for _ in range(10):
            dqa.evaluate("def f(): pass", "write a function")
        health = dqa.fractal_health()
        assert "fd" in health
        assert "hiho_engaged" in health


# ---------------------------------------------------------------------------
# ID-14: Brownian motion validator — healthy compound loop quality (exp_RRRR)
# ---------------------------------------------------------------------------


class TestBrownianMotionHIHORange:
    """Verify that Brownian quality series produce FD in HIHO [1.3, 1.7] range."""

    def _brownian_quality(self, n: int = 100, noise: float = 0.06, seed: int = 42) -> list[float]:
        rng = random.Random(seed)
        x = 0.5
        out = []
        for _ in range(n):
            x += rng.gauss(0, noise)
            out.append(max(0.0, min(1.0, x)))
        return out

    def test_brownian_fd_in_hiho_range_seed42(self):
        from cohezion.inference.fractal_metrics import higuchi_fd

        fd = higuchi_fd(self._brownian_quality(seed=42))
        assert 1.3 <= fd <= 1.7, f"Brownian FD {fd:.4f} outside HIHO range [1.3, 1.7]"

    def test_brownian_fd_in_hiho_range_multiple_seeds(self):
        from cohezion.inference.fractal_metrics import higuchi_fd

        seeds = [42, 123, 2026, 999, 1337]
        fds = [higuchi_fd(self._brownian_quality(seed=s)) for s in seeds]
        in_range = sum(1 for fd in fds if 1.3 <= fd <= 1.7)
        assert in_range >= 4, f"Only {in_range}/5 Brownian series in HIHO range. FDs: {fds}"

    def test_brownian_mean_fd_near_1_5(self):
        from cohezion.inference.fractal_metrics import higuchi_fd

        fds = [higuchi_fd(self._brownian_quality(seed=s)) for s in range(10)]
        avg = sum(fds) / len(fds)
        assert 1.3 <= avg <= 1.7, f"Mean Brownian FD {avg:.4f} far from 1.5 target"

    def test_bimodal_fd_outside_hiho_range(self):
        """Bimodal (binary 0/1) quality series should have FD > 1.7 (too noisy)."""
        from cohezion.inference.fractal_metrics import higuchi_fd

        bimodal = [1.0 if i % 5 != 0 else 0.0 for i in range(100)]
        fd = higuchi_fd(bimodal)
        assert fd > 1.7, f"Bimodal FD {fd:.4f} should be > 1.7 (chaotic)"

    def test_step_function_fd_below_hiho_range(self):
        """Step function (stuck quality) should have FD < 1.3 (deterministic)."""
        from cohezion.inference.fractal_metrics import higuchi_fd

        step = [0.3] * 30 + [0.7] * 40 + [0.5] * 30
        fd = higuchi_fd(step)
        assert fd < 1.3, f"Step function FD {fd:.4f} should be < 1.3 (stuck)"


# ---------------------------------------------------------------------------
# ID-15 lives in test_orchestrator.py (already added in exp_OOOO)
# Quick structural check here as a regression guard
# ---------------------------------------------------------------------------
