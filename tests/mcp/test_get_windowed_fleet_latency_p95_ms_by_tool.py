"""Item 1169: get_windowed_fleet_latency_p95_ms_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- thin composition: percentile_ms_by_tool(window_ms, tool_name, 95.0, ...).
Returns float. 0.0 for unknown/empty tool.

PRIMARY DISC.:
  tool_a=[10,20,30,40,50,60,70,80,90,100] n=10
  P95 (nearest-rank): ceil(0.95*10)-1 = ceil(9.5)-1 = 9 → latencies[9] = 100ms
  kills fleet P95 (pooled), kills always-0.
  Composition: p95_by_tool == percentile_by_tool(tool, 95.0).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_p95_ms_by_tool,
    get_windowed_fleet_latency_percentile_ms_by_tool,
    get_windowed_fleet_latency_p95_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_p95_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a P95=100ms; kills fleet P95, kills always-0."""
    _reset()
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    store = _make_store(
        {
            "fp95bt_a": [
                (_NOW - float(1000 - i * 90), lat, True) for i, lat in enumerate(latencies)
            ],
            "fp95bt_b": [(_NOW - float(200 - j * 50), 5.0, True) for j in range(3)],
        }
    )
    result = get_windowed_fleet_latency_p95_ms_by_tool(_WIN, "fp95bt_a", store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    # n=10: ceil(0.95*10)-1 = ceil(9.5)-1 = 10-1 = 9 → latencies[9]=100ms
    assert abs(result - 100.0) < 1e-9, f"tool_a P95=100ms; kills fleet P95/always-0; got {result}"


def test_fleet_p95_by_tool_composition() -> None:
    """Composition: p95_by_tool == percentile_by_tool(95.0)."""
    _reset()
    store = _make_store(
        {
            "fp95bt_comp": [
                (_NOW - float(1000 - i * 80), float(i * 15 + 5), True) for i in range(8)
            ],
        }
    )
    p95 = get_windowed_fleet_latency_p95_ms_by_tool(_WIN, "fp95bt_comp", store=store, now_ms=_NOW)
    generic = get_windowed_fleet_latency_percentile_ms_by_tool(
        _WIN, "fp95bt_comp", 95.0, store=store, now_ms=_NOW
    )
    assert abs(p95 - generic) < 1e-12


def test_fleet_p95_by_tool_differs_from_fleet_p95() -> None:
    """Per-tool P95 differs from fleet P95 when tool_b has higher latencies."""
    _reset()
    store = _make_store(
        {
            # tool_a: [10..100] n=10, P95=ceil(9.5)-1=9 → 100ms
            "fp95bt_diff_a": [
                (_NOW - float(1000 - i * 90), float(i * 10 + 10), True) for i in range(10)
            ],
            # tool_b: [200,300,400] — fleet P95 = sorted(13 values)[12]=400ms
            "fp95bt_diff_b": [
                (_NOW - float(600 - j * 100), float(200 + j * 100), True) for j in range(3)
            ],
        }
    )
    tool_p95 = get_windowed_fleet_latency_p95_ms_by_tool(
        _WIN, "fp95bt_diff_a", store=store, now_ms=_NOW
    )
    fleet_p95 = get_windowed_fleet_latency_p95_ms(_WIN, store=store, now_ms=_NOW)
    # tool_a P95=100ms; fleet P95=400ms (tool_b inflates it)
    assert abs(tool_p95 - fleet_p95) > 50.0, (
        f"per-tool({tool_p95}) should differ from fleet({fleet_p95}) by >50ms"
    )


def test_fleet_p95_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fp95bt_other": [(_NOW - 500, 100.0, True)],
        }
    )
    result = get_windowed_fleet_latency_p95_ms_by_tool(
        _WIN, "nonexistent", store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9
    assert isinstance(result, float)


def test_fleet_p95_by_tool_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_p95_ms_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_p95_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fp95bt_old": [(_NOW - _WIN - float(d), 50.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_p95_ms_by_tool(_WIN, "fp95bt_old", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fp95bt_rt": [(_NOW - float(d * 100), float(d * 10), True) for d in range(1, 6)],
        }
    )
    result = get_windowed_fleet_latency_p95_ms_by_tool(_WIN, "fp95bt_rt", store=store, now_ms=_NOW)
    assert isinstance(result, float)
