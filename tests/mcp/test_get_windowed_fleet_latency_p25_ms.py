"""Item 1162: get_windowed_fleet_latency_p25_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide 25th percentile latency.
Thin composition: get_windowed_fleet_latency_percentile_ms(window_ms, 25.0, ...).
Returns float. 0.0 for empty window.

PRIMARY DISC.:
  [10,20,30,40,50,60,70,80,90,100] n=10
  P25: ceil(0.25*10)-1 = ceil(2.5)-1 = 3-1 = 2 → latencies[2] = 30ms
  kills P50=50ms; kills P75=80ms; kills mean=55ms.
  IQR check: p75_ms(80) - p25_ms(30) == iqr_ms(50).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_p25_ms,
    get_windowed_fleet_latency_percentile_ms,
    get_windowed_fleet_latency_p75_ms,
    get_windowed_fleet_latency_iqr_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_p25_primary_discriminator() -> None:
    """PRIMARY DISC.: P25=30ms; kills P50=50ms, P75=80ms, mean=55ms."""
    _reset()
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    store = _make_store(
        {
            "fp25_a": [(_NOW - float(1000 - i * 95), lat, True) for i, lat in enumerate(latencies)],
        }
    )
    result = get_windowed_fleet_latency_p25_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 30.0) < 1e-9, (
        f"P25=30ms (nearest-rank index 2 of n=10); kills P50=50/P75=80/mean=55; got {result}"
    )


def test_fleet_p25_iqr_sanity() -> None:
    """IQR sanity: p75_ms - p25_ms == iqr_ms."""
    _reset()
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    store = _make_store(
        {
            "fp25_iqr": [
                (_NOW - float(1000 - i * 95), lat, True) for i, lat in enumerate(latencies)
            ],
        }
    )
    p25 = get_windowed_fleet_latency_p25_ms(_WIN, store=store, now_ms=_NOW)
    p75 = get_windowed_fleet_latency_p75_ms(_WIN, store=store, now_ms=_NOW)
    iqr = get_windowed_fleet_latency_iqr_ms(_WIN, store=store, now_ms=_NOW)
    assert abs((p75 - p25) - iqr) < 1e-9, (
        f"P75({p75})-P25({p25})={p75 - p25} should equal iqr({iqr})"
    )


def test_fleet_p25_composition() -> None:
    """Composition: p25_ms == percentile_ms(25.0)."""
    _reset()
    store = _make_store(
        {
            "fp25_comp": [
                (_NOW - float(1000 - i * 80), float(i * 20 + 10), True) for i in range(8)
            ],
        }
    )
    p25 = get_windowed_fleet_latency_p25_ms(_WIN, store=store, now_ms=_NOW)
    generic = get_windowed_fleet_latency_percentile_ms(_WIN, 25.0, store=store, now_ms=_NOW)
    assert abs(p25 - generic) < 1e-12


def test_fleet_p25_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_p25_ms(_WIN, store={}, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_p25_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fp25_old": [(_NOW - _WIN - float(d), 25.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_p25_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_p25_single_call() -> None:
    """Single call -> P25 == that call's latency."""
    _reset()
    store = _make_store(
        {
            "fp25_one": [(_NOW - 300, 66.0, True)],
        }
    )
    result = get_windowed_fleet_latency_p25_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 66.0) < 1e-9


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fp25_rt": [(_NOW - float(d), float(d), True) for d in range(10, 60, 10)],
        }
    )
    result = get_windowed_fleet_latency_p25_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
