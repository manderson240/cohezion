"""Item 1187: get_windowed_fleet_latency_sla_mean_overage_by_tool(
              window_ms, tool_name, threshold_ms, *, store=None, now_ms=None) -> float
-- per-tool mean latency overage for SLA-violating calls only.
Returns float. 0.0 for unknown/empty tool or all-compliant.
Formula: budget_consumed / violation_count.

PRIMARY DISC.:
  tool_a=[10,30,50] threshold=25ms → violations=[30,50], overages=[5,25], mean=15ms
  tool_b=[100,200]  threshold=25ms → violations=[100,200], overages=[75,175], mean=125ms
  mean_overage_a=15ms kills mean_overage_b=125ms; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_sla_mean_overage_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_sla_mean_overage_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: mean_overage_a=15ms kills mean_overage_b=125ms; kills always-0."""
    _reset()
    store = _make_store(
        {
            "fsmovbt_a": [
                (_NOW - 900, 10.0, True),  # compliant: 0 overage
                (_NOW - 800, 30.0, True),  # violates: 5ms overage
                (_NOW - 700, 50.0, True),  # violates: 25ms overage
            ],
            "fsmovbt_b": [
                (_NOW - 600, 100.0, True),  # violates: 75ms overage
                (_NOW - 500, 200.0, True),  # violates: 175ms overage
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_mean_overage_by_tool(
        _WIN, "fsmovbt_a", 25.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float), f"expected float, got {type(result)}"
    expected = (5.0 + 25.0) / 2.0  # 15.0ms
    assert abs(result - expected) < 1e-9, (
        f"mean_overage_a=15ms; kills mean_overage_b=125ms/always-0; got {result}"
    )


def test_fleet_sla_mean_overage_by_tool_all_compliant_returns_zero() -> None:
    """All latencies <= threshold → 0.0."""
    _reset()
    store = _make_store(
        {
            "fsmovbt_ok": [(_NOW - float(d), 10.0, True) for d in [900, 800, 700]],
        }
    )
    result = get_windowed_fleet_latency_sla_mean_overage_by_tool(
        _WIN, "fsmovbt_ok", 50.0, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9, f"all compliant → 0.0; got {result}"


def test_fleet_sla_mean_overage_by_tool_single_violation() -> None:
    """Single violation: mean_overage == that violation's overage."""
    _reset()
    store = _make_store(
        {
            "fsmovbt_one": [
                (_NOW - 900, 10.0, True),  # compliant
                (_NOW - 800, 75.0, True),  # violates: 75 - 25 = 50ms overage
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_mean_overage_by_tool(
        _WIN, "fsmovbt_one", 25.0, store=store, now_ms=_NOW
    )
    assert abs(result - 50.0) < 1e-9, f"single violation: mean=overage=50ms; got {result}"


def test_fleet_sla_mean_overage_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store(
        {
            "fsmovbt_other": [(_NOW - 500, 100.0, True)],
        }
    )
    result = get_windowed_fleet_latency_sla_mean_overage_by_tool(
        _WIN, "nonexistent", 25.0, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9
    assert isinstance(result, float)


def test_fleet_sla_mean_overage_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_sla_mean_overage_by_tool(
        _WIN, "any_tool", 25.0, store={}, now_ms=_NOW
    )
    assert abs(result) < 1e-9


def test_fleet_sla_mean_overage_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store(
        {
            "fsmovbt_old": [(_NOW - _WIN - float(d), 500.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_sla_mean_overage_by_tool(
        _WIN, "fsmovbt_old", 10.0, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fsmovbt_rt": [
                (_NOW - 400, 50.0, True),  # overage = 50 - 25 = 25ms
                (_NOW - 300, 100.0, True),  # overage = 100 - 25 = 75ms
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_mean_overage_by_tool(
        _WIN, "fsmovbt_rt", 25.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 50.0) < 1e-9  # (25 + 75) / 2 = 50ms
