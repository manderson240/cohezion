"""Item 990: get_windowed_tool_p50_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool p50 (median) latency standalone shortcut.

PRIMARY DISC.: lats [10, 20, 30, 40, 90] -> p50=30.0 (not mean=38.0, not max=90.0).
unknown -> 0.0; consistent with get_windowed_latency_percentile(tool, 50, ...); returns float.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_p50_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_p50_primary_discriminator() -> None:
    """FALSIFIABLE: lats [10,20,30,40,90] -> p50=30.0 (not mean=38.0, not max=90.0)."""
    _reset()
    store = _make_store({
        "wp50_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 90]],
    })
    result = get_windowed_tool_p50_ms("wp50_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 30.0) < 0.001   # not mean=38.0, not max=90.0


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_p50_ms("no_such_wp50", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    store = _make_store({
        "wp50_old": [(_NOW - _WIN - 100, 50.0, True)] * 3,
    })
    assert get_windowed_tool_p50_ms("wp50_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_consistent_with_latency_percentile_50() -> None:
    """p50_ms == get_windowed_latency_percentile(tool, 50, ...)."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_latency_percentile
    store = _make_store({
        "wp50_cons": [(_NOW - 10, float(v), True) for v in [5, 15, 25, 35, 45]],
    })
    shortcut = get_windowed_tool_p50_ms("wp50_cons", _WIN, store=store, now_ms=_NOW)
    generic = get_windowed_latency_percentile("wp50_cons", 50.0, _WIN, store=store, now_ms=_NOW)
    assert abs(shortcut - generic) < 0.001


def test_even_count_p50() -> None:
    """Even number of values: p50 via linear interpolation."""
    store = _make_store({
        "wp50_even": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40]],
    })
    result = get_windowed_tool_p50_ms("wp50_even", _WIN, store=store, now_ms=_NOW)
    # 4 values sorted: [10,20,30,40]; idx = 0.5*(4-1)=1.5; 20+0.5*(30-20)=25.0
    assert abs(result - 25.0) < 0.001


def test_single_call_returns_that_value() -> None:
    """Single call -> p50 = that value."""
    store = _make_store({"wp50_one": [(_NOW - 10, 42.0, True)]})
    assert abs(get_windowed_tool_p50_ms("wp50_one", _WIN, store=store, now_ms=_NOW) - 42.0) < 0.001


def test_returns_float_type() -> None:
    """Return type is float."""
    store = _make_store({"rtype_wp50": [(_NOW - 10, 5.0, True)] * 3})
    assert isinstance(get_windowed_tool_p50_ms("rtype_wp50", _WIN, store=store, now_ms=_NOW), float)
