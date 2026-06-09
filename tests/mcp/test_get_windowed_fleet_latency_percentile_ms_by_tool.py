"""Item 1166: get_windowed_fleet_latency_percentile_ms_by_tool(window_ms, tool_name,
              percentile, *, store=None, now_ms=None) -> float
-- per-tool nearest-rank percentile latency within the fleet store window.
Returns float. 0.0 for unknown/empty tool.

PRIMARY DISC.:
  tool_a=[10,20,30,40,50,60,70,80,90,100] n=10
  P95 = ceil(0.95*10)-1 = ceil(9.5)-1 = 9 -> latencies[9] = 100ms
  tool_b=[5,5,5] n=3; P95 = ceil(0.95*3)-1 = ceil(2.85)-1 = 2 -> latencies[2] = 5ms
  Fleet pools both: sorted 13 values, P95 = ceil(0.95*13)-1 = ceil(12.35)-1 = 12 -> 100ms
    (but the test also checks P50 which gives a distinct fleet vs per-tool result)
  tool_a P95=100ms kills tool_b P95=5ms; kills always-0.
  Composition: percentile_by_tool(tool_a, 50.0) == p50_ms value for tool_a.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_percentile_ms_by_tool,
    get_windowed_fleet_latency_percentile_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_percentile_by_tool_p95_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a P95=100ms kills tool_b P95=5ms and always-0."""
    _reset()
    latencies_a = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    store = _make_store({
        "fpbt_tool_a": [
            (_NOW - float(1000 - i * 90), lat, True)
            for i, lat in enumerate(latencies_a)
        ],
        "fpbt_tool_b": [
            (_NOW - float(600 - j * 100), 5.0, True)
            for j in range(3)
        ],
    })
    result = get_windowed_fleet_latency_percentile_ms_by_tool(
        _WIN, "fpbt_tool_a", 95.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float), f"expected float, got {type(result)}"
    # tool_a n=10: ceil(0.95*10)-1 = ceil(9.5)-1 = 9 → latencies[9]=100ms
    assert abs(result - 100.0) < 1e-9, (
        f"tool_a P95=100ms; kills tool_b=5ms/always-0; got {result}"
    )


def test_fleet_percentile_by_tool_p50_differs_from_fleet_p50() -> None:
    """P50 per-tool vs fleet differ when tools have distinct latency distributions."""
    _reset()
    latencies_a = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    store = _make_store({
        "fpbt_diff_a": [
            (_NOW - float(1000 - i * 90), lat, True)
            for i, lat in enumerate(latencies_a)
        ],
        "fpbt_diff_b": [
            (_NOW - float(200 - j * 50), 5.0, True)
            for j in range(3)
        ],
    })
    tool_p50 = get_windowed_fleet_latency_percentile_ms_by_tool(
        _WIN, "fpbt_diff_a", 50.0, store=store, now_ms=_NOW
    )
    fleet_p50 = get_windowed_fleet_latency_percentile_ms(_WIN, 50.0, store=store, now_ms=_NOW)
    # tool_a n=10: P50=ceil(5)-1=4 → latencies[4]=50ms
    # fleet n=13: P50=ceil(6.5)-1=6 → sorted([5,5,5,10,20,30,40,50,60,70,80,90,100])[6]=40ms
    assert abs(tool_p50 - fleet_p50) > 1.0, (
        f"per-tool({tool_p50}) should differ from fleet({fleet_p50})"
    )


def test_fleet_percentile_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    store = _make_store({
        "fpbt_other": [(_NOW - 500, 100.0, True)],
    })
    result = get_windowed_fleet_latency_percentile_ms_by_tool(
        _WIN, "nonexistent", 50.0, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9
    assert isinstance(result, float)


def test_fleet_percentile_by_tool_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_percentile_ms_by_tool(
        _WIN, "any_tool", 75.0, store={}, now_ms=_NOW
    )
    assert abs(result) < 1e-9


def test_fleet_percentile_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window for that tool -> 0.0."""
    _reset()
    store = _make_store({
        "fpbt_old": [(_NOW - _WIN - float(d), 50.0, True) for d in [300, 200, 100]],
    })
    result = get_windowed_fleet_latency_percentile_ms_by_tool(
        _WIN, "fpbt_old", 50.0, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9


def test_fleet_percentile_by_tool_single_call_any_percentile() -> None:
    """Single call -> any percentile == that call's latency."""
    _reset()
    store = _make_store({
        "fpbt_one": [(_NOW - 300, 42.0, True)],
    })
    for pct in [25.0, 50.0, 75.0, 95.0, 99.0]:
        result = get_windowed_fleet_latency_percentile_ms_by_tool(
            _WIN, "fpbt_one", pct, store=store, now_ms=_NOW
        )
        assert abs(result - 42.0) < 1e-9, f"P{pct}: single call → 42ms; got {result}"


def test_fleet_percentile_by_tool_p25_nearest_rank() -> None:
    """P25 uses nearest-rank: ceil(0.25*n)-1."""
    _reset()
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    store = _make_store({
        "fpbt_p25": [
            (_NOW - float(1000 - i * 90), lat, True)
            for i, lat in enumerate(latencies)
        ],
    })
    result = get_windowed_fleet_latency_percentile_ms_by_tool(
        _WIN, "fpbt_p25", 25.0, store=store, now_ms=_NOW
    )
    # n=10: ceil(0.25*10)-1 = ceil(2.5)-1 = 3-1 = 2 → latencies[2]=30ms
    assert abs(result - 30.0) < 1e-9, f"P25 nearest-rank=30ms; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fpbt_rt": [(_NOW - float(d * 100), float(d * 10), True) for d in range(1, 6)],
    })
    result = get_windowed_fleet_latency_percentile_ms_by_tool(
        _WIN, "fpbt_rt", 50.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
