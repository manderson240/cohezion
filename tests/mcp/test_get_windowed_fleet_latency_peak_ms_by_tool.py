"""Item 1192: get_windowed_fleet_latency_peak_ms_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool peak (maximum) latency within the window (alias for max).
Returns float. 0.0 for unknown/empty tool or all calls outside window.

PRIMARY DISC.:
  tool_a=[10,50,200] → peak=200.0
  tool_b=[5,15,25]   → peak=25.0
  peak_a=200.0 kills peak_b=25.0; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_peak_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_peak_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: peak_a=200.0 kills peak_b=25.0; kills always-0."""
    _reset()
    store = _make_store(
        {
            "fpbt_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 600, 50.0, True),
                (_NOW - 300, 200.0, True),
            ],
            "fpbt_b": [
                (_NOW - 800, 5.0, True),
                (_NOW - 500, 15.0, True),
                (_NOW - 200, 25.0, True),
            ],
        }
    )
    peak_a = get_windowed_fleet_latency_peak_ms_by_tool(_WIN, "fpbt_a", store=store, now_ms=_NOW)
    peak_b = get_windowed_fleet_latency_peak_ms_by_tool(_WIN, "fpbt_b", store=store, now_ms=_NOW)
    assert isinstance(peak_a, float), f"expected float, got {type(peak_a)}"
    assert peak_a == 200.0, f"peak_a=200.0 kills peak_b=25.0/always-0; got {peak_a}"
    assert peak_b == 25.0, f"peak_b should be 25.0; got {peak_b}"


def test_fleet_peak_by_tool_single_call() -> None:
    """Single call → its latency is the peak."""
    _reset()
    store = _make_store(
        {
            "fpbt_single": [(_NOW - 500, 77.0, True)],
        }
    )
    result = get_windowed_fleet_latency_peak_ms_by_tool(
        _WIN, "fpbt_single", store=store, now_ms=_NOW
    )
    assert result == 77.0


def test_fleet_peak_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store(
        {
            "fpbt_other": [(_NOW - 500, 100.0, True)],
        }
    )
    result = get_windowed_fleet_latency_peak_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_peak_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_peak_ms_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert result == 0.0


def test_fleet_peak_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store(
        {
            "fpbt_old": [
                (_NOW - _WIN - 300, 500.0, True),
                (_NOW - _WIN - 100, 999.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_peak_ms_by_tool(_WIN, "fpbt_old", store=store, now_ms=_NOW)
    assert result == 0.0


def test_fleet_peak_by_tool_only_window_calls_counted() -> None:
    """Calls outside window are excluded; only windowed ones contribute."""
    _reset()
    store = _make_store(
        {
            "fpbt_mix": [
                (_NOW - _WIN - 1, 9999.0, True),  # outside window → excluded
                (_NOW - 500, 42.0, True),  # inside window
                (_NOW - 200, 88.0, True),  # inside window
            ],
        }
    )
    result = get_windowed_fleet_latency_peak_ms_by_tool(_WIN, "fpbt_mix", store=store, now_ms=_NOW)
    assert result == 88.0, f"9999ms outside window excluded; peak=88; got {result}"


def test_fleet_peak_by_tool_all_same_latency() -> None:
    """All same latency → peak == that value."""
    _reset()
    store = _make_store(
        {
            "fpbt_flat": [(_NOW - float(d), 30.0, True) for d in [900, 600, 300]],
        }
    )
    result = get_windowed_fleet_latency_peak_ms_by_tool(_WIN, "fpbt_flat", store=store, now_ms=_NOW)
    assert result == 30.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fpbt_rt": [
                (_NOW - 400, 11.0, True),
                (_NOW - 200, 55.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_peak_ms_by_tool(_WIN, "fpbt_rt", store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert result == 55.0
