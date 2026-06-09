"""Item 1193: get_windowed_fleet_latency_floor_ms_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool floor (minimum) latency within the window (alias for min).
Returns float. 0.0 for unknown/empty tool or all calls outside window.

PRIMARY DISC.:
  tool_a=[200,50,10] → floor=10.0
  tool_b=[300,150,25] → floor=25.0
  floor_a=10.0 kills floor_b=25.0; kills always-0.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_floor_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_floor_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: floor_a=10.0 kills floor_b=25.0; kills always-0."""
    _reset()
    store = _make_store({
        "fflbt_a": [
            (_NOW - 900, 200.0, True),
            (_NOW - 600, 50.0, True),
            (_NOW - 300, 10.0, True),
        ],
        "fflbt_b": [
            (_NOW - 800, 300.0, True),
            (_NOW - 500, 150.0, True),
            (_NOW - 200, 25.0, True),
        ],
    })
    floor_a = get_windowed_fleet_latency_floor_ms_by_tool(
        _WIN, "fflbt_a", store=store, now_ms=_NOW
    )
    floor_b = get_windowed_fleet_latency_floor_ms_by_tool(
        _WIN, "fflbt_b", store=store, now_ms=_NOW
    )
    assert isinstance(floor_a, float), f"expected float, got {type(floor_a)}"
    assert floor_a == 10.0, (
        f"floor_a=10.0 kills floor_b=25.0/always-0; got {floor_a}"
    )
    assert floor_b == 25.0, f"floor_b should be 25.0; got {floor_b}"


def test_fleet_floor_by_tool_single_call() -> None:
    """Single call → its latency is the floor."""
    _reset()
    store = _make_store({
        "fflbt_single": [(_NOW - 500, 42.0, True)],
    })
    result = get_windowed_fleet_latency_floor_ms_by_tool(
        _WIN, "fflbt_single", store=store, now_ms=_NOW
    )
    assert result == 42.0


def test_fleet_floor_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store({
        "fflbt_other": [(_NOW - 500, 100.0, True)],
    })
    result = get_windowed_fleet_latency_floor_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_floor_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_floor_ms_by_tool(
        _WIN, "any_tool", store={}, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_floor_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store({
        "fflbt_old": [
            (_NOW - _WIN - 300, 1.0, True),
            (_NOW - _WIN - 100, 2.0, True),
        ],
    })
    result = get_windowed_fleet_latency_floor_ms_by_tool(
        _WIN, "fflbt_old", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_floor_by_tool_only_window_calls_counted() -> None:
    """Calls outside window excluded; only windowed calls contribute."""
    _reset()
    store = _make_store({
        "fflbt_mix": [
            (_NOW - _WIN - 1, 0.001, True),   # outside window — if included would be min
            (_NOW - 500, 88.0, True),
            (_NOW - 200, 33.0, True),
        ],
    })
    result = get_windowed_fleet_latency_floor_ms_by_tool(
        _WIN, "fflbt_mix", store=store, now_ms=_NOW
    )
    assert result == 33.0, f"0.001ms outside window excluded; floor=33; got {result}"


def test_fleet_floor_by_tool_all_same_latency() -> None:
    """All same latency → floor == that value."""
    _reset()
    store = _make_store({
        "fflbt_flat": [(_NOW - float(d), 55.0, True) for d in [900, 600, 300]],
    })
    result = get_windowed_fleet_latency_floor_ms_by_tool(
        _WIN, "fflbt_flat", store=store, now_ms=_NOW
    )
    assert result == 55.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fflbt_rt": [
            (_NOW - 400, 99.0, True),
            (_NOW - 200, 7.0, True),
        ],
    })
    result = get_windowed_fleet_latency_floor_ms_by_tool(
        _WIN, "fflbt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert result == 7.0
