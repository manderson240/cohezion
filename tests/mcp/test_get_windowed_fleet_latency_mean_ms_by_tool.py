"""Item 1165: get_windowed_fleet_latency_mean_ms_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- per-tool mean latency within the fleet store window.
Returns float. 0.0 for unknown/empty tool.

PRIMARY DISC.:
  tool_a=[10,90] → mean=50ms
  tool_b=[200,300] → mean=250ms
  fleet_mean=(10+90+200+300)/4=150ms
  mean_a=50ms kills fleet_mean=150ms, mean_b=250ms, always-0.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_mean_ms_by_tool,
    get_windowed_fleet_latency_mean_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_mean_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: mean_a=50ms kills fleet_mean=150ms, mean_b=250ms, always-0."""
    _reset()
    store = _make_store({
        "fmbt_tool_a": [
            (_NOW - 900, 10.0, True),
            (_NOW - 800, 90.0, True),
        ],
        "fmbt_tool_b": [
            (_NOW - 700, 200.0, True),
            (_NOW - 600, 300.0, True),
        ],
    })
    result = get_windowed_fleet_latency_mean_ms_by_tool(_WIN, "fmbt_tool_a", store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 50.0) < 1e-9, (
        f"mean_a=(10+90)/2=50ms; kills fleet_mean=150ms/mean_b=250ms/always-0; got {result}"
    )


def test_fleet_mean_by_tool_differs_from_fleet_mean() -> None:
    """Per-tool mean must differ from fleet mean when tools have different latency profiles."""
    _reset()
    store = _make_store({
        "fmbt_diff_a": [
            (_NOW - 900, 10.0, True),
            (_NOW - 800, 90.0, True),
        ],
        "fmbt_diff_b": [
            (_NOW - 700, 200.0, True),
            (_NOW - 600, 300.0, True),
        ],
    })
    tool_mean = get_windowed_fleet_latency_mean_ms_by_tool(_WIN, "fmbt_diff_a", store=store, now_ms=_NOW)
    fleet_mean = get_windowed_fleet_latency_mean_ms(_WIN, store=store, now_ms=_NOW)
    # tool_a = 50ms; fleet = 150ms — must differ
    assert abs(tool_mean - fleet_mean) > 50.0, (
        f"per-tool({tool_mean}) should differ from fleet({fleet_mean}) by >50ms"
    )


def test_fleet_mean_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    store = _make_store({
        "fmbt_other": [(_NOW - 500, 100.0, True)],
    })
    result = get_windowed_fleet_latency_mean_ms_by_tool(_WIN, "nonexistent", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"unknown tool -> 0.0; got {result}"
    assert isinstance(result, float)


def test_fleet_mean_by_tool_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_mean_ms_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_mean_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "fmbt_old": [(_NOW - _WIN - float(d), 50.0, True) for d in [300, 200, 100]],
    })
    result = get_windowed_fleet_latency_mean_ms_by_tool(_WIN, "fmbt_old", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_mean_by_tool_single_call() -> None:
    """Single call -> mean == that call's latency."""
    _reset()
    store = _make_store({
        "fmbt_one": [(_NOW - 300, 77.5, True)],
    })
    result = get_windowed_fleet_latency_mean_ms_by_tool(_WIN, "fmbt_one", store=store, now_ms=_NOW)
    assert abs(result - 77.5) < 1e-9


def test_fleet_mean_by_tool_includes_all_calls_regardless_of_success() -> None:
    """Mean is computed over ALL calls regardless of success/failure flag."""
    _reset()
    store = _make_store({
        "fmbt_mixed": [
            (_NOW - 900, 10.0, True),
            (_NOW - 800, 30.0, False),
            (_NOW - 700, 50.0, True),
            (_NOW - 600, 70.0, False),
        ],
    })
    result = get_windowed_fleet_latency_mean_ms_by_tool(_WIN, "fmbt_mixed", store=store, now_ms=_NOW)
    expected = (10.0 + 30.0 + 50.0 + 70.0) / 4
    assert abs(result - expected) < 1e-9, f"mean of all calls; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fmbt_rt": [
            (_NOW - 400, 20.0, True),
            (_NOW - 300, 40.0, True),
        ],
    })
    result = get_windowed_fleet_latency_mean_ms_by_tool(_WIN, "fmbt_rt", store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 30.0) < 1e-9
