"""Item 1205: get_windowed_fleet_latency_mean_per_success_ms_by_tool(
              window_ms, tool_name, *, store=None, now_ms=None) -> float
-- per-tool mean latency of SUCCESSFUL calls only (ok=True) within window.
Returns float. 0.0 for unknown/empty tool or no successful calls.
Formula: sum(lat for ok=True) / count(ok=True).

PRIMARY DISC.:
  tool_a: [(10ms,ok=T),(20ms,ok=T),(100ms,ok=F)] → mean_success=15.0
  tool_b: [(50ms,ok=T),(50ms,ok=T)] → mean_success=50.0
  mean_success_a=15.0 kills mean_success_b=50.0; kills always-0.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_mean_per_success_ms_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_mean_per_success_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: mean_success_a=15.0 kills mean_success_b=50.0; kills always-0."""
    _reset()
    store = _make_store({
        "fmpsbt_a": [
            (_NOW - 900, 10.0, True),    # success
            (_NOW - 600, 20.0, True),    # success
            (_NOW - 300, 100.0, False),  # failure — excluded
        ],
        "fmpsbt_b": [
            (_NOW - 700, 50.0, True),    # success
            (_NOW - 400, 50.0, True),    # success
        ],
    })
    mean_a = get_windowed_fleet_latency_mean_per_success_ms_by_tool(
        _WIN, "fmpsbt_a", store=store, now_ms=_NOW
    )
    mean_b = get_windowed_fleet_latency_mean_per_success_ms_by_tool(
        _WIN, "fmpsbt_b", store=store, now_ms=_NOW
    )
    assert isinstance(mean_a, float), f"expected float, got {type(mean_a)}"
    assert mean_a == 15.0, (
        f"mean_success_a=15.0 (10+20)/2; kills mean_b=50/always-0; got {mean_a}"
    )
    assert mean_b == 50.0, f"mean_success_b=50.0; got {mean_b}"


def test_fleet_mean_per_success_no_successes_returns_zero() -> None:
    """All calls failed → no successes → 0.0."""
    _reset()
    store = _make_store({
        "fmpsbt_fail": [
            (_NOW - 900, 100.0, False),
            (_NOW - 600, 200.0, False),
        ],
    })
    result = get_windowed_fleet_latency_mean_per_success_ms_by_tool(
        _WIN, "fmpsbt_fail", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_mean_per_success_excludes_failures() -> None:
    """Failures do not affect the mean: only ok=True calls counted."""
    _reset()
    store = _make_store({
        "fmpsbt_excl": [
            (_NOW - 900, 10.0, True),    # success
            (_NOW - 800, 9999.0, False), # failure — should not shift mean
            (_NOW - 700, 20.0, True),    # success
        ],
    })
    result = get_windowed_fleet_latency_mean_per_success_ms_by_tool(
        _WIN, "fmpsbt_excl", store=store, now_ms=_NOW
    )
    assert result == 15.0, f"9999ms failure excluded; mean=(10+20)/2=15; got {result}"


def test_fleet_mean_per_success_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store({
        "fmpsbt_other": [(_NOW - 500, 100.0, True)],
    })
    result = get_windowed_fleet_latency_mean_per_success_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_mean_per_success_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_mean_per_success_ms_by_tool(
        _WIN, "any_tool", store={}, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_mean_per_success_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store({
        "fmpsbt_old": [
            (_NOW - _WIN - 200, 10.0, True),
            (_NOW - _WIN - 100, 20.0, True),
        ],
    })
    result = get_windowed_fleet_latency_mean_per_success_ms_by_tool(
        _WIN, "fmpsbt_old", store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fmpsbt_rt": [
            (_NOW - 400, 30.0, True),
            (_NOW - 200, 50.0, False),  # failure excluded
        ],
    })
    result = get_windowed_fleet_latency_mean_per_success_ms_by_tool(
        _WIN, "fmpsbt_rt", store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert result == 30.0
