"""Discriminating tests for optimization.r_zero.LocalModelOptimizer.

FIXED 2026-06-06 (backlog item 8 / audit §12.1): the success-rate tracker previously counted
prior records whose DERIVED rate == 1.0 (impossible for a fresh optimizer) and divided by
total+1, so the rate never exceeded 0.5 and the >0.8 difficulty branch was unreachable. The
rate is now computed from the RAW per-execution success bools. These tests assert the FIXED
behavior (the two formerly-pinned-buggy tests were flipped deliberately); each still fails a
plausible wrong impl:
  - get_current_multiplier that returns 0.8 (not 1.0) on an empty history,
  - a rate that doesn't reflect the real success ratio,
  - difficulty_adjustment thresholded at >= 0.8 instead of > 0.8.
"""

from __future__ import annotations

from cohezion.optimization.r_zero import LocalModelOptimizer


def test_empty_history_multiplier_is_one() -> None:
    # Discriminates an impl that defaults to the 0.8 "hard" multiplier before any data.
    assert LocalModelOptimizer().get_current_multiplier() == 1.0


def test_first_success_rate_is_one_after_fix() -> None:
    # FIXED §12.1: rate = raw successes / window. 1 success / 1 execution = 1.0 (was a buggy
    # 0.5). 1.0 > 0.8 → the multiplier reaches 1.0 (the branch that used to be dead).
    opt = LocalModelOptimizer()
    opt.record_execution("qwen3-coder", success=True, iterations=3)
    m = opt.metrics_history[-1]
    assert m.success_rate == 1.0
    assert m.iteration_count == 3
    assert opt.get_current_multiplier() == 1.0


def test_first_failure_rate_is_zero() -> None:
    opt = LocalModelOptimizer()
    opt.record_execution("deepseek-r1", success=False, iterations=7)
    assert opt.metrics_history[-1].success_rate == 0.0
    assert opt.get_current_multiplier() == 0.8


def test_repeated_success_reaches_full_rate_and_high_multiplier() -> None:
    # THE falsifiable check for §12.1: repeated successes now climb to rate 1.0 (was capped
    # ≤0.5), so success_rate CAN exceed 0.5 and the >0.8 branch fires.
    opt = LocalModelOptimizer()
    for _ in range(6):
        opt.record_execution("m", success=True, iterations=1)
    assert opt.metrics_history[-1].success_rate == 1.0
    assert any(m.success_rate > 0.5 for m in opt.metrics_history)
    assert opt.get_current_multiplier() == 1.0


def test_rate_reflects_real_success_ratio() -> None:
    # Discriminates: the rate is the real trailing ratio, not stuck and not always 1.0.
    # 7 successes + 3 failures in the 10-window → 0.7 (and 0.7 is NOT > 0.8 → multiplier 0.8).
    opt = LocalModelOptimizer()
    for s in [True] * 7 + [False] * 3:
        opt.record_execution("m", success=s, iterations=1)
    assert opt.metrics_history[-1].success_rate == 0.7
    assert opt.get_current_multiplier() == 0.8


def test_record_execution_appends_history() -> None:
    opt = LocalModelOptimizer()
    opt.record_execution("m", success=True, iterations=1)
    opt.record_execution("m", success=False, iterations=2)
    assert len(opt.metrics_history) == 2
    assert opt.get_current_multiplier() == opt.metrics_history[-1].difficulty_adjustment
