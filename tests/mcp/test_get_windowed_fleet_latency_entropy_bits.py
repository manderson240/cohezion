"""Item 1146: get_windowed_fleet_latency_entropy_bits(window_ms, n_bins=10, *, store=None, now_ms=None) -> float
-- fleet-wide Shannon entropy (bits) of pooled latency histogram.
Bins latencies into n_bins equal-width buckets, computes p_i = count_i/total,
returns -sum(p_i * log2(p_i)) for non-zero bins.
Returns float >= 0.0. 0.0 for empty window or single distinct value. Max = log2(n_bins).

PRIMARY DISC.:
  pooled [10, 10, 90, 90] with n_bins=2:
  bin[0] covers [10..50): count=2, p=0.5
  bin[1] covers [50..90]: count=2, p=0.5
  entropy = -(0.5*log2(0.5) + 0.5*log2(0.5)) = -2*(0.5*(-1)) = 1.0 bit

  Single-value [50, 50, 50] with any n_bins -> all in one bin -> entropy=0.0
  (PRIMARY DISC.: kills always-zero; kills always-max).
"""
from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_entropy_bits,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_entropy_two_equal_bins_is_one_bit() -> None:
    """PRIMARY DISC.: two equal bins -> entropy=1.0 bit."""
    _reset()
    store = _make_store({
        "fent_a": [(_NOW - 700, 10.0, True), (_NOW - 600, 10.0, True)],
        "fent_b": [(_NOW - 500, 90.0, True), (_NOW - 400, 90.0, True)],
    })
    # n_bins=2: bin[10..50)=count 2, bin[50..90]=count 2; entropy=1.0 bit
    result = get_windowed_fleet_latency_entropy_bits(_WIN, 2, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 1.0) < 1e-9, (
        f"two equal bins -> entropy=1.0 bit; got {result}"
    )


def test_fleet_entropy_single_bin_returns_zero() -> None:
    """All values in one bin -> entropy=0.0."""
    _reset()
    store = _make_store({
        "fent_flat": [(_NOW - float(d), 50.0, True) for d in [900, 800, 700, 600]],
    })
    result = get_windowed_fleet_latency_entropy_bits(_WIN, 10, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"single bin -> 0.0; got {result}"


def test_fleet_entropy_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_entropy_bits(_WIN, store={}, now_ms=_NOW)
    assert result == 0.0


def test_fleet_entropy_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "fent_old": [(_NOW - _WIN - float(d), float(d), True) for d in [300, 200, 100]],
    })
    result = get_windowed_fleet_latency_entropy_bits(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0


def test_fleet_entropy_max_is_log2_n_bins() -> None:
    """Uniform distribution across n_bins -> entropy = log2(n_bins)."""
    _reset()
    n_bins = 4
    # Create 4 well-separated values, one per bin
    store = _make_store({
        "fent_unif": [
            (_NOW - 700, 5.0, True),    # bin 0: [0..25)
            (_NOW - 600, 30.0, True),   # bin 1: [25..50)
            (_NOW - 500, 55.0, True),   # bin 2: [50..75)
            (_NOW - 400, 80.0, True),   # bin 3: [75..80]
        ],
    })
    result = get_windowed_fleet_latency_entropy_bits(_WIN, n_bins, store=store, now_ms=_NOW)
    expected_max = math.log2(n_bins)
    assert abs(result - expected_max) < 1e-9, (
        f"uniform across {n_bins} bins -> entropy={expected_max:.4f}; got {result}"
    )


def test_fleet_entropy_nonnegative() -> None:
    """Entropy is always >= 0."""
    _reset()
    store = _make_store({
        "fent_nn": [(_NOW - float(d), float(v), True)
                    for d, v in zip([900, 800, 700, 600, 500], [1, 10, 50, 100, 1000])],
    })
    result = get_windowed_fleet_latency_entropy_bits(_WIN, store=store, now_ms=_NOW)
    assert result >= 0.0, f"entropy must be >= 0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fent_rt_a": [(_NOW - 400, 10.0, True)],
        "fent_rt_b": [(_NOW - 200, 90.0, True)],
    })
    result = get_windowed_fleet_latency_entropy_bits(_WIN, 2, store=store, now_ms=_NOW)
    assert isinstance(result, float)
