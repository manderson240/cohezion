"""Tests for shared eval statistics (variance-honest coding-eval scoring).

Implements OpenAI coding-eval practices (work-queue d7f5e0e4808d): pass@k, bootstrap CI +
small-n caveat, contamination probe.
"""

from __future__ import annotations

import pytest

from cohezion.eval.stats import (
    MIN_TRUSTWORTHY_TRIALS,
    bootstrap_ci,
    contamination_probe,
    mean_ci,
    pass_at_k,
)


class TestPassAtK:
    def test_all_correct_is_one(self):
        assert pass_at_k(5, 5, 1) == 1.0

    def test_none_correct_is_zero(self):
        assert pass_at_k(5, 0, 1) == 0.0

    def test_known_values(self):
        # 1 - C(n-c,k)/C(n,k): (10,1,1)->1-9/10=0.1 ; (10,5,1)->1-5/10=0.5
        assert pass_at_k(10, 1, 1) == pytest.approx(0.1)
        assert pass_at_k(10, 5, 1) == pytest.approx(0.5)

    def test_fewer_than_k_failures_is_one(self):
        # only 4 failures but k=5 → some correct sample always drawn
        assert pass_at_k(5, 1, 5) == 1.0

    def test_exact_intermediate_value(self):
        # 1 - C(2,2)/C(5,2) = 1 - 1/10 = 0.9
        assert pass_at_k(5, 3, 2) == pytest.approx(0.9)

    def test_monotonic_in_k(self):
        # more attempts can only raise the chance at least one is correct
        assert pass_at_k(10, 3, 1) <= pass_at_k(10, 3, 2) <= pass_at_k(10, 3, 3)

    @pytest.mark.parametrize("n,c,k", [(0, 0, 1), (5, 6, 1), (5, 2, 0)])
    def test_invalid_inputs_raise(self, n, c, k):
        with pytest.raises(ValueError):
            pass_at_k(n, c, k)


class TestBootstrapCI:
    def test_constant_values_zero_width(self):
        assert bootstrap_ci([0.7, 0.7, 0.7, 0.7]) == (pytest.approx(0.7), pytest.approx(0.7))

    def test_single_value_no_spread(self):
        assert bootstrap_ci([0.42]) == (pytest.approx(0.42), pytest.approx(0.42))

    def test_ci_brackets_the_mean(self):
        vals = [0.0, 0.5, 0.5, 1.0, 0.5, 0.0, 1.0, 0.5]
        low, high = bootstrap_ci(vals, seed=1)
        assert low <= sum(vals) / len(vals) <= high
        assert low < high  # genuine spread → non-degenerate interval

    def test_seeded_deterministic(self):
        vals = [0.1, 0.9, 0.5, 0.3, 0.7]
        assert bootstrap_ci(vals, seed=7) == bootstrap_ci(vals, seed=7)


class TestMeanCI:
    def test_small_n_flagged(self):
        r = mean_ci([1.0, 0.0, 1.0])  # n=3 < MIN_TRUSTWORTHY_TRIALS
        assert r.n == 3 and r.small_n_warning is True
        assert r.mean == pytest.approx(2 / 3)
        assert r.ci_low <= r.mean <= r.ci_high

    def test_enough_trials_not_flagged(self):
        r = mean_ci([1.0, 0.0, 1.0, 1.0, 0.0, 1.0])  # n=6 >= 5
        assert r.n >= MIN_TRUSTWORTHY_TRIALS and r.small_n_warning is False


class TestContaminationProbe:
    def test_leak_detected_when_model_regurgitates_reference(self):
        ref = "def add(a, b):\n    return a + b"
        res = contamination_probe(lambda _p: ref, ref, threshold=0.6)
        assert res.leaked is True and res.similarity == pytest.approx(1.0)

    def test_no_leak_on_unrelated_output(self):
        res = contamination_probe(
            lambda _p: "the weather is nice today", "def add(a, b): return a + b", threshold=0.6
        )
        assert res.leaked is False and res.similarity < 0.6

    def test_model_error_is_handled(self):
        def boom(_p):
            raise RuntimeError("model down")

        res = contamination_probe(boom, "reference", threshold=0.6)
        assert res.leaked is False and res.similarity == 0.0
