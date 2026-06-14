"""Item 1032: get_windowed_tool_latency_mad_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- Median Absolute Deviation (MAD) of latency in window.

MAD = median(|lat - median(lats)|) for all calls in window.
0.0 for empty/unknown tool. Injectable store. Pure function.
Robust spread measure: insensitive to extreme outliers (unlike stddev).

PRIMARY DISC.: lats [10, 20, 30, 40, 100]
  sorted -> median = 30.0
  abs_deviations = [|10-30|, |20-30|, |30-30|, |40-30|, |100-30|] = [20, 10, 0, 10, 70]
  sorted_devs = [0, 10, 10, 20, 70]
  MAD = median([0, 10, 10, 20, 70]) = 10.0
  (PRIMARY DISC.: kills stddev≈32.0; kills mean_abs_dev=24.0; kills range=90.0;
   correct MAD=10.0 float).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_mad_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def _mad(lats: list[float]) -> float:
    """Reference implementation."""
    n = len(lats)
    if n == 0:
        return 0.0
    s = sorted(lats)
    mid = n // 2
    med = s[mid] if n % 2 == 1 else (s[mid - 1] + s[mid]) / 2.0
    devs = sorted(abs(x - med) for x in lats)
    mid2 = n // 2
    return devs[mid2] if n % 2 == 1 else (devs[mid2 - 1] + devs[mid2]) / 2.0


def test_mad_primary_discriminator() -> None:
    """PRIMARY DISC.: [10, 20, 30, 40, 100] -> MAD=10.0.

    Kills stddev≈32.0 (sensitive to outlier 100).
    Kills mean_abs_dev=24.0 (uses mean not median).
    Kills range=90.0 (max-min not MAD).
    Correct: median=30, MAD=median([0,10,10,20,70])=10.0.
    """
    _reset()
    store = _make_store(
        {
            "mad_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 100]],
        }
    )
    result = get_windowed_tool_latency_mad_ms("mad_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 10.0) < 1e-9, (
        f"MAD=10.0; kills stddev≈32/mean_abs=24/range=90; got {result}"
    )


def test_mad_matches_reference_implementation() -> None:
    """MAD must equal the reference median-of-absolute-deviations formula."""
    _reset()
    lats = [50.0, 150.0, 200.0, 50.0, 300.0, 100.0]
    store = _make_store(
        {
            "mad_ref": [(_NOW - 10, v, True) for v in lats],
        }
    )
    result = get_windowed_tool_latency_mad_ms("mad_ref", _WIN, store=store, now_ms=_NOW)
    expected = _mad(lats)
    assert abs(result - expected) < 1e-9, f"expected={expected}; got {result}"


def test_all_equal_mad_zero() -> None:
    """All equal latencies -> MAD=0.0 (all deviations are 0)."""
    _reset()
    store = _make_store(
        {
            "mad_eq": [(_NOW - 10, 100.0, True)] * 5,
        }
    )
    result = get_windowed_tool_latency_mad_ms("mad_eq", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"all-equal -> MAD=0.0; got {result}"


def test_single_call_mad_zero() -> None:
    """Single call -> MAD=0.0 (deviation from itself is 0)."""
    _reset()
    store = _make_store(
        {
            "mad_one": [(_NOW - 10, 75.0, True)],
        }
    )
    result = get_windowed_tool_latency_mad_ms("mad_one", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"single call -> MAD=0.0; got {result}"


def test_mad_robust_to_outliers() -> None:
    """MAD is much smaller than stddev when there's an extreme outlier."""
    _reset()
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_latency_stddev_ms

    # 9 calls at 10ms, one extreme outlier at 10000ms
    lats = [10.0] * 9 + [10000.0]
    store = _make_store(
        {
            "mad_rob": [(_NOW - 10, v, True) for v in lats],
        }
    )
    mad = get_windowed_tool_latency_mad_ms("mad_rob", _WIN, store=store, now_ms=_NOW)
    stddev = get_windowed_tool_latency_stddev_ms("mad_rob", _WIN, store=store, now_ms=_NOW)
    assert mad < stddev, f"MAD={mad} must be << stddev={stddev} with outlier"
    assert mad == 0.0, f"median is 10, MAD of mostly-10s = 0.0; got {mad}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_mad_ms("no_such_mad", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "mad_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
        }
    )
    assert get_windowed_tool_latency_mad_ms("mad_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"mad_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    assert isinstance(
        get_windowed_tool_latency_mad_ms("mad_rt", _WIN, store=store, now_ms=_NOW), float
    )
