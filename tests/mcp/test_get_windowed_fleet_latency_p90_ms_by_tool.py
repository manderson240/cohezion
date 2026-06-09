"""Item 1199: get_windowed_fleet_latency_p90_ms_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool 90th-percentile latency within the window.
Returns float. 0.0 for unknown/empty tool or all calls outside window.
Thin wrapper: get_windowed_fleet_latency_percentile_ms_by_tool(..., 90, ...).
Nearest-rank: ceil(0.90 * n) - 1 (0-based index).

PRIMARY DISC.:
  tool_a=[10,20,30,40,50] → p90=50.0 (idx=4)
  tool_b=[100,200,300,400,500] → p90=500.0 (idx=4)
  p90_a=50.0 kills p90_b=500.0; kills always-0.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_p90_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_p90_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: p90_a=50.0 kills p90_b=500.0; kills always-0."""
    _reset()
    store = _make_store({
        "fp90bt_a": [
            (_NOW - float(900 - i*150), float(v), True)
            for i, v in enumerate([10, 20, 30, 40, 50])
        ],
        "fp90bt_b": [
            (_NOW - float(900 - i*150), float(v), True)
            for i, v in enumerate([100, 200, 300, 400, 500])
        ],
    })
    p90_a = get_windowed_fleet_latency_p90_ms_by_tool(
        _WIN, "fp90bt_a", store=store, now_ms=_NOW
    )
    p90_b = get_windowed_fleet_latency_p90_ms_by_tool(
        _WIN, "fp90bt_b", store=store, now_ms=_NOW
    )
    assert isinstance(p90_a, float), f"expected float, got {type(p90_a)}"
    assert p90_a == 50.0, (
        f"p90_a=50.0 (idx=4 of [10..50]); kills p90_b=500/always-0; got {p90_a}"
    )
    assert p90_b == 500.0, f"p90_b=500.0; got {p90_b}"


def test_fleet_p90_by_tool_single_call() -> None:
    """Single call → that latency is p90."""
    _reset()
    store = _make_store({
        "fp90bt_one": [(_NOW - 500, 99.0, True)],
    })
    result = get_windowed_fleet_latency_p90_ms_by_tool(
        _WIN, "fp90bt_one", store=store, now_ms=_NOW
    )
    assert result == 99.0


def test_fleet_p90_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store({
        "fp90bt_other": [(_NOW - 500, 50.0, True)],
    })
    result = get_windowed_fleet_latency_p90_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_p90_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_p90_ms_by_tool(
        _WIN, "any_tool", store={}, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_p90_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store({
        "fp90bt_old": [
            (_NOW - _WIN - 200, 10.0, True),
            (_NOW - _WIN - 100, 50.0, True),
        ],
    })
    result = get_windowed_fleet_latency_p90_ms_by_tool(
        _WIN, "fp90bt_old", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_p90_is_above_median() -> None:
    """p90 is at or above the median (sanity check)."""
    _reset()
    store = _make_store({
        "fp90bt_cmp": [
            (_NOW - float(900 - i*150), float(v), True)
            for i, v in enumerate([10, 20, 30, 40, 50])
        ],
    })
    p90 = get_windowed_fleet_latency_p90_ms_by_tool(
        _WIN, "fp90bt_cmp", store=store, now_ms=_NOW
    )
    # p50 = ceil(0.5*5)-1 = 2 → sorted[2] = 30.0
    assert p90 >= 30.0, f"p90 should be at or above median=30; got {p90}"


def test_fleet_p90_all_same_latency() -> None:
    """All same latency → p90 == that value."""
    _reset()
    store = _make_store({
        "fp90bt_flat": [(_NOW - float(d), 77.0, True) for d in [900, 600, 300]],
    })
    result = get_windowed_fleet_latency_p90_ms_by_tool(
        _WIN, "fp90bt_flat", store=store, now_ms=_NOW
    )
    assert result == 77.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fp90bt_rt": [
            (_NOW - float(900 - i*150), float(v), True)
            for i, v in enumerate([10, 20, 30, 40, 50])
        ],
    })
    result = get_windowed_fleet_latency_p90_ms_by_tool(
        _WIN, "fp90bt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert result == 50.0
