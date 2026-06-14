"""Item 1186: get_windowed_fleet_latency_sla_budget_consumed_by_tool(
              window_ms, tool_name, threshold_ms, *, store=None, now_ms=None) -> float
-- per-tool SLA budget consumed: sum of latency overage above threshold_ms.
Returns float. 0.0 for unknown/empty tool or all-compliant calls.
Formula: sum(max(0, lat - threshold_ms) for each call in window).

PRIMARY DISC.:
  tool_a=[10,30,50] threshold=25ms → overages: 0+5+25 = 30ms
  tool_b=[100,200]  threshold=25ms → overages: 75+175 = 250ms
  budget_a=30ms kills budget_b=250ms; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_sla_budget_consumed_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_sla_budget_consumed_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: budget_a=30ms kills budget_b=250ms; kills always-0."""
    _reset()
    store = _make_store(
        {
            "fbcbt_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 30.0, True),
                (_NOW - 700, 50.0, True),
            ],
            "fbcbt_b": [
                (_NOW - 600, 100.0, True),
                (_NOW - 500, 200.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_budget_consumed_by_tool(
        _WIN, "fbcbt_a", 25.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float), f"expected float, got {type(result)}"
    expected = 0.0 + 5.0 + 25.0  # 30.0ms
    assert abs(result - expected) < 1e-9, (
        f"budget_a=30ms; kills budget_b=250ms/always-0; got {result}"
    )


def test_fleet_sla_budget_consumed_by_tool_all_compliant_returns_zero() -> None:
    """All latencies <= threshold → budget consumed = 0.0."""
    _reset()
    store = _make_store(
        {
            "fbcbt_ok": [(_NOW - float(d), 10.0, True) for d in [900, 800, 700]],
        }
    )
    result = get_windowed_fleet_latency_sla_budget_consumed_by_tool(
        _WIN, "fbcbt_ok", 50.0, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9, f"all compliant → 0.0; got {result}"


def test_fleet_sla_budget_consumed_by_tool_threshold_is_inclusive() -> None:
    """Latency == threshold contributes 0 overage (not violated)."""
    _reset()
    store = _make_store(
        {
            "fbcbt_exact": [
                (_NOW - 900, 50.0, True),  # == threshold, 0 overage
                (_NOW - 800, 51.0, True),  # > threshold, 1ms overage
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_budget_consumed_by_tool(
        _WIN, "fbcbt_exact", 50.0, store=store, now_ms=_NOW
    )
    assert abs(result - 1.0) < 1e-9, (
        f"50ms==threshold contributes 0; 51ms contributes 1ms; got {result}"
    )


def test_fleet_sla_budget_consumed_by_tool_exact_overage_values() -> None:
    """Budget = exact sum of overages above threshold."""
    _reset()
    store = _make_store(
        {
            "fbcbt_exact2": [
                (_NOW - 900, 100.0, True),  # overage = 100 - 25 = 75
                (_NOW - 800, 200.0, True),  # overage = 200 - 25 = 175
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_budget_consumed_by_tool(
        _WIN, "fbcbt_exact2", 25.0, store=store, now_ms=_NOW
    )
    assert abs(result - 250.0) < 1e-9, f"expected 250ms; got {result}"


def test_fleet_sla_budget_consumed_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store(
        {
            "fbcbt_other": [(_NOW - 500, 100.0, True)],
        }
    )
    result = get_windowed_fleet_latency_sla_budget_consumed_by_tool(
        _WIN, "nonexistent", 25.0, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9
    assert isinstance(result, float)


def test_fleet_sla_budget_consumed_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_sla_budget_consumed_by_tool(
        _WIN, "any_tool", 25.0, store={}, now_ms=_NOW
    )
    assert abs(result) < 1e-9


def test_fleet_sla_budget_consumed_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store(
        {
            "fbcbt_old": [(_NOW - _WIN - float(d), 500.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_sla_budget_consumed_by_tool(
        _WIN, "fbcbt_old", 10.0, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fbcbt_rt": [
                (_NOW - 400, 50.0, True),  # overage = 50 - 25 = 25ms
                (_NOW - 300, 100.0, True),  # overage = 100 - 25 = 75ms
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_budget_consumed_by_tool(
        _WIN, "fbcbt_rt", 25.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 100.0) < 1e-9  # 25 + 75 = 100ms
