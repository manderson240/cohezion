"""Item 1177: get_windowed_fleet_sla_violation_rate_by_tool(window_ms, tool_name,
              threshold_ms, *, store=None, now_ms=None) -> float
-- per-tool SLA violation rate: fraction of calls with latency > threshold_ms.
Thin composition: 1.0 - sla_compliance_rate_by_tool.
Returns float in [0.0, 1.0]. 1.0 for unknown/empty tool.

PRIMARY DISC.:
  tool_a=[10,20,30] threshold=25ms → 1 violation (30>25), violation=1/3≈0.333
  tool_b=[100,200]  threshold=25ms → 2 violations, violation=1.0
  Composition: violation_by_tool + compliance_by_tool == 1.0.
  violation_a=0.333 kills violation_b=1.0; kills fleet_violation (pooled); kills always-0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_sla_violation_rate_by_tool,
    get_windowed_fleet_sla_compliance_rate_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_sla_violation_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: violation_a=1/3 kills violation_b=1.0; kills always-0."""
    _reset()
    store = _make_store(
        {
            "fslavbt_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 20.0, True),
                (_NOW - 700, 30.0, True),
            ],
            "fslavbt_b": [
                (_NOW - 600, 100.0, True),
                (_NOW - 500, 200.0, True),
            ],
        }
    )
    result = get_windowed_fleet_sla_violation_rate_by_tool(
        _WIN, "fslavbt_a", 25.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float), f"expected float, got {type(result)}"
    expected = 1.0 / 3.0
    assert abs(result - expected) < 1e-9, (
        f"violation_a=1/3; kills violation_b=1.0/always-0; got {result}"
    )


def test_fleet_sla_violation_by_tool_composition_with_compliance() -> None:
    """Composition: violation_by_tool + compliance_by_tool == 1.0."""
    _reset()
    store = _make_store(
        {
            "fslavbt_comp": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 20.0, True),
                (_NOW - 700, 30.0, True),
                (_NOW - 600, 40.0, True),
            ],
        }
    )
    for threshold in [15.0, 25.0, 35.0, 50.0]:
        violation = get_windowed_fleet_sla_violation_rate_by_tool(
            _WIN, "fslavbt_comp", threshold, store=store, now_ms=_NOW
        )
        compliance = get_windowed_fleet_sla_compliance_rate_by_tool(
            _WIN, "fslavbt_comp", threshold, store=store, now_ms=_NOW
        )
        assert abs(violation + compliance - 1.0) < 1e-9, (
            f"threshold={threshold}: violation({violation}) + compliance({compliance}) != 1.0"
        )


def test_fleet_sla_violation_by_tool_all_compliant() -> None:
    """All latencies <= threshold -> violation == 0.0."""
    _reset()
    store = _make_store(
        {
            "fslavbt_ok": [(_NOW - float(d), 10.0, True) for d in [900, 800, 700]],
        }
    )
    result = get_windowed_fleet_sla_violation_rate_by_tool(
        _WIN, "fslavbt_ok", 50.0, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9


def test_fleet_sla_violation_by_tool_none_compliant() -> None:
    """All latencies > threshold -> violation == 1.0."""
    _reset()
    store = _make_store(
        {
            "fslavbt_none": [(_NOW - float(d), 500.0, True) for d in [900, 800, 700]],
        }
    )
    result = get_windowed_fleet_sla_violation_rate_by_tool(
        _WIN, "fslavbt_none", 10.0, store=store, now_ms=_NOW
    )
    assert abs(result - 1.0) < 1e-9


def test_fleet_sla_violation_by_tool_unknown_tool_returns_one() -> None:
    """Unknown tool -> 1.0 (vacuous: no calls = all violations)."""
    _reset()
    store = _make_store(
        {
            "fslavbt_other": [(_NOW - 500, 10.0, True)],
        }
    )
    result = get_windowed_fleet_sla_violation_rate_by_tool(
        _WIN, "nonexistent", 50.0, store=store, now_ms=_NOW
    )
    assert abs(result - 1.0) < 1e-9, f"unknown tool -> 1.0; got {result}"
    assert isinstance(result, float)


def test_fleet_sla_violation_by_tool_empty_store_returns_one() -> None:
    """Empty store -> 1.0 (vacuous)."""
    _reset()
    result = get_windowed_fleet_sla_violation_rate_by_tool(
        _WIN, "any_tool", 50.0, store={}, now_ms=_NOW
    )
    assert abs(result - 1.0) < 1e-9


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fslavbt_rt": [
                (_NOW - 400, 10.0, True),
                (_NOW - 300, 100.0, True),
            ],
        }
    )
    result = get_windowed_fleet_sla_violation_rate_by_tool(
        _WIN, "fslavbt_rt", 50.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 0.5) < 1e-9  # 1 out of 2 violates
