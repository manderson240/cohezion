"""Item 1191: get_windowed_fleet_latency_recent_trend_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool latency trend (OLS linear regression slope, ms per ms elapsed).
Returns float. 0.0 for unknown/empty tool or fewer than 2 calls.
Positive slope = latency increasing; negative = improving.

PRIMARY DISC.:
  tool_a: timestamps at [_NOW-500, _NOW-0], latencies [10, 110] → slope = +0.2 (rising)
  tool_b: timestamps at [_NOW-500, _NOW-0], latencies [110, 10] → slope = -0.2 (falling)
  slope_a > 0 kills slope_b < 0; kills always-0.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_recent_trend_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_trend_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: slope_a > 0 kills slope_b < 0; kills always-0."""
    _reset()
    store = _make_store({
        "ftrdbt_a": [
            (_NOW - 500.0, 10.0, True),   # earlier, lower latency
            (_NOW - 0.001, 110.0, True),  # later, higher latency → rising
        ],
        "ftrdbt_b": [
            (_NOW - 500.0, 110.0, True),  # earlier, higher latency
            (_NOW - 0.001, 10.0, True),   # later, lower latency → falling
        ],
    })
    slope_a = get_windowed_fleet_latency_recent_trend_by_tool(
        _WIN, "ftrdbt_a", store=store, now_ms=_NOW
    )
    slope_b = get_windowed_fleet_latency_recent_trend_by_tool(
        _WIN, "ftrdbt_b", store=store, now_ms=_NOW
    )
    assert isinstance(slope_a, float), f"expected float, got {type(slope_a)}"
    assert slope_a > 0, (
        f"slope_a (rising latency) should be > 0; kills slope_b<0/always-0; got {slope_a}"
    )
    assert slope_b < 0, (
        f"slope_b (falling latency) should be < 0; got {slope_b}"
    )


def test_fleet_trend_by_tool_exact_slope() -> None:
    """Two-point OLS: slope = (lat2 - lat1) / (t2 - t1)."""
    _reset()
    store = _make_store({
        "ftrdbt_exact": [
            (_NOW - 500.0, 10.0, True),
            (_NOW - 0.001, 110.0, True),
        ],
    })
    slope = get_windowed_fleet_latency_recent_trend_by_tool(
        _WIN, "ftrdbt_exact", store=store, now_ms=_NOW
    )
    # slope = (110-10) / ((_NOW-0.001) - (_NOW-500.0)) = 100 / 499.999 ≈ 0.2
    expected = 100.0 / 499.999
    assert abs(slope - expected) < 1e-6, f"exact slope; got {slope}"


def test_fleet_trend_by_tool_flat_returns_zero() -> None:
    """Constant latency → slope == 0.0."""
    _reset()
    store = _make_store({
        "ftrdbt_flat": [
            (_NOW - 900, 50.0, True),
            (_NOW - 600, 50.0, True),
            (_NOW - 300, 50.0, True),
        ],
    })
    slope = get_windowed_fleet_latency_recent_trend_by_tool(
        _WIN, "ftrdbt_flat", store=store, now_ms=_NOW
    )
    assert abs(slope) < 1e-9, f"constant latency → slope=0; got {slope}"


def test_fleet_trend_by_tool_single_call_returns_zero() -> None:
    """Single call → fewer than 2 points → 0.0."""
    _reset()
    store = _make_store({
        "ftrdbt_one": [(_NOW - 500, 50.0, True)],
    })
    slope = get_windowed_fleet_latency_recent_trend_by_tool(
        _WIN, "ftrdbt_one", store=store, now_ms=_NOW
    )
    assert abs(slope) < 1e-9


def test_fleet_trend_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store({
        "ftrdbt_other": [(_NOW - 500, 10.0, True)],
    })
    slope = get_windowed_fleet_latency_recent_trend_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert abs(slope) < 1e-9
    assert isinstance(slope, float)


def test_fleet_trend_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    slope = get_windowed_fleet_latency_recent_trend_by_tool(
        _WIN, "any_tool", store={}, now_ms=_NOW
    )
    assert abs(slope) < 1e-9


def test_fleet_trend_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store({
        "ftrdbt_old": [
            (_NOW - _WIN - 300, 10.0, True),
            (_NOW - _WIN - 100, 110.0, True),
        ],
    })
    slope = get_windowed_fleet_latency_recent_trend_by_tool(
        _WIN, "ftrdbt_old", store=store, now_ms=_NOW
    )
    assert abs(slope) < 1e-9


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "ftrdbt_rt": [
            (_NOW - 800, 10.0, True),
            (_NOW - 400, 60.0, True),
        ],
    })
    slope = get_windowed_fleet_latency_recent_trend_by_tool(
        _WIN, "ftrdbt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(slope, float)
    assert slope > 0  # 10 → 60ms over time: rising
