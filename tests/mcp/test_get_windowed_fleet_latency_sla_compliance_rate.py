"""Item 1150: get_windowed_fleet_latency_sla_compliance_rate(window_ms, sla_ms, *, store=None, now_ms=None) -> float
-- fleet-wide SLA compliance rate: fraction of calls with latency <= sla_ms.
Returns float in [0.0, 1.0]. 1.0 for empty window (vacuous).
Uses <= (inclusive): a call at exactly sla_ms IS compliant.

PRIMARY DISC. (SLA discriminator):
  pooled [10, 50, 200, 300], sla_ms=100ms
  compliant (<=100): [10, 50] → rate=2/4=0.5
  (PRIMARY DISC.: kills always-1.0; kills <-strict (lat=100 not counted);
   correct: lat<=sla_ms, return float=0.5).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_sla_compliance_rate,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_sla_compliance_primary_discriminator() -> None:
    """PRIMARY DISC.: compliance_rate=0.5 for [10,50,200,300] sla=100ms; kills always-1.0."""
    _reset()
    store = _make_store(
        {
            "fsla_a": [(_NOW - 900, 10.0, True), (_NOW - 800, 200.0, True)],
            "fsla_b": [(_NOW - 700, 50.0, True), (_NOW - 600, 300.0, True)],
        }
    )
    result = get_windowed_fleet_latency_sla_compliance_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 0.5) < 1e-9, f"compliance_rate=0.5 (2/4); kills always-1.0; got {result}"


def test_fleet_sla_compliance_boundary_inclusive() -> None:
    """lat == sla_ms is compliant (<=); boundary call IS counted."""
    _reset()
    store = _make_store(
        {
            "fsla_bnd": [
                (_NOW - 700, 100.0, True),  # exactly at SLA, IS compliant
                (_NOW - 600, 200.0, True),  # above SLA, NOT compliant
            ],
        }
    )
    result = get_windowed_fleet_latency_sla_compliance_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result - 0.5) < 1e-9, f"boundary inclusive -> 0.5; got {result}"


def test_fleet_sla_compliance_all_compliant_returns_one() -> None:
    """All calls below or at SLA -> 1.0."""
    _reset()
    store = _make_store(
        {
            "fsla_all": [(_NOW - float(d), 50.0, True) for d in [900, 800, 700]],
        }
    )
    result = get_windowed_fleet_latency_sla_compliance_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"all compliant -> 1.0; got {result}"


def test_fleet_sla_compliance_none_compliant_returns_zero() -> None:
    """All calls above SLA -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fsla_none": [(_NOW - float(d), 200.0, True) for d in [900, 800, 700]],
        }
    )
    result = get_windowed_fleet_latency_sla_compliance_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"none compliant -> 0.0; got {result}"


def test_fleet_sla_compliance_empty_store_returns_one() -> None:
    """Empty store -> 1.0 (vacuous)."""
    _reset()
    result = get_windowed_fleet_latency_sla_compliance_rate(_WIN, 100.0, store={}, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"empty -> 1.0; got {result}"


def test_fleet_sla_compliance_outside_window_returns_one() -> None:
    """All calls outside window -> 1.0 (vacuous)."""
    _reset()
    store = _make_store(
        {
            "fsla_old": [(_NOW - _WIN - float(d), 500.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_sla_compliance_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"no in-window calls -> 1.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float in [0.0, 1.0]."""
    _reset()
    store = _make_store(
        {
            "fsla_rt": [(_NOW - 400, 30.0, True), (_NOW - 200, 200.0, True)],
        }
    )
    result = get_windowed_fleet_latency_sla_compliance_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0
    assert abs(result - 0.5) < 1e-9
