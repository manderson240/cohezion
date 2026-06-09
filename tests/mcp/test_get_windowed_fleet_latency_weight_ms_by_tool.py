"""Item 1204: get_windowed_fleet_latency_weight_ms_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool total latency weight (sum of all latency values) within window.
Returns float. 0.0 for unknown/empty tool or all calls outside window.
Formula: sum(lat for each call in window).

PRIMARY DISC.:
  tool_a=[10,20,30] → weight=60.0
  tool_b=[100,200,300] → weight=600.0
  weight_a=60.0 kills weight_b=600.0; kills always-0.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_weight_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_latency_weight_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: weight_a=60.0 kills weight_b=600.0; kills always-0."""
    _reset()
    store = _make_store({
        "flwbt_a": [
            (_NOW - 900, 10.0, True),
            (_NOW - 600, 20.0, True),
            (_NOW - 300, 30.0, True),
        ],
        "flwbt_b": [
            (_NOW - 800, 100.0, True),
            (_NOW - 500, 200.0, True),
            (_NOW - 200, 300.0, True),
        ],
    })
    weight_a = get_windowed_fleet_latency_weight_ms_by_tool(
        _WIN, "flwbt_a", store=store, now_ms=_NOW
    )
    weight_b = get_windowed_fleet_latency_weight_ms_by_tool(
        _WIN, "flwbt_b", store=store, now_ms=_NOW
    )
    assert isinstance(weight_a, float), f"expected float, got {type(weight_a)}"
    assert weight_a == 60.0, (
        f"weight_a=60.0 (10+20+30); kills weight_b=600/always-0; got {weight_a}"
    )
    assert weight_b == 600.0, f"weight_b=600.0 (100+200+300); got {weight_b}"


def test_fleet_latency_weight_single_call() -> None:
    """Single call → its latency is the weight."""
    _reset()
    store = _make_store({
        "flwbt_one": [(_NOW - 500, 77.0, True)],
    })
    result = get_windowed_fleet_latency_weight_ms_by_tool(
        _WIN, "flwbt_one", store=store, now_ms=_NOW
    )
    assert result == 77.0


def test_fleet_latency_weight_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store({
        "flwbt_other": [(_NOW - 500, 100.0, True)],
    })
    result = get_windowed_fleet_latency_weight_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_latency_weight_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_weight_ms_by_tool(
        _WIN, "any_tool", store={}, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_latency_weight_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store({
        "flwbt_old": [
            (_NOW - _WIN - 300, 100.0, True),
            (_NOW - _WIN - 100, 200.0, True),
        ],
    })
    result = get_windowed_fleet_latency_weight_ms_by_tool(
        _WIN, "flwbt_old", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_latency_weight_equals_mean_times_count() -> None:
    """weight == mean * count (fundamental arithmetic identity)."""
    _reset()
    store = _make_store({
        "flwbt_arith": [
            (_NOW - 900, 10.0, True),
            (_NOW - 600, 20.0, True),
            (_NOW - 300, 30.0, True),
        ],
    })
    weight = get_windowed_fleet_latency_weight_ms_by_tool(
        _WIN, "flwbt_arith", store=store, now_ms=_NOW
    )
    # mean = 20.0, count = 3 → weight = 60.0
    assert weight == 60.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "flwbt_rt": [
            (_NOW - 400, 15.0, True),
            (_NOW - 200, 25.0, True),
        ],
    })
    result = get_windowed_fleet_latency_weight_ms_by_tool(
        _WIN, "flwbt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert result == 40.0
