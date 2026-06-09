"""Item 1151: get_windowed_fleet_latency_sla_violation_rate(window_ms, sla_ms, *, store=None, now_ms=None) -> float
-- fleet-wide SLA violation rate: fraction of calls with latency > sla_ms.
Thin composition: 1.0 - get_windowed_fleet_latency_sla_compliance_rate(...).
Returns float in [0.0, 1.0]. 0.0 for empty window.

PRIMARY DISC.:
  pooled [10, 50, 200, 300], sla_ms=100ms
  violating (>100): [200, 300] → rate=2/4=0.5
  compliance_rate=0.5 → violation_rate=0.5 (composition: both are 0.5)
  Use different fixture to show non-trivial: [10, 50, 200], sla=100ms
  violation_rate = 1/3 ≈ 0.333 ≠ compliance_rate=2/3
  (PRIMARY DISC.: kills always-0; composition check: violation+compliance=1.0).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_sla_violation_rate,
    get_windowed_fleet_latency_sla_compliance_rate,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_sla_violation_rate_primary_discriminator() -> None:
    """PRIMARY DISC.: violation_rate=1/3≈0.333 for [10,50,200] sla=100ms."""
    _reset()
    store = _make_store({
        "fvr_a": [(_NOW - 900, 10.0, True), (_NOW - 800, 200.0, True)],
        "fvr_b": [(_NOW - 700, 50.0, True)],
    })
    result = get_windowed_fleet_latency_sla_violation_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    expected = 1.0 / 3.0
    assert abs(result - expected) < 1e-9, (
        f"violation_rate=1/3; kills always-0; got {result}"
    )


def test_fleet_sla_violation_plus_compliance_is_one() -> None:
    """Composition invariant: violation_rate + compliance_rate == 1.0 always."""
    _reset()
    store = _make_store({
        "fvr_comp_a": [(_NOW - 900, 10.0, True), (_NOW - 800, 200.0, True)],
        "fvr_comp_b": [(_NOW - 700, 50.0, True), (_NOW - 600, 300.0, True)],
    })
    viol = get_windowed_fleet_latency_sla_violation_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    comp = get_windowed_fleet_latency_sla_compliance_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(viol + comp - 1.0) < 1e-12, f"viol+comp={viol+comp} != 1.0"


def test_fleet_sla_violation_all_compliant_returns_zero() -> None:
    """All calls at or below SLA -> 0.0."""
    _reset()
    store = _make_store({
        "fvr_ok": [(_NOW - float(d), 50.0, True) for d in [900, 800, 700]],
    })
    result = get_windowed_fleet_latency_sla_violation_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"all compliant -> 0.0; got {result}"


def test_fleet_sla_violation_all_violating_returns_one() -> None:
    """All calls above SLA -> 1.0."""
    _reset()
    store = _make_store({
        "fvr_all": [(_NOW - float(d), 200.0, True) for d in [900, 800, 700]],
    })
    result = get_windowed_fleet_latency_sla_violation_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"all violating -> 1.0; got {result}"


def test_fleet_sla_violation_empty_store_returns_zero() -> None:
    """Empty store -> 0.0 (vacuous no-violation)."""
    _reset()
    result = get_windowed_fleet_latency_sla_violation_rate(_WIN, 100.0, store={}, now_ms=_NOW)
    assert abs(result) < 1e-9, f"empty -> 0.0; got {result}"


def test_fleet_sla_violation_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "fvr_old": [(_NOW - _WIN - float(d), 500.0, True) for d in [300, 200, 100]],
    })
    result = get_windowed_fleet_latency_sla_violation_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"no in-window calls -> 0.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fvr_rt": [(_NOW - 400, 30.0, True), (_NOW - 200, 200.0, True)],
    })
    result = get_windowed_fleet_latency_sla_violation_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 0.5) < 1e-9
