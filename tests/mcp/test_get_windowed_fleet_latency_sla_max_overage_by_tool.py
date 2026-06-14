"""Item 1188: get_windowed_fleet_latency_sla_max_overage_by_tool(
              window_ms, tool_name, threshold_ms, *, store=None, now_ms=None) -> float
-- per-tool maximum single-call latency overage above threshold_ms.
Returns float. 0.0 for unknown/empty tool or all-compliant.
Formula: max(max(0, lat - threshold_ms) for each call in window).

PRIMARY DISC.:
  tool_a=[10,30,50] threshold=25ms → max overage = max(0,5,25) = 25ms
  tool_b=[100,200]  threshold=25ms → max overage = max(75,175) = 175ms
  max_overage_a=25ms kills max_overage_b=175ms; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_sla_max_overage_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_sla_max_overage_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: max_overage_a=25ms kills max_overage_b=175ms; kills always-0."""
    _reset()
    store = _make_store(
        {
            "fsmxovbt_a": [
                (_NOW - 900, 10.0, True),  # compliant: 0 overage
                (_NOW - 800, 30.0, True),  # violates: 5ms
                (_NOW - 700, 50.0, True),  # violates: 25ms  ← max
            ],
            "fsmxovbt_b": [
                (_NOW - 600, 100.0, True),  # violates: 75ms
                (_NOW - 500, 200.0, True),  # violates: 175ms ← max
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_max_overage_by_tool(
        _WIN, "fsmxovbt_a", 25.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 25.0) < 1e-9, (
        f"max_overage_a=25ms; kills max_overage_b=175ms/always-0; got {result}"
    )


def test_fleet_sla_max_overage_by_tool_all_compliant_returns_zero() -> None:
    """All latencies <= threshold → 0.0."""
    _reset()
    store = _make_store(
        {
            "fsmxovbt_ok": [(_NOW - float(d), 10.0, True) for d in [900, 800, 700]],
        }
    )
    result = get_windowed_fleet_latency_sla_max_overage_by_tool(
        _WIN, "fsmxovbt_ok", 50.0, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9


def test_fleet_sla_max_overage_by_tool_threshold_at_boundary() -> None:
    """Latency == threshold → 0 overage (not violated)."""
    _reset()
    store = _make_store(
        {
            "fsmxovbt_bnd": [
                (_NOW - 900, 50.0, True),  # == threshold, 0 overage
                (_NOW - 800, 51.0, True),  # > threshold, 1ms overage
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_max_overage_by_tool(
        _WIN, "fsmxovbt_bnd", 50.0, store=store, now_ms=_NOW
    )
    assert abs(result - 1.0) < 1e-9, f"max overage = 1ms; got {result}"


def test_fleet_sla_max_overage_by_tool_single_violation() -> None:
    """Single violating call → max_overage = that call's overage."""
    _reset()
    store = _make_store(
        {
            "fsmxovbt_one": [
                (_NOW - 900, 10.0, True),  # compliant
                (_NOW - 800, 80.0, True),  # violates: 80-25=55ms
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_max_overage_by_tool(
        _WIN, "fsmxovbt_one", 25.0, store=store, now_ms=_NOW
    )
    assert abs(result - 55.0) < 1e-9


def test_fleet_sla_max_overage_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store(
        {
            "fsmxovbt_other": [(_NOW - 500, 100.0, True)],
        }
    )
    result = get_windowed_fleet_latency_sla_max_overage_by_tool(
        _WIN, "nonexistent", 25.0, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9
    assert isinstance(result, float)


def test_fleet_sla_max_overage_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_sla_max_overage_by_tool(
        _WIN, "any_tool", 25.0, store={}, now_ms=_NOW
    )
    assert abs(result) < 1e-9


def test_fleet_sla_max_overage_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store(
        {
            "fsmxovbt_old": [(_NOW - _WIN - float(d), 500.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_sla_max_overage_by_tool(
        _WIN, "fsmxovbt_old", 10.0, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fsmxovbt_rt": [
                (_NOW - 400, 50.0, True),  # overage = 25ms
                (_NOW - 300, 100.0, True),  # overage = 75ms ← max
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_max_overage_by_tool(
        _WIN, "fsmxovbt_rt", 25.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 75.0) < 1e-9  # max overage = 100-25=75ms
