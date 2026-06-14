"""Item 1173: get_windowed_fleet_latency_min_ms_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool minimum latency within the fleet store window.
Returns float. 0.0 for unknown/empty tool.

PRIMARY DISC.:
  tool_a=[10,200,50] → min_a=10ms
  tool_b=[1,400]     → min_b=1ms
  fleet_min=1ms
  min_a=10ms kills min_b=1ms; kills fleet_min=1ms; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_min_ms_by_tool,
    get_windowed_fleet_latency_min_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_min_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: min_a=10ms kills min_b=1ms, fleet_min=1ms, always-0."""
    _reset()
    store = _make_store(
        {
            "fminbt_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 200.0, True),
                (_NOW - 700, 50.0, True),
            ],
            "fminbt_b": [
                (_NOW - 600, 1.0, True),
                (_NOW - 500, 400.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_min_ms_by_tool(_WIN, "fminbt_a", store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 10.0) < 1e-9, (
        f"min_a=10ms; kills min_b=1ms/fleet_min=1ms/always-0; got {result}"
    )


def test_fleet_min_by_tool_differs_from_fleet_min() -> None:
    """Per-tool min > fleet min when tool_b has lower latency."""
    _reset()
    store = _make_store(
        {
            "fminbt_diff_a": [(_NOW - 900, 100.0, True), (_NOW - 800, 200.0, True)],
            "fminbt_diff_b": [(_NOW - 700, 1.0, True), (_NOW - 600, 2.0, True)],
        }
    )
    tool_min = get_windowed_fleet_latency_min_ms_by_tool(
        _WIN, "fminbt_diff_a", store=store, now_ms=_NOW
    )
    fleet_min = get_windowed_fleet_latency_min_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(tool_min - fleet_min) > 10.0, (
        f"per-tool({tool_min}) should differ from fleet({fleet_min})"
    )


def test_fleet_min_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fminbt_other": [(_NOW - 500, 1.0, True)],
        }
    )
    result = get_windowed_fleet_latency_min_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9
    assert isinstance(result, float)


def test_fleet_min_by_tool_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_min_ms_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_min_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fminbt_old": [(_NOW - _WIN - float(d), 1.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_min_ms_by_tool(_WIN, "fminbt_old", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_min_by_tool_single_call() -> None:
    """Single call -> min == that call's latency."""
    _reset()
    store = _make_store(
        {
            "fminbt_one": [(_NOW - 300, 33.3, True)],
        }
    )
    result = get_windowed_fleet_latency_min_ms_by_tool(_WIN, "fminbt_one", store=store, now_ms=_NOW)
    assert abs(result - 33.3) < 1e-9


def test_fleet_min_by_tool_includes_error_calls() -> None:
    """Min is computed over all calls regardless of success/failure."""
    _reset()
    store = _make_store(
        {
            "fminbt_mixed": [
                (_NOW - 900, 100.0, True),
                (_NOW - 800, 5.0, False),  # error call with low latency
                (_NOW - 700, 200.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_min_ms_by_tool(
        _WIN, "fminbt_mixed", store=store, now_ms=_NOW
    )
    assert abs(result - 5.0) < 1e-9, f"min includes error calls; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fminbt_rt": [(_NOW - float(d * 100), float(d * 10), True) for d in range(1, 6)],
        }
    )
    result = get_windowed_fleet_latency_min_ms_by_tool(_WIN, "fminbt_rt", store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 10.0) < 1e-9  # min of [10,20,30,40,50]
