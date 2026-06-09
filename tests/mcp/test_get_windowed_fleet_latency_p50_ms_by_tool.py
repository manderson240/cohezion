"""Item 1167: get_windowed_fleet_latency_p50_ms_by_tool(window_ms, tool_name,
              *, store=None, now_ms=None) -> float
-- thin composition: percentile_ms_by_tool(window_ms, tool_name, 50.0, ...).
Returns float. 0.0 for unknown/empty tool.

PRIMARY DISC.:
  tool_a=[10,20,30,40,50,60,70,80,90,100] n=10
  P50 (nearest-rank): ceil(0.5*10)-1 = 4 → latencies[4] = 50ms
  kills fleet P50 (pooled), kills always-0.
  Composition: p50_by_tool == percentile_by_tool(tool, 50.0).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_p50_ms_by_tool,
    get_windowed_fleet_latency_percentile_ms_by_tool,
    get_windowed_fleet_latency_p50_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_p50_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a P50=50ms; kills fleet P50, kills always-0."""
    _reset()
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    store = _make_store({
        "fp50bt_a": [
            (_NOW - float(1000 - i * 90), lat, True)
            for i, lat in enumerate(latencies)
        ],
        "fp50bt_b": [
            (_NOW - float(200 - j * 50), 5.0, True)
            for j in range(3)
        ],
    })
    result = get_windowed_fleet_latency_p50_ms_by_tool(_WIN, "fp50bt_a", store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    # n=10: ceil(0.5*10)-1 = 4 → latencies[4]=50ms
    assert abs(result - 50.0) < 1e-9, (
        f"tool_a P50=50ms; kills fleet P50/always-0; got {result}"
    )


def test_fleet_p50_by_tool_composition() -> None:
    """Composition: p50_by_tool == percentile_by_tool(50.0)."""
    _reset()
    store = _make_store({
        "fp50bt_comp": [
            (_NOW - float(1000 - i * 80), float(i * 15 + 5), True) for i in range(8)
        ],
    })
    p50 = get_windowed_fleet_latency_p50_ms_by_tool(_WIN, "fp50bt_comp", store=store, now_ms=_NOW)
    generic = get_windowed_fleet_latency_percentile_ms_by_tool(
        _WIN, "fp50bt_comp", 50.0, store=store, now_ms=_NOW
    )
    assert abs(p50 - generic) < 1e-12, f"p50_by_tool({p50}) != percentile_by_tool(50.0)({generic})"


def test_fleet_p50_by_tool_differs_from_fleet_p50() -> None:
    """Per-tool P50 differs from fleet P50 when tools have distinct latencies."""
    _reset()
    store = _make_store({
        "fp50bt_diff_a": [
            (_NOW - float(1000 - i * 90), float(i * 10 + 10), True) for i in range(10)
        ],
        "fp50bt_diff_b": [
            (_NOW - float(200 - j * 50), 5.0, True) for j in range(3)
        ],
    })
    tool_p50 = get_windowed_fleet_latency_p50_ms_by_tool(
        _WIN, "fp50bt_diff_a", store=store, now_ms=_NOW
    )
    fleet_p50 = get_windowed_fleet_latency_p50_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(tool_p50 - fleet_p50) > 1.0, (
        f"per-tool({tool_p50}) should differ from fleet({fleet_p50})"
    )


def test_fleet_p50_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    store = _make_store({
        "fp50bt_other": [(_NOW - 500, 100.0, True)],
    })
    result = get_windowed_fleet_latency_p50_ms_by_tool(_WIN, "nonexistent", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9
    assert isinstance(result, float)


def test_fleet_p50_by_tool_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_p50_ms_by_tool(_WIN, "any_tool", store={}, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_p50_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "fp50bt_old": [(_NOW - _WIN - float(d), 50.0, True) for d in [300, 200, 100]],
    })
    result = get_windowed_fleet_latency_p50_ms_by_tool(_WIN, "fp50bt_old", store=store, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fp50bt_rt": [(_NOW - float(d * 100), float(d * 10), True) for d in range(1, 6)],
    })
    result = get_windowed_fleet_latency_p50_ms_by_tool(_WIN, "fp50bt_rt", store=store, now_ms=_NOW)
    assert isinstance(result, float)
