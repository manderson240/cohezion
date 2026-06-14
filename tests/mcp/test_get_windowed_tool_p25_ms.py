"""Item 1010: get_windowed_tool_p25_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool 25th-percentile latency in window.

Named convenience alias for get_windowed_latency_percentile(tool_name, 25.0, window_ms, ...).
0.0 for unknown/empty tool. Injectable store. Pure function.
Completes the named-percentile quintet: p25/p50/p75/p95/p99.
p25 is the lower quartile; IQR = p75 - p25.

PRIMARY DISC.: lats [10,20,50,100,200,300,500,1000] (n=8)
  idx = 25/100 * (8-1) = 1.75
  floor=1 -> sorted[1]=20, ceil=2 -> sorted[2]=50
  interpolated = 20 + 0.75*(50-20) = 42.5
  (kills floor=20.0; kills ceil=50.0; kills naive index=sorted[1]=20.0).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_p25_ms,
    get_windowed_latency_percentile,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_p25_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,20,50,100,200,300,500,1000] -> 42.5.

    idx=1.75 -> 20 + 0.75*(50-20) = 42.5.
    Kills floor-only=20.0.
    Kills ceil-only=50.0.
    Kills naive sorted[1]=20.0.
    """
    _reset()
    store = _make_store(
        {
            "p25_a": [(_NOW - 10, float(v), True) for v in [10, 20, 50, 100, 200, 300, 500, 1000]],
        }
    )
    result = get_windowed_tool_p25_ms("p25_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 42.5) < 1e-9, (
        f"interpolated p25=42.5; kills floor=20 or ceil=50; got {result}"
    )


def test_p25_equals_generic_percentile() -> None:
    """p25 == get_windowed_latency_percentile(tool, 25.0, window, ...)."""
    _reset()
    store = _make_store(
        {
            "p25_eq": [(_NOW - 10, float(v), True) for v in [50, 100, 150, 200, 250]],
        }
    )
    p25 = get_windowed_tool_p25_ms("p25_eq", _WIN, store=store, now_ms=_NOW)
    generic = get_windowed_latency_percentile("p25_eq", 25.0, _WIN, store=store, now_ms=_NOW)
    assert abs(p25 - generic) < 1e-9, f"p25={p25} must equal generic percentile={generic}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_p25_ms("no_such_p25", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "p25_old": [(_NOW - _WIN - 100, 9999.0, True)] * 5,
        }
    )
    assert get_windowed_tool_p25_ms("p25_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_single_call_returns_that_latency() -> None:
    """Single call -> p25 == that latency."""
    _reset()
    store = _make_store(
        {
            "p25_one": [(_NOW - 10, 77.0, True)],
        }
    )
    result = get_windowed_tool_p25_ms("p25_one", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 77.0) < 1e-9, f"single call -> p25=77.0; got {result}"


def test_p25_le_p75() -> None:
    """p25 <= p75 for any non-empty window (lower quartile <= upper quartile)."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_p75_ms

    _reset()
    store = _make_store(
        {
            "p25_ord": [(_NOW - 10, float(v), True) for v in [10, 30, 70, 90, 150]],
        }
    )
    p25 = get_windowed_tool_p25_ms("p25_ord", _WIN, store=store, now_ms=_NOW)
    p75 = get_windowed_tool_p75_ms("p25_ord", _WIN, store=store, now_ms=_NOW)
    assert p25 <= p75, f"p25={p25} must be <= p75={p75}"


def test_p25_le_p50() -> None:
    """p25 <= p50 (lower quartile <= median)."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_p50_ms

    _reset()
    store = _make_store(
        {
            "p25_ord2": [(_NOW - 10, float(v), True) for v in [10, 30, 70, 90, 150, 300]],
        }
    )
    p25 = get_windowed_tool_p25_ms("p25_ord2", _WIN, store=store, now_ms=_NOW)
    p50 = get_windowed_tool_p50_ms("p25_ord2", _WIN, store=store, now_ms=_NOW)
    assert p25 <= p50, f"p25={p25} must be <= p50={p50}"


def test_iqr_from_p75_minus_p25() -> None:
    """IQR = p75 - p25 matches get_windowed_tool_latency_iqr_ms."""
    from cohezion.mcp.compound_mcp_telemetry import (
        get_windowed_tool_p75_ms,
        get_windowed_tool_latency_iqr_ms,
    )

    _reset()
    store = _make_store(
        {
            "p25_iqr": [
                (_NOW - 10, float(v), True) for v in [10, 20, 50, 100, 200, 300, 500, 1000]
            ],
        }
    )
    p25 = get_windowed_tool_p25_ms("p25_iqr", _WIN, store=store, now_ms=_NOW)
    p75 = get_windowed_tool_p75_ms("p25_iqr", _WIN, store=store, now_ms=_NOW)
    iqr = get_windowed_tool_latency_iqr_ms("p25_iqr", _WIN, store=store, now_ms=_NOW)
    assert abs((p75 - p25) - iqr) < 1e-9, f"p75-p25={p75 - p25} must equal iqr={iqr}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"p25_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 200]]})
    assert isinstance(get_windowed_tool_p25_ms("p25_rt", _WIN, store=store, now_ms=_NOW), float)
