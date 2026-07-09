"""Discriminating tests for feynman_amplitude_rank (2026-06-06, backlog item 6).

The continuous quality×energy ranking. Each test fails a plausible wrong impl:
  - one that ignores energy (NPU would NOT win the equal-quality tie),
  - one that lets energy OVERRIDE quality (a heavier-but-better lane would lose),
  - one that breaks CC2 (energy term must be inert at energy=0 → cost-only ordering),
  - an unstable sort (equal candidates must keep input order).
"""

from __future__ import annotations

from cohezion.inference.fractal_metrics import (
    feynman_amplitude_rank,
    feynman_path_weight,
)


def test_npu_wins_the_equal_quality_tie_on_lower_energy() -> None:
    # All equal quality + $0; only joules differ. NPU (4 J) must rank first.
    cands = [("igpu", 0.8, 0.0, 35.0), ("cpu", 0.8, 0.0, 55.0), ("npu", 0.8, 0.0, 4.0)]
    assert feynman_amplitude_rank(cands)[0] == "npu"


def test_higher_quality_heavier_lane_still_wins() -> None:
    # CRITICAL guard: energy must NOT override quality. A 0.9-quality CPU (55 J) beats a
    # 0.5-quality NPU (4 J) — a wrong impl that over-weights energy would pick npu.
    cands = [("npu", 0.5, 0.0, 4.0), ("cpu", 0.9, 0.0, 55.0)]
    assert feynman_amplitude_rank(cands)[0] == "cpu"


def test_cc2_energy_off_is_cost_only_ordering() -> None:
    # energy_joules=0 for all → ranking reduces to quality×cost (CC2 unaffected).
    # Local $0 q=0.5 must beat cloud $0.01 q=1.0 (the CC2 guarantee).
    cands = [("cloud", 1.0, 0.01, 0.0), ("local", 0.5, 0.0, 0.0)]
    assert feynman_amplitude_rank(cands)[0] == "local"
    # and it agrees with feynman_path_weight directly
    assert feynman_path_weight(0.5, 0.0, 0.0) > feynman_path_weight(1.0, 0.01, 0.0)


def test_rank_is_stable_for_identical_candidates() -> None:
    cands = [("a", 0.7, 0.0, 10.0), ("b", 0.7, 0.0, 10.0), ("c", 0.7, 0.0, 10.0)]
    assert feynman_amplitude_rank(cands) == ["a", "b", "c"]  # input order preserved


def test_returns_all_candidates_once() -> None:
    cands = [("a", 0.6, 0.0, 4.0), ("b", 0.9, 0.0, 55.0)]
    assert sorted(feynman_amplitude_rank(cands)) == ["a", "b"]
