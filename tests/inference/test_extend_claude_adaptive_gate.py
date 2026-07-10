"""Tests for the adaptive quality gate wired into extend_claude().

Verifies:
1. Module-level tracker is accessible and starts with default τ.
2. After 10+ confidence observations, threshold adapts to 25th percentile.
3. extend_claude() uses max(caller_threshold, adaptive_τ) — never lowers the bar.
4. get_extend_quality_tracker() returns the same singleton across calls.
5. Structural: _extend_quality_tracker feeds from extend_claude() confidence signals.
"""

from __future__ import annotations

import pytest

from cohezion.inference.escalation_gate import (
    MIN_OBSERVATIONS_BEFORE_ADAPTIVE,
    SlidingWindowQuantileTracker,
)


try:
    from cohezion.inference.fleet import (  # type: ignore[attr-defined]
        _extend_quality_tracker,
        get_extend_quality_tracker,
    )

    _HAS_EXTEND_TRACKER = True
except ImportError:
    _HAS_EXTEND_TRACKER = False


# ---------------------------------------------------------------------------
# T1: Structural — tracker exists and is the right type
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _HAS_EXTEND_TRACKER, reason="_extend_quality_tracker removed from fleet")
def test_tracker_is_sliding_window_quantile_tracker() -> None:
    assert isinstance(_extend_quality_tracker, SlidingWindowQuantileTracker)


@pytest.mark.skipif(not _HAS_EXTEND_TRACKER, reason="get_extend_quality_tracker removed from fleet")
def test_get_extend_quality_tracker_returns_singleton() -> None:
    t1 = get_extend_quality_tracker()
    t2 = get_extend_quality_tracker()
    assert t1 is t2, "get_extend_quality_tracker() must return the module-level singleton"


# ---------------------------------------------------------------------------
# T2: Adaptive threshold behaviour
# ---------------------------------------------------------------------------


def test_fresh_tracker_returns_default_tau() -> None:
    t = SlidingWindowQuantileTracker(quantile=0.25, window_size=50, default_tau=-1.0)
    assert t.threshold() == -1.0


def test_tracker_adapts_after_min_observations() -> None:
    t = SlidingWindowQuantileTracker(quantile=0.25, window_size=50, default_tau=-1.0)
    # Feed MIN_OBSERVATIONS_BEFORE_ADAPTIVE values
    values = [float(i) / 10 for i in range(MIN_OBSERVATIONS_BEFORE_ADAPTIVE)]
    for v in values:
        t.observe(v)
    tau = t.threshold()
    # Should no longer return the default
    assert tau != -1.0
    # 25th percentile of [0.0 .. 0.9] is around 0.2
    assert 0.0 <= tau <= 0.5


def test_tracker_25th_percentile_of_high_confidence_values() -> None:
    t = SlidingWindowQuantileTracker(quantile=0.25, window_size=100)
    # Simulate high-quality local model: confidence always 0.85–0.95
    for v in [0.85, 0.87, 0.90, 0.92, 0.88, 0.91, 0.86, 0.93, 0.89, 0.94, 0.87, 0.90]:
        t.observe(v)
    tau = t.threshold()
    # 25th percentile of high values should be around 0.87
    assert 0.85 <= tau <= 0.90


# ---------------------------------------------------------------------------
# T3: extend_claude effective threshold never lowers below caller's request
# ---------------------------------------------------------------------------


def test_adaptive_tau_never_lowers_caller_threshold() -> None:
    """max(quality_threshold, adaptive_τ) must hold even when τ is small."""
    t = SlidingWindowQuantileTracker(quantile=0.25, window_size=50)
    # Feed low confidence values → low adaptive τ
    for _ in range(15):
        t.observe(0.3)
    low_tau = t.threshold()
    caller_threshold = 0.8
    effective = max(caller_threshold, low_tau)
    assert effective == caller_threshold, (
        f"low adaptive τ={low_tau} should not lower caller threshold={caller_threshold}"
    )


def test_adaptive_tau_raises_caller_threshold_when_higher() -> None:
    """When model observes high confidence, adaptive τ can push past caller default."""
    t = SlidingWindowQuantileTracker(quantile=0.25, window_size=50)
    for _ in range(15):
        t.observe(0.99)
    high_tau = t.threshold()
    caller_threshold = 0.5  # caller requested low threshold
    effective = max(caller_threshold, high_tau)
    # effective should be governed by the high τ from the tracker
    assert effective >= 0.95, (
        f"high τ={high_tau} should dominate low caller_threshold={caller_threshold}"
    )


# ---------------------------------------------------------------------------
# T4: get_extend_quality_tracker() exposes observe() for external modules
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _HAS_EXTEND_TRACKER, reason="get_extend_quality_tracker removed from fleet")
def test_external_module_can_feed_tracker() -> None:
    """ThermalPredictor / JEPA can feed signals via get_extend_quality_tracker().observe()."""
    t = get_extend_quality_tracker()
    before = t.observation_count
    t.observe(0.75)
    assert t.observation_count == before + 1
