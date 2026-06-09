"""Item 1158: get_windowed_fleet_latency_p95_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide 95th percentile latency.
Thin composition: get_windowed_fleet_latency_percentile_ms(window_ms, 95.0, ...).
Returns float. 0.0 for empty window.

PRIMARY DISC.:
  pooled sorted [10,20,30,40,50,60,70,80,90,100,1000], n=11
  P95: ceil(0.95*11)-1 = 10 → latencies[10] = 1000ms
  kills P50=60ms; kills mean≈141ms; verifies nearest-rank at 95.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_p95_ms,
    get_windowed_fleet_latency_percentile_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_p95_primary_discriminator() -> None:
    """PRIMARY DISC.: P95=1000ms for n=11; kills P50=60ms and mean≈141ms."""
    _reset()
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 1000.0]
    store = _make_store({
        "fp95_a": [(_NOW - float(1000 - i * 90), lat, True) for i, lat in enumerate(latencies)],
    })
    result = get_windowed_fleet_latency_p95_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 1000.0) < 1e-9, (
        f"P95=1000ms (nearest-rank index 10); kills P50=60/mean≈141; got {result}"
    )


def test_fleet_p95_composition_with_percentile_ms() -> None:
    """Composition: p95_ms == percentile_ms(95.0) for same store."""
    _reset()
    store = _make_store({
        "fp95_comp": [(_NOW - float(1000 - i * 80), float(i * 10 + 10), True) for i in range(8)],
    })
    p95 = get_windowed_fleet_latency_p95_ms(_WIN, store=store, now_ms=_NOW)
    generic = get_windowed_fleet_latency_percentile_ms(_WIN, 95.0, store=store, now_ms=_NOW)
    assert abs(p95 - generic) < 1e-12, (
        f"p95_ms must equal percentile_ms(95.0); got p95={p95} vs generic={generic}"
    )


def test_fleet_p95_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_p95_ms(_WIN, store={}, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_p95_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "fp95_old": [(_NOW - _WIN - float(d), 500.0, True) for d in [300, 200, 100]],
    })
    result = get_windowed_fleet_latency_p95_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_p95_all_equal_returns_that_value() -> None:
    """All calls at same latency -> P95 == that latency."""
    _reset()
    store = _make_store({
        "fp95_eq": [(_NOW - float(d), 42.0, True) for d in [900, 700, 500, 300]],
    })
    result = get_windowed_fleet_latency_p95_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 42.0) < 1e-9, f"all equal -> 42.0; got {result}"


def test_fleet_p95_single_call() -> None:
    """Single call -> P95 == that call's latency."""
    _reset()
    store = _make_store({
        "fp95_one": [(_NOW - 300, 77.0, True)],
    })
    result = get_windowed_fleet_latency_p95_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 77.0) < 1e-9, f"single call -> 77.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fp95_rt": [(_NOW - float(d), float(d), True) for d in range(10, 110, 10)],
    })
    result = get_windowed_fleet_latency_p95_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
