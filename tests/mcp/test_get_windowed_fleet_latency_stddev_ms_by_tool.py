"""Item 1174: get_windowed_fleet_latency_stddev_ms_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool population standard deviation of latency in the window.
Returns float. 0.0 for unknown/empty tool or single call.
Uses population stddev: sqrt(sum((x-mean)^2)/n).

PRIMARY DISC.:
  tool_a=[10,90]   → mean=50, variance=((10-50)²+(90-50)²)/2=1600, stddev=40ms
  tool_b=[200,300] → mean=250, variance=((200-250)²+(300-250)²)/2=2500, stddev=50ms
  fleet_stddev pools [10,90,200,300]: mean=150, variance= ..., stddev!=40 and !=50
  stddev_a=40ms kills stddev_b=50ms; kills fleet_stddev; kills always-0.
"""

from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_stddev_ms_by_tool,
    get_windowed_fleet_latency_stddev_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_stddev_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: stddev_a=40ms kills stddev_b=50ms, fleet_stddev, always-0."""
    _reset()
    store = _make_store(
        {
            "fsdbt_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 90.0, True),
            ],
            "fsdbt_b": [
                (_NOW - 700, 200.0, True),
                (_NOW - 600, 300.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_stddev_ms_by_tool(_WIN, "fsdbt_a", store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    expected = math.sqrt(((10.0 - 50.0) ** 2 + (90.0 - 50.0) ** 2) / 2)  # = 40ms
    assert abs(result - expected) < 1e-9, (
        f"stddev_a={expected}ms; kills stddev_b=50ms/fleet/always-0; got {result}"
    )


def test_fleet_stddev_by_tool_differs_from_fleet_stddev() -> None:
    """Per-tool stddev differs from fleet stddev (heterogeneous pool)."""
    _reset()
    store = _make_store(
        {
            "fsdbt_diff_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 90.0, True),
            ],
            "fsdbt_diff_b": [
                (_NOW - 700, 200.0, True),
                (_NOW - 600, 300.0, True),
            ],
        }
    )
    tool_sd = get_windowed_fleet_latency_stddev_ms_by_tool(
        _WIN, "fsdbt_diff_a", store=store, now_ms=_NOW
    )
    fleet_sd = get_windowed_fleet_latency_stddev_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(tool_sd - fleet_sd) > 1.0, (
        f"per-tool({tool_sd}) should differ from fleet({fleet_sd})"
    )


def test_fleet_stddev_by_tool_identical_values_returns_zero() -> None:
    """All calls same latency -> stddev == 0.0."""
    _reset()
    store = _make_store(
        {
            "fsdbt_same": [(_NOW - float(d), 100.0, True) for d in [900, 800, 700]],
        }
    )
    result = get_windowed_fleet_latency_stddev_ms_by_tool(
        _WIN, "fsdbt_same", store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9, f"uniform latency -> 0.0; got {result}"


def test_fleet_stddev_by_tool_single_call_returns_zero() -> None:
    """Single call -> stddev == 0.0."""
    _reset()
    store = _make_store(
        {
            "fsdbt_one": [(_NOW - 300, 55.0, True)],
        }
    )
    result = get_windowed_fleet_latency_stddev_ms_by_tool(
        _WIN, "fsdbt_one", store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9


def test_fleet_stddev_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fsdbt_other": [(_NOW - 500, 100.0, True)],
        }
    )
    result = get_windowed_fleet_latency_stddev_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9
    assert isinstance(result, float)


def test_fleet_stddev_by_tool_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_stddev_ms_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_stddev_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fsdbt_old": [(_NOW - _WIN - float(d), 50.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_stddev_ms_by_tool(
        _WIN, "fsdbt_old", store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fsdbt_rt": [
                (_NOW - 400, 10.0, True),
                (_NOW - 300, 30.0, True),  # mean=20, variance=(100+100)/2=100, sd=10
            ],
        }
    )
    result = get_windowed_fleet_latency_stddev_ms_by_tool(
        _WIN, "fsdbt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 10.0) < 1e-9
