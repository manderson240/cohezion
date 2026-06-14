"""Item 1190: get_windowed_fleet_latency_sla_compliance_count_by_tool(
              window_ms, tool_name, threshold_ms, *, store=None, now_ms=None) -> int
-- per-tool count of SLA-compliant calls (latency <= threshold_ms).
Returns int. 0 for unknown/empty tool.
Composition: compliance_count + violation_count == total_call_count.

PRIMARY DISC.:
  tool_a=[10,20,30] threshold=25ms → 2 compliant (10≤25, 20≤25, 30>25)
  tool_b=[100,200,300] threshold=25ms → 0 compliant
  count_a=2 kills count_b=0; kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_sla_compliance_count_by_tool,
    get_windowed_fleet_latency_sla_violation_count_by_tool,
    get_windowed_fleet_total_call_count_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_sla_compliance_count_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: count_a=2 kills count_b=0; kills always-0."""
    _reset()
    store = _make_store(
        {
            "fsccbt_a": [
                (_NOW - 900, 10.0, True),  # ≤ 25: compliant
                (_NOW - 800, 20.0, True),  # ≤ 25: compliant
                (_NOW - 700, 30.0, True),  # > 25: violation
            ],
            "fsccbt_b": [
                (_NOW - 600, 100.0, True),  # violation
                (_NOW - 500, 200.0, True),  # violation
                (_NOW - 400, 300.0, True),  # violation
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_compliance_count_by_tool(
        _WIN, "fsccbt_a", 25.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, int), f"expected int, got {type(result)}"
    assert result == 2, f"count_a=2; kills count_b=0/always-0; got {result}"


def test_fleet_sla_compliance_count_composition_with_violation_and_total() -> None:
    """Composition: compliance_count + violation_count == total_call_count."""
    _reset()
    store = _make_store(
        {
            "fsccbt_comp": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 30.0, True),
                (_NOW - 700, 50.0, True),
                (_NOW - 600, 100.0, True),
            ],
        }
    )
    compliance = get_windowed_fleet_latency_sla_compliance_count_by_tool(
        _WIN, "fsccbt_comp", 25.0, store=store, now_ms=_NOW
    )
    violation = get_windowed_fleet_latency_sla_violation_count_by_tool(
        _WIN, "fsccbt_comp", 25.0, store=store, now_ms=_NOW
    )
    total = get_windowed_fleet_total_call_count_by_tool(
        _WIN, "fsccbt_comp", store=store, now_ms=_NOW
    )
    assert compliance + violation == total, (
        f"compliance({compliance}) + violation({violation}) != total({total})"
    )


def test_fleet_sla_compliance_count_threshold_inclusive() -> None:
    """Latency == threshold is compliant (inclusive)."""
    _reset()
    store = _make_store(
        {
            "fsccbt_incl": [
                (_NOW - 900, 50.0, True),  # == threshold: compliant
                (_NOW - 800, 51.0, True),  # > threshold: violation
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_compliance_count_by_tool(
        _WIN, "fsccbt_incl", 50.0, store=store, now_ms=_NOW
    )
    assert result == 1, f"50ms==threshold is compliant; got {result}"


def test_fleet_sla_compliance_count_all_compliant() -> None:
    """All calls <= threshold → count == total_call_count."""
    _reset()
    store = _make_store(
        {
            "fsccbt_all": [(_NOW - float(d), 10.0, True) for d in [900, 800, 700]],
        }
    )
    result = get_windowed_fleet_latency_sla_compliance_count_by_tool(
        _WIN, "fsccbt_all", 50.0, store=store, now_ms=_NOW
    )
    assert result == 3


def test_fleet_sla_compliance_count_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0."""
    _reset()
    store = _make_store(
        {
            "fsccbt_other": [(_NOW - 500, 10.0, True)],
        }
    )
    result = get_windowed_fleet_latency_sla_compliance_count_by_tool(
        _WIN, "nonexistent", 25.0, store=store, now_ms=_NOW
    )
    assert result == 0
    assert isinstance(result, int)


def test_fleet_sla_compliance_count_empty_store_returns_zero() -> None:
    """Empty store → 0."""
    _reset()
    result = get_windowed_fleet_latency_sla_compliance_count_by_tool(
        _WIN, "any_tool", 25.0, store={}, now_ms=_NOW
    )
    assert result == 0


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    store = _make_store(
        {
            "fsccbt_rt": [
                (_NOW - 400, 10.0, True),  # compliant
                (_NOW - 300, 50.0, True),  # violation (>25)
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_compliance_count_by_tool(
        _WIN, "fsccbt_rt", 25.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, int)
    assert result == 1
