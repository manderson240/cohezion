"""Item 1176: get_windowed_fleet_sla_compliance_rate_by_tool(window_ms, tool_name,
              threshold_ms, *, store=None, now_ms=None) -> float
-- per-tool SLA compliance rate: fraction of calls with latency <= threshold_ms.
Returns float in [0.0, 1.0]. 0.0 for unknown/empty tool.

PRIMARY DISC.:
  tool_a=[10,20,30] threshold=25ms → 2/3≈0.667 (10<=25, 20<=25, 30>25)
  tool_b=[100,200]  threshold=25ms → 0/2=0.0
  fleet compliance (pools 5 calls) = 2/5=0.4
  compliance_a=0.667 kills compliance_b=0.0; kills fleet=0.4; kills always-0.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_sla_compliance_rate_by_tool,
    get_windowed_fleet_latency_sla_compliance_rate,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_sla_compliance_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: compliance_a=2/3 kills compliance_b=0.0, fleet=0.4, always-0."""
    _reset()
    store = _make_store({
        "fslacbt_a": [
            (_NOW - 900, 10.0, True),
            (_NOW - 800, 20.0, True),
            (_NOW - 700, 30.0, True),
        ],
        "fslacbt_b": [
            (_NOW - 600, 100.0, True),
            (_NOW - 500, 200.0, True),
        ],
    })
    result = get_windowed_fleet_sla_compliance_rate_by_tool(
        _WIN, "fslacbt_a", 25.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float), f"expected float, got {type(result)}"
    expected = 2.0 / 3.0
    assert abs(result - expected) < 1e-9, (
        f"compliance_a=2/3; kills compliance_b=0/fleet=0.4/always-0; got {result}"
    )


def test_fleet_sla_compliance_by_tool_differs_from_fleet() -> None:
    """Per-tool compliance differs from fleet compliance."""
    _reset()
    store = _make_store({
        "fslacbt_diff_a": [
            (_NOW - 900, 10.0, True),
            (_NOW - 800, 20.0, True),
            (_NOW - 700, 30.0, True),
        ],
        "fslacbt_diff_b": [
            (_NOW - 600, 100.0, True),
            (_NOW - 500, 200.0, True),
        ],
    })
    tool_rate = get_windowed_fleet_sla_compliance_rate_by_tool(
        _WIN, "fslacbt_diff_a", 25.0, store=store, now_ms=_NOW
    )
    fleet_rate = get_windowed_fleet_latency_sla_compliance_rate(
        _WIN, 25.0, store=store, now_ms=_NOW
    )
    # tool_a=2/3≈0.667; fleet=2/5=0.4 — must differ
    assert abs(tool_rate - fleet_rate) > 0.1, (
        f"per-tool({tool_rate}) should differ from fleet({fleet_rate})"
    )


def test_fleet_sla_compliance_by_tool_all_compliant() -> None:
    """All latencies <= threshold -> 1.0."""
    _reset()
    store = _make_store({
        "fslacbt_ok": [(_NOW - float(d), 10.0, True) for d in [900, 800, 700]],
    })
    result = get_windowed_fleet_sla_compliance_rate_by_tool(
        _WIN, "fslacbt_ok", 50.0, store=store, now_ms=_NOW
    )
    assert abs(result - 1.0) < 1e-9, f"all comply -> 1.0; got {result}"


def test_fleet_sla_compliance_by_tool_none_compliant() -> None:
    """All latencies > threshold -> 0.0."""
    _reset()
    store = _make_store({
        "fslacbt_none": [(_NOW - float(d), 500.0, True) for d in [900, 800, 700]],
    })
    result = get_windowed_fleet_sla_compliance_rate_by_tool(
        _WIN, "fslacbt_none", 10.0, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9, f"none comply -> 0.0; got {result}"


def test_fleet_sla_compliance_by_tool_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    store = _make_store({
        "fslacbt_other": [(_NOW - 500, 10.0, True)],
    })
    result = get_windowed_fleet_sla_compliance_rate_by_tool(
        _WIN, "nonexistent", 50.0, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9
    assert isinstance(result, float)


def test_fleet_sla_compliance_by_tool_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_sla_compliance_rate_by_tool(
        _WIN, "any_tool", 50.0, store={}, now_ms=_NOW
    )
    assert abs(result) < 1e-9


def test_fleet_sla_compliance_by_tool_threshold_is_inclusive() -> None:
    """SLA threshold is inclusive (<=): latency == threshold counts as compliant."""
    _reset()
    store = _make_store({
        "fslacbt_incl": [
            (_NOW - 900, 50.0, True),  # == threshold
            (_NOW - 800, 51.0, True),  # > threshold
        ],
    })
    result = get_windowed_fleet_sla_compliance_rate_by_tool(
        _WIN, "fslacbt_incl", 50.0, store=store, now_ms=_NOW
    )
    assert abs(result - 0.5) < 1e-9, f"50ms==threshold complies, 51ms doesn't; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fslacbt_rt": [
            (_NOW - 400, 10.0, True),
            (_NOW - 300, 100.0, True),
        ],
    })
    result = get_windowed_fleet_sla_compliance_rate_by_tool(
        _WIN, "fslacbt_rt", 50.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 0.5) < 1e-9
