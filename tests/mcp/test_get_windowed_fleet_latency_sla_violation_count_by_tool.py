"""Item 1189: get_windowed_fleet_latency_sla_violation_count_by_tool(
              window_ms, tool_name, threshold_ms, *, store=None, now_ms=None) -> int
-- per-tool count of SLA-violating calls (latency > threshold_ms).
Returns int. 0 for unknown/empty tool or all-compliant.

PRIMARY DISC.:
  tool_a=[10,20,30] threshold=25ms → 1 violation (30>25)
  tool_b=[100,200,300] threshold=25ms → 3 violations
  fleet_count = 4 (all 6 calls pooled: 1+3)
  count_a=1 kills count_b=3; kills fleet_count=4; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_sla_violation_count_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_sla_violation_count_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: count_a=1 kills count_b=3; kills fleet_count=4; kills always-0."""
    _reset()
    store = _make_store(
        {
            "fsvcbt_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 20.0, True),
                (_NOW - 700, 30.0, True),  # violates: 30 > 25
            ],
            "fsvcbt_b": [
                (_NOW - 600, 100.0, True),  # violates
                (_NOW - 500, 200.0, True),  # violates
                (_NOW - 400, 300.0, True),  # violates
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_violation_count_by_tool(
        _WIN, "fsvcbt_a", 25.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, int), f"expected int, got {type(result)}"
    assert result == 1, f"count_a=1; kills count_b=3/fleet_count=4/always-0; got {result}"


def test_fleet_sla_violation_count_by_tool_all_compliant_returns_zero() -> None:
    """All latencies <= threshold → 0."""
    _reset()
    store = _make_store(
        {
            "fsvcbt_ok": [(_NOW - float(d), 10.0, True) for d in [900, 800, 700]],
        }
    )
    result = get_windowed_fleet_latency_sla_violation_count_by_tool(
        _WIN, "fsvcbt_ok", 50.0, store=store, now_ms=_NOW
    )
    assert result == 0


def test_fleet_sla_violation_count_by_tool_threshold_is_exclusive() -> None:
    """Latency == threshold is NOT a violation (threshold is inclusive boundary)."""
    _reset()
    store = _make_store(
        {
            "fsvcbt_bnd": [
                (_NOW - 900, 50.0, True),  # == threshold, NOT a violation
                (_NOW - 800, 51.0, True),  # > threshold, IS a violation
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_violation_count_by_tool(
        _WIN, "fsvcbt_bnd", 50.0, store=store, now_ms=_NOW
    )
    assert result == 1, f"50ms==threshold not a violation; 51ms is; got {result}"


def test_fleet_sla_violation_count_by_tool_counts_correctly() -> None:
    """Counts exactly the violating calls."""
    _reset()
    store = _make_store(
        {
            "fsvcbt_cnt": [
                (_NOW - 900, 100.0, True),
                (_NOW - 800, 200.0, True),
                (_NOW - 700, 300.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_violation_count_by_tool(
        _WIN, "fsvcbt_cnt", 25.0, store=store, now_ms=_NOW
    )
    assert result == 3


def test_fleet_sla_violation_count_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0."""
    _reset()
    store = _make_store(
        {
            "fsvcbt_other": [(_NOW - 500, 100.0, True)],
        }
    )
    result = get_windowed_fleet_latency_sla_violation_count_by_tool(
        _WIN, "nonexistent", 25.0, store=store, now_ms=_NOW
    )
    assert result == 0
    assert isinstance(result, int)


def test_fleet_sla_violation_count_by_tool_empty_store_returns_zero() -> None:
    """Empty store → 0."""
    _reset()
    result = get_windowed_fleet_latency_sla_violation_count_by_tool(
        _WIN, "any_tool", 25.0, store={}, now_ms=_NOW
    )
    assert result == 0


def test_fleet_sla_violation_count_by_tool_outside_window_returns_zero() -> None:
    """All calls outside window → 0."""
    _reset()
    store = _make_store(
        {
            "fsvcbt_old": [(_NOW - _WIN - float(d), 500.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_sla_violation_count_by_tool(
        _WIN, "fsvcbt_old", 10.0, store=store, now_ms=_NOW
    )
    assert result == 0


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    store = _make_store(
        {
            "fsvcbt_rt": [
                (_NOW - 400, 30.0, True),  # violates threshold=25ms
                (_NOW - 300, 10.0, True),  # compliant
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_violation_count_by_tool(
        _WIN, "fsvcbt_rt", 25.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, int)
    assert result == 1
