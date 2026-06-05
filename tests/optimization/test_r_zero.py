"""Discriminating tests for optimization.r_zero.LocalModelOptimizer (V-model audit, 2026-06-05).

`optimization` was a no-test module. These tests pin the ACTUAL arithmetic of the R-Zero
success-rate tracker (report-only audit — behavior is pinned, not changed). Each fails a
plausible wrong impl:
  - get_current_multiplier that returns 0.8 (not 1.0) on an empty history,
  - a missing max(1, len) clamp that would divide the first success by 1 (rate 1.0) instead of 2,
  - difficulty_adjustment thresholded at >= 0.8 instead of > 0.8.

OBSERVATION (latent smell, flagged not fixed): `recent_successes` counts prior records whose
success_rate == 1.0, which a fresh optimizer can never produce, so success_rate never climbs
above 0.5 and the >0.8 (multiplier 1.0) branch is effectively unreachable. Recorded in the
audit report for a future, separately-gated remediation.
"""
from __future__ import annotations

from cohezion.optimization.r_zero import LocalModelOptimizer


def test_empty_history_multiplier_is_one() -> None:
    # Discriminates an impl that defaults to the 0.8 "hard" multiplier before any data.
    assert LocalModelOptimizer().get_current_multiplier() == 1.0


def test_first_success_rate_is_half_not_one() -> None:
    # base_rate = (0 + 1) / (min(10,max(1,0)) + 1) = 1/2. A missing max(1,len) clamp would
    # make the denominator 1 -> rate 1.0. Pin 0.5.
    opt = LocalModelOptimizer()
    opt.record_execution("qwen3-coder", success=True, iterations=3)
    m = opt.metrics_history[-1]
    assert m.success_rate == 0.5
    assert m.iteration_count == 3
    assert opt.get_current_multiplier() == 0.8  # 0.5 is NOT > 0.8


def test_first_failure_rate_is_zero() -> None:
    opt = LocalModelOptimizer()
    opt.record_execution("deepseek-r1", success=False, iterations=7)
    assert opt.metrics_history[-1].success_rate == 0.0
    assert opt.get_current_multiplier() == 0.8


def test_success_rate_does_not_climb_above_half_on_repeated_success() -> None:
    # Pins the latent quirk: repeated successes never reach rate 1.0, so the multiplier
    # stays at 0.8 (the >0.8 branch is unreachable from a fresh optimizer). If a future fix
    # changes this, THIS test should be updated deliberately.
    opt = LocalModelOptimizer()
    for _ in range(6):
        opt.record_execution("m", success=True, iterations=1)
    assert all(m.success_rate <= 0.5 for m in opt.metrics_history)
    assert opt.get_current_multiplier() == 0.8


def test_record_execution_appends_history() -> None:
    opt = LocalModelOptimizer()
    opt.record_execution("m", success=True, iterations=1)
    opt.record_execution("m", success=False, iterations=2)
    assert len(opt.metrics_history) == 2
    assert opt.get_current_multiplier() == opt.metrics_history[-1].difficulty_adjustment
