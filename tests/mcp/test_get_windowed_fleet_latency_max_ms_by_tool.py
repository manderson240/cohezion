"""Item 1172: get_windowed_fleet_latency_max_ms_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool maximum latency within the fleet store window.
Returns float. 0.0 for unknown/empty tool.

PRIMARY DISC.:
  tool_a=[10,200,50] → max_a=200ms
  tool_b=[300,400]   → max_b=400ms
  fleet_max=400ms
  max_a=200ms kills max_b=400ms; kills fleet_max=400ms; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_max_ms_by_tool,
    get_windowed_fleet_latency_max_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_max_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: max_a=200ms kills max_b=400ms, fleet_max=400ms, always-0."""
    _reset()
    store = _make_store(
        {
            "fmaxbt_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 200.0, True),
                (_NOW - 700, 50.0, True),
            ],
            "fmaxbt_b": [
                (_NOW - 600, 300.0, True),
                (_NOW - 500, 400.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_max_ms_by_tool(_WIN, "fmaxbt_a", store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 200.0) < 1e-9, (
        f"max_a=200ms; kills max_b=400ms/fleet_max=400ms/always-0; got {result}"
    )


def test_fleet_max_by_tool_differs_from_fleet_max() -> None:
    """Per-tool max < fleet max when tool_b has higher latencies."""
    _reset()
    store = _make_store(
        {
            "fmaxbt_diff_a": [(_NOW - 900, 50.0, True), (_NOW - 800, 100.0, True)],
            "fmaxbt_diff_b": [(_NOW - 700, 500.0, True), (_NOW - 600, 999.0, True)],
        }
    )
    tool_max = get_windowed_fleet_latency_max_ms_by_tool(
        _WIN, "fmaxbt_diff_a", store=store, now_ms=_NOW
    )
    fleet_max = get_windowed_fleet_latency_max_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(tool_max - fleet_max) > 100.0, (
        f"per-tool({tool_max}) should differ from fleet({fleet_max})"
    )


def test_fleet_max_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fmaxbt_other": [(_NOW - 500, 999.0, True)],
        }
    )
    result = get_windowed_fleet_latency_max_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9
    assert isinstance(result, float)


def test_fleet_max_by_tool_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_max_ms_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_max_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fmaxbt_old": [(_NOW - _WIN - float(d), 999.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_max_ms_by_tool(_WIN, "fmaxbt_old", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_max_by_tool_single_call() -> None:
    """Single call -> max == that call's latency."""
    _reset()
    store = _make_store(
        {
            "fmaxbt_one": [(_NOW - 300, 137.5, True)],
        }
    )
    result = get_windowed_fleet_latency_max_ms_by_tool(_WIN, "fmaxbt_one", store=store, now_ms=_NOW)
    assert abs(result - 137.5) < 1e-9


def test_fleet_max_by_tool_includes_error_calls() -> None:
    """Max is computed over all calls regardless of success/failure."""
    _reset()
    store = _make_store(
        {
            "fmaxbt_mixed": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 500.0, False),  # error call with high latency
                (_NOW - 700, 20.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_max_ms_by_tool(
        _WIN, "fmaxbt_mixed", store=store, now_ms=_NOW
    )
    assert abs(result - 500.0) < 1e-9, f"max includes error calls; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fmaxbt_rt": [(_NOW - float(d * 100), float(d * 10), True) for d in range(1, 6)],
        }
    )
    result = get_windowed_fleet_latency_max_ms_by_tool(_WIN, "fmaxbt_rt", store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 50.0) < 1e-9  # max of [10,20,30,40,50]
