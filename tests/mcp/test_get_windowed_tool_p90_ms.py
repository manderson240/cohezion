"""Item 1028: get_windowed_tool_p90_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- 90th percentile of latency_ms in window.

Thin delegate to get_windowed_latency_percentile(tool, 90.0, ...).
0.0 for unknown/empty tool. Injectable store. Pure function.
Extends high-tail coverage above p75.

PRIMARY DISC.: lats [10, 20, 30, 40, 50]
  idx = 0.90 * (5-1) = 3.6
  lo = sorted[3] = 40, hi = sorted[4] = 50, frac = 0.6
  p90 = 40 + 0.6*(50-40) = 46.0
  (kills max=50.0; kills p75=32.5; correct interpolated=46.0 float).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_p90_ms,
    get_windowed_latency_percentile,
    get_windowed_tool_p75_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_p90_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,20,30,40,50] -> p90=46.0.

    Kills max=50.0 (above the 90th percentile value).
    Kills p75=32.5 (wrong percentile level).
    Correct: idx=3.6 -> 40+0.6*(50-40)=46.0.
    """
    _reset()
    store = _make_store({
        "p90_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
    })
    result = get_windowed_tool_p90_ms("p90_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 46.0) < 1e-9, (
        f"p90=46.0; kills max=50 or p75=32.5; got {result}"
    )


def test_p90_delegates_to_percentile_function() -> None:
    """p90 must equal get_windowed_latency_percentile(tool, 90.0, ...)."""
    _reset()
    store = _make_store({
        "p90_del": [(_NOW - 10, float(v), True) for v in [100, 200, 300, 400, 500]],
    })
    p90 = get_windowed_tool_p90_ms("p90_del", _WIN, store=store, now_ms=_NOW)
    ref = get_windowed_latency_percentile("p90_del", 90.0, _WIN, store=store, now_ms=_NOW)
    assert p90 == ref, f"p90={p90} must equal percentile(90.0)={ref}"


def test_p90_greater_than_or_equal_p75() -> None:
    """p90 >= p75 always (ordering invariant)."""
    _reset()
    store = _make_store({
        "p90_ord": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50, 60, 70, 80]],
    })
    p90 = get_windowed_tool_p90_ms("p90_ord", _WIN, store=store, now_ms=_NOW)
    p75 = get_windowed_tool_p75_ms("p90_ord", _WIN, store=store, now_ms=_NOW)
    assert p90 >= p75, f"p90={p90} must be >= p75={p75}"


def test_p90_single_call_returns_that_latency() -> None:
    """Single call -> p90 == that call's latency."""
    _reset()
    store = _make_store({
        "p90_one": [(_NOW - 10, 137.0, True)],
    })
    result = get_windowed_tool_p90_ms("p90_one", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 137.0) < 1e-9, f"single call -> p90=137.0; got {result}"


def test_p90_all_equal_returns_that_value() -> None:
    """All equal -> p90 == that value."""
    _reset()
    store = _make_store({
        "p90_eq": [(_NOW - 10, 200.0, True)] * 5,
    })
    result = get_windowed_tool_p90_ms("p90_eq", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 200.0) < 1e-9, f"all equal -> p90=200.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    result = get_windowed_tool_p90_ms("no_such_p90", _WIN, store={}, now_ms=_NOW)
    assert result == 0.0 or result is None, f"unknown tool -> 0.0 or None; got {result}"


def test_no_recent_calls_returns_zero_or_none() -> None:
    """All calls outside window -> 0.0 or None."""
    _reset()
    store = _make_store({
        "p90_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
    })
    result = get_windowed_tool_p90_ms("p90_old", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0 or result is None, f"no recent -> 0.0 or None; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"p90_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    result = get_windowed_tool_p90_ms("p90_rt", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
