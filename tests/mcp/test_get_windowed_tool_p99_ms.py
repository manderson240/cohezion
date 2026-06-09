"""Item 992: get_windowed_tool_p99_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool p99 latency standalone shortcut.

PRIMARY DISC.: lats [10, 20, 30, 40, 50] -> p99=49.6
(not p95=48.0; not max=50.0; idx=0.99*(5-1)=3.96 -> 40+0.96*(50-40)=49.6).
unknown -> 0.0; consistent with get_windowed_latency_percentile(tool, 99, ...); returns float.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_p99_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_p99_primary_discriminator() -> None:
    """FALSIFIABLE: lats [10,20,30,40,50] -> p99=49.6 (not p95=48.0, not max=50.0)."""
    _reset()
    store = _make_store({
        "wp99_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
    })
    result = get_windowed_tool_p99_ms("wp99_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    # idx = 0.99 * (5-1) = 3.96; sorted=[10,20,30,40,50]
    # 40 + 0.96*(50-40) = 40 + 9.6 = 49.6
    assert abs(result - 49.6) < 0.001   # not p95=48.0, not max=50.0


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_p99_ms("no_such_wp99", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    store = _make_store({
        "wp99_old": [(_NOW - _WIN - 100, 50.0, True)] * 3,
    })
    assert get_windowed_tool_p99_ms("wp99_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_consistent_with_latency_percentile_99() -> None:
    """p99_ms == get_windowed_latency_percentile(tool, 99, ...)."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_latency_percentile
    store = _make_store({
        "wp99_cons": [(_NOW - 10, float(v * 10), True) for v in range(1, 11)],
    })
    shortcut = get_windowed_tool_p99_ms("wp99_cons", _WIN, store=store, now_ms=_NOW)
    generic = get_windowed_latency_percentile("wp99_cons", 99.0, _WIN, store=store, now_ms=_NOW)
    assert abs(shortcut - generic) < 0.001


def test_p99_ge_p95() -> None:
    """p99 >= p95 >= p50 for any non-empty window (order constraint)."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_p95_ms, get_windowed_tool_p50_ms
    store = _make_store({
        "wp99_ord": [(_NOW - 10, float(v * 10), True) for v in range(1, 11)],
    })
    p50 = get_windowed_tool_p50_ms("wp99_ord", _WIN, store=store, now_ms=_NOW)
    p95 = get_windowed_tool_p95_ms("wp99_ord", _WIN, store=store, now_ms=_NOW)
    p99 = get_windowed_tool_p99_ms("wp99_ord", _WIN, store=store, now_ms=_NOW)
    assert p99 >= p95 >= p50


def test_single_call_returns_that_value() -> None:
    """Single call -> p99 = that value."""
    store = _make_store({"wp99_one": [(_NOW - 10, 42.0, True)]})
    assert abs(get_windowed_tool_p99_ms("wp99_one", _WIN, store=store, now_ms=_NOW) - 42.0) < 0.001


def test_returns_float_type() -> None:
    """Return type is float."""
    store = _make_store({"rtype_wp99": [(_NOW - 10, float(v), True) for v in range(1, 6)]})
    assert isinstance(get_windowed_tool_p99_ms("rtype_wp99", _WIN, store=store, now_ms=_NOW), float)
