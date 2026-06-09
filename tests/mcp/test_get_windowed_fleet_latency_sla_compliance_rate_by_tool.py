"""Item 1196: get_windowed_fleet_latency_sla_compliance_rate_by_tool(
              window_ms, tool_name, threshold_ms, *, store=None, now_ms=None) -> float
-- per-tool fraction of calls complying with SLA (latency <= threshold_ms).
Returns float in [0.0, 1.0]. 0.0 for unknown/empty tool.
Formula: compliance_count / total_count.

PRIMARY DISC.:
  tool_a=[10,20,30] threshold=25ms → 2/3 ≈ 0.667
  tool_b=[100,200,300] threshold=25ms → 0/3 = 0.0
  rate_a≈0.667 kills rate_b=0.0; kills always-0.
  Composition: compliance_rate + violation_rate == 1.0.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_sla_compliance_rate_by_tool,
    get_windowed_fleet_latency_sla_violation_rate_by_tool,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_sla_compliance_rate_by_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: rate_a≈0.667 kills rate_b=0.0; kills always-0."""
    _reset()
    store = _make_store({
        "fscrt_a": [
            (_NOW - 900, 10.0, True),  # compliant
            (_NOW - 600, 20.0, True),  # compliant
            (_NOW - 300, 30.0, True),  # violation
        ],
        "fscrt_b": [
            (_NOW - 800, 100.0, True),  # violation
            (_NOW - 500, 200.0, True),  # violation
            (_NOW - 200, 300.0, True),  # violation
        ],
    })
    rate_a = get_windowed_fleet_latency_sla_compliance_rate_by_tool(
        _WIN, "fscrt_a", 25.0, store=store, now_ms=_NOW
    )
    rate_b = get_windowed_fleet_latency_sla_compliance_rate_by_tool(
        _WIN, "fscrt_b", 25.0, store=store, now_ms=_NOW
    )
    assert isinstance(rate_a, float), f"expected float, got {type(rate_a)}"
    assert abs(rate_a - 2.0 / 3.0) < 1e-9, (
        f"rate_a=2/3≈0.667; kills rate_b=0.0/always-0; got {rate_a}"
    )
    assert rate_b == 0.0, f"rate_b should be 0.0; got {rate_b}"


def test_fleet_sla_compliance_rate_composition_with_violation_rate() -> None:
    """Composition: compliance_rate + violation_rate == 1.0."""
    _reset()
    store = _make_store({
        "fscrt_comp": [
            (_NOW - 900, 10.0, True),   # compliant
            (_NOW - 700, 30.0, True),   # violation
            (_NOW - 500, 50.0, True),   # violation
            (_NOW - 300, 15.0, True),   # compliant
        ],
    })
    compliance = get_windowed_fleet_latency_sla_compliance_rate_by_tool(
        _WIN, "fscrt_comp", 25.0, store=store, now_ms=_NOW
    )
    violation = get_windowed_fleet_latency_sla_violation_rate_by_tool(
        _WIN, "fscrt_comp", 25.0, store=store, now_ms=_NOW
    )
    assert abs(compliance + violation - 1.0) < 1e-9, (
        f"compliance({compliance}) + violation({violation}) != 1.0"
    )


def test_fleet_sla_compliance_rate_all_compliant() -> None:
    """All calls <= threshold → 1.0."""
    _reset()
    store = _make_store({
        "fscrt_all": [(_NOW - float(d), 10.0, True) for d in [900, 600, 300]],
    })
    result = get_windowed_fleet_latency_sla_compliance_rate_by_tool(
        _WIN, "fscrt_all", 50.0, store=store, now_ms=_NOW
    )
    assert result == 1.0


def test_fleet_sla_compliance_rate_threshold_inclusive() -> None:
    """Latency == threshold is compliant (inclusive boundary)."""
    _reset()
    store = _make_store({
        "fscrt_bnd": [
            (_NOW - 500, 50.0, True),   # == threshold: compliant
            (_NOW - 300, 51.0, True),   # > threshold: violation
        ],
    })
    result = get_windowed_fleet_latency_sla_compliance_rate_by_tool(
        _WIN, "fscrt_bnd", 50.0, store=store, now_ms=_NOW
    )
    assert abs(result - 0.5) < 1e-9, f"1/2 = 0.5; got {result}"


def test_fleet_sla_compliance_rate_unknown_tool_returns_zero() -> None:
    """Unknown tool → 0.0."""
    _reset()
    store = _make_store({
        "fscrt_other": [(_NOW - 500, 10.0, True)],
    })
    result = get_windowed_fleet_latency_sla_compliance_rate_by_tool(
        _WIN, "nonexistent", 25.0, store=store, now_ms=_NOW
    )
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_sla_compliance_rate_empty_store_returns_zero() -> None:
    """Empty store → 0.0."""
    _reset()
    result = get_windowed_fleet_latency_sla_compliance_rate_by_tool(
        _WIN, "any_tool", 25.0, store={}, now_ms=_NOW
    )
    assert result == 0.0


def test_fleet_sla_compliance_rate_outside_window_returns_zero() -> None:
    """All calls outside window → 0.0."""
    _reset()
    store = _make_store({
        "fscrt_old": [(_NOW - _WIN - float(d), 5.0, True) for d in [300, 200, 100]],
    })
    result = get_windowed_fleet_latency_sla_compliance_rate_by_tool(
        _WIN, "fscrt_old", 1000.0, store=store, now_ms=_NOW
    )
    assert result == 0.0


def test_returns_float_type() -> None:
    """Return type is float in [0.0, 1.0]."""
    _reset()
    store = _make_store({
        "fscrt_rt": [
            (_NOW - 400, 10.0, True),  # compliant
            (_NOW - 300, 30.0, True),  # violation
        ],
    })
    result = get_windowed_fleet_latency_sla_compliance_rate_by_tool(
        _WIN, "fscrt_rt", 25.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert result == 0.5
