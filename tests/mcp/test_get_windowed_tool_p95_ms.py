"""Item 991: get_windowed_tool_p95_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool p95 latency standalone shortcut.

PRIMARY DISC.: lats [10, 20, 30, 40, 50] -> p95=48.0
(not p50=30.0; not max=50.0; idx=0.95*(5-1)=3.8 -> 40+0.8*(50-40)=48.0).
unknown -> 0.0; consistent with get_windowed_latency_percentile(tool, 95, ...); returns float.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_p95_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_p95_primary_discriminator() -> None:
    """FALSIFIABLE: lats [10,20,30,40,50] -> p95=48.0 (not p50=30.0, not max=50.0)."""
    _reset()
    store = _make_store(
        {
            "wp95_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
        }
    )
    result = get_windowed_tool_p95_ms("wp95_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    # idx = 0.95 * (5-1) = 3.8; sorted=[10,20,30,40,50]
    # 40 + 0.8*(50-40) = 40 + 8 = 48.0
    assert abs(result - 48.0) < 0.001  # not p50=30.0, not max=50.0


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_p95_ms("no_such_wp95", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    store = _make_store(
        {
            "wp95_old": [(_NOW - _WIN - 100, 50.0, True)] * 3,
        }
    )
    assert get_windowed_tool_p95_ms("wp95_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_consistent_with_latency_percentile_95() -> None:
    """p95_ms == get_windowed_latency_percentile(tool, 95, ...)."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_latency_percentile

    store = _make_store(
        {
            "wp95_cons": [
                (_NOW - 10, float(v), True) for v in [5, 15, 25, 35, 45, 55, 65, 75, 85, 95]
            ],
        }
    )
    shortcut = get_windowed_tool_p95_ms("wp95_cons", _WIN, store=store, now_ms=_NOW)
    generic = get_windowed_latency_percentile("wp95_cons", 95.0, _WIN, store=store, now_ms=_NOW)
    assert abs(shortcut - generic) < 0.001


def test_single_call_returns_that_value() -> None:
    """Single call -> p95 = that value (nothing above it)."""
    store = _make_store({"wp95_one": [(_NOW - 10, 42.0, True)]})
    assert abs(get_windowed_tool_p95_ms("wp95_one", _WIN, store=store, now_ms=_NOW) - 42.0) < 0.001


def test_p95_ge_p50() -> None:
    """p95 >= p50 for any non-empty window (order constraint)."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_p50_ms

    store = _make_store(
        {
            "wp95_ord": [
                (_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
            ],
        }
    )
    p50 = get_windowed_tool_p50_ms("wp95_ord", _WIN, store=store, now_ms=_NOW)
    p95 = get_windowed_tool_p95_ms("wp95_ord", _WIN, store=store, now_ms=_NOW)
    assert p95 >= p50


def test_returns_float_type() -> None:
    """Return type is float."""
    store = _make_store({"rtype_wp95": [(_NOW - 10, float(v), True) for v in range(1, 6)]})
    assert isinstance(get_windowed_tool_p95_ms("rtype_wp95", _WIN, store=store, now_ms=_NOW), float)
