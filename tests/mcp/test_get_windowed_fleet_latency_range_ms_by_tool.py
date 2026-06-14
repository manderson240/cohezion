"""Item 1178: get_windowed_fleet_latency_range_ms_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool latency range (max - min) within the fleet store window.
Returns float. 0.0 for unknown/empty tool.
Composition: range_by_tool == max_by_tool - min_by_tool.

PRIMARY DISC.:
  tool_a=[10,200,50] → range_a=200-10=190ms
  tool_b=[1,400]     → range_b=400-1=399ms
  fleet_range=400-1=399ms (pools all tools)
  range_a=190ms kills range_b=399ms; kills fleet_range=399ms; kills always-0.
  Composition: range_by_tool == max_by_tool - min_by_tool.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_range_ms_by_tool,
    get_windowed_fleet_latency_max_ms_by_tool,
    get_windowed_fleet_latency_min_ms_by_tool,
    get_windowed_fleet_latency_range_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_range_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: range_a=190ms kills range_b=399ms; kills fleet_range=399ms; kills always-0."""
    _reset()
    store = _make_store(
        {
            "frangbt_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 200.0, True),
                (_NOW - 700, 50.0, True),
            ],
            "frangbt_b": [
                (_NOW - 600, 1.0, True),
                (_NOW - 500, 400.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_range_ms_by_tool(
        _WIN, "frangbt_a", store=store, now_ms=_NOW
    )
    assert isinstance(result, float), f"expected float, got {type(result)}"
    expected = 200.0 - 10.0  # 190ms
    assert abs(result - expected) < 1e-9, (
        f"range_a=190ms; kills range_b=399ms/fleet_range=399ms/always-0; got {result}"
    )


def test_fleet_range_by_tool_composition_max_minus_min() -> None:
    """Composition: range_by_tool == max_by_tool - min_by_tool."""
    _reset()
    store = _make_store(
        {
            "frangbt_comp": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 200.0, True),
                (_NOW - 700, 50.0, True),
                (_NOW - 600, 150.0, True),
            ],
        }
    )
    rng = get_windowed_fleet_latency_range_ms_by_tool(
        _WIN, "frangbt_comp", store=store, now_ms=_NOW
    )
    mx = get_windowed_fleet_latency_max_ms_by_tool(_WIN, "frangbt_comp", store=store, now_ms=_NOW)
    mn = get_windowed_fleet_latency_min_ms_by_tool(_WIN, "frangbt_comp", store=store, now_ms=_NOW)
    assert abs(rng - (mx - mn)) < 1e-9, f"range({rng}) != max({mx}) - min({mn}) = {mx - mn}"


def test_fleet_range_by_tool_differs_from_fleet_range() -> None:
    """Per-tool range differs from fleet range (pooled)."""
    _reset()
    store = _make_store(
        {
            "frangbt_diff_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 200.0, True),
                (_NOW - 700, 50.0, True),
            ],
            "frangbt_diff_b": [
                (_NOW - 600, 1.0, True),
                (_NOW - 500, 400.0, True),
            ],
        }
    )
    tool_range = get_windowed_fleet_latency_range_ms_by_tool(
        _WIN, "frangbt_diff_a", store=store, now_ms=_NOW
    )
    fleet_range = get_windowed_fleet_latency_range_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(tool_range - fleet_range) > 1.0, (
        f"per-tool({tool_range}) should differ from fleet({fleet_range})"
    )


def test_fleet_range_by_tool_single_record_returns_zero() -> None:
    """Single record: max == min → range == 0.0."""
    _reset()
    store = _make_store(
        {
            "frangbt_one": [(_NOW - 500, 75.0, True)],
        }
    )
    result = get_windowed_fleet_latency_range_ms_by_tool(
        _WIN, "frangbt_one", store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9, f"single record: max==min → range=0; got {result}"


def test_fleet_range_by_tool_uniform_returns_zero() -> None:
    """All same latency → range == 0.0."""
    _reset()
    store = _make_store(
        {
            "frangbt_same": [(_NOW - float(d), 50.0, True) for d in [900, 800, 700]],
        }
    )
    result = get_windowed_fleet_latency_range_ms_by_tool(
        _WIN, "frangbt_same", store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9


def test_fleet_range_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store(
        {
            "frangbt_other": [(_NOW - 500, 100.0, True)],
        }
    )
    result = get_windowed_fleet_latency_range_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9
    assert isinstance(result, float)


def test_fleet_range_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_range_ms_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_range_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store(
        {
            "frangbt_old": [(_NOW - _WIN - float(d), 50.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_range_ms_by_tool(
        _WIN, "frangbt_old", store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "frangbt_rt": [
                (_NOW - 400, 20.0, True),
                (_NOW - 300, 80.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_range_ms_by_tool(
        _WIN, "frangbt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 60.0) < 1e-9  # 80 - 20 = 60ms
