"""Item 1008: get_windowed_tool_p75_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool 75th-percentile latency in window.

Named convenience alias for get_windowed_latency_percentile(tool_name, 75.0, window_ms, ...).
0.0 for unknown/empty tool. Injectable store. Pure function.

PRIMARY DISC.: lats [10,20,50,100,200,300,500,1000] (n=8)
  idx = 75/100 * (8-1) = 5.25
  floor=5 -> sorted[5]=300, ceil=6 -> sorted[6]=500
  interpolated = 300 + 0.25*(500-300) = 350.0
  (kills floor=300.0; kills ceil=500.0; kills naive 75th=sorted[5]=300).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_p75_ms,
    get_windowed_latency_percentile,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_p75_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,20,50,100,200,300,500,1000] -> 350.0.

    idx=5.25 -> 300 + 0.25*(500-300) = 350.0.
    Kills floor-only=300.0.
    Kills ceil-only=500.0.
    Kills naive index=sorted[5]=300.0.
    """
    _reset()
    store = _make_store({
        "p75_a": [(_NOW - 10, float(v), True) for v in [10, 20, 50, 100, 200, 300, 500, 1000]],
    })
    result = get_windowed_tool_p75_ms("p75_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 350.0) < 1e-9, (
        f"interpolated p75=350.0; kills floor=300 or ceil=500; got {result}"
    )


def test_p75_equals_generic_percentile() -> None:
    """p75 == get_windowed_latency_percentile(tool, 75.0, window, ...)."""
    _reset()
    store = _make_store({
        "p75_eq": [(_NOW - 10, float(v), True) for v in [50, 100, 150, 200, 250]],
    })
    p75 = get_windowed_tool_p75_ms("p75_eq", _WIN, store=store, now_ms=_NOW)
    generic = get_windowed_latency_percentile("p75_eq", 75.0, _WIN, store=store, now_ms=_NOW)
    assert abs(p75 - generic) < 1e-9, (
        f"p75={p75} must equal generic percentile={generic}"
    )


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_p75_ms("no_such_p75", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "p75_old": [(_NOW - _WIN - 100, 9999.0, True)] * 5,
    })
    assert get_windowed_tool_p75_ms("p75_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_single_call_returns_that_latency() -> None:
    """Single call -> p75 == that latency (single-element percentile)."""
    _reset()
    store = _make_store({
        "p75_one": [(_NOW - 10, 123.0, True)],
    })
    result = get_windowed_tool_p75_ms("p75_one", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 123.0) < 1e-9, f"single call -> p75=123.0; got {result}"


def test_p75_ge_p50() -> None:
    """p75 >= p50 for any non-empty window."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_p50_ms
    _reset()
    store = _make_store({
        "p75_ord": [(_NOW - 10, float(v), True) for v in [10, 30, 70, 90, 150]],
    })
    p75 = get_windowed_tool_p75_ms("p75_ord", _WIN, store=store, now_ms=_NOW)
    p50 = get_windowed_tool_p50_ms("p75_ord", _WIN, store=store, now_ms=_NOW)
    assert p75 >= p50, f"p75={p75} must be >= p50={p50}"


def test_p75_le_p99() -> None:
    """p75 <= p99 for any non-empty window."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_p99_ms
    _reset()
    store = _make_store({
        "p75_ord2": [(_NOW - 10, float(v), True) for v in [10, 30, 70, 90, 150, 300, 500]],
    })
    p75 = get_windowed_tool_p75_ms("p75_ord2", _WIN, store=store, now_ms=_NOW)
    p99 = get_windowed_tool_p99_ms("p75_ord2", _WIN, store=store, now_ms=_NOW)
    assert p75 <= p99, f"p75={p75} must be <= p99={p99}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"p75_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 200]]})
    assert isinstance(get_windowed_tool_p75_ms("p75_rt", _WIN, store=store, now_ms=_NOW), float)
