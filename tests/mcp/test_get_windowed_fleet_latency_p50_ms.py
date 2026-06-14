"""Item 1160: get_windowed_fleet_latency_p50_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide 50th percentile latency (nearest-rank).
Thin composition: get_windowed_fleet_latency_percentile_ms(window_ms, 50.0, ...).
Returns float. 0.0 for empty window.

PRIMARY DISC.:
  [10,20,30,40,50,60,70,80,90,100] n=10 (even)
  P50 nearest-rank: ceil(0.5*10)-1 = 4 → latencies[4] = 50ms
  arithmetic median = (latencies[4]+latencies[5])/2 = (50+60)/2 = 55ms
  P50=50ms kills median_ms=55ms for even n.
  Composition: p50_ms == percentile_ms(50.0).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_p50_ms,
    get_windowed_fleet_latency_percentile_ms,
    get_windowed_fleet_latency_median_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_p50_primary_discriminator() -> None:
    """PRIMARY DISC.: P50=50ms (nearest-rank) ≠ median_ms=55ms for even n=10."""
    _reset()
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    store = _make_store(
        {
            "fp50_a": [(_NOW - float(1000 - i * 95), lat, True) for i, lat in enumerate(latencies)],
        }
    )
    result = get_windowed_fleet_latency_p50_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 50.0) < 1e-9, (
        f"P50=50ms (nearest-rank index 4 of n=10); kills median=55ms; got {result}"
    )


def test_fleet_p50_differs_from_arithmetic_median_for_even_n() -> None:
    """P50 (nearest-rank) ≠ arithmetic median for even n."""
    _reset()
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    store = _make_store(
        {
            "fp50_diff": [
                (_NOW - float(1000 - i * 95), lat, True) for i, lat in enumerate(latencies)
            ],
        }
    )
    p50 = get_windowed_fleet_latency_p50_ms(_WIN, store=store, now_ms=_NOW)
    median = get_windowed_fleet_latency_median_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(p50 - 50.0) < 1e-9, f"P50 should be 50.0; got {p50}"
    assert abs(median - 55.0) < 1e-9, f"arithmetic median should be 55.0; got {median}"
    assert p50 != median, "P50 nearest-rank ≠ arithmetic median for even n"


def test_fleet_p50_composition_with_percentile_ms() -> None:
    """Composition: p50_ms == percentile_ms(50.0)."""
    _reset()
    store = _make_store(
        {
            "fp50_comp": [
                (_NOW - float(1000 - i * 80), float(i * 15 + 10), True) for i in range(7)
            ],
        }
    )
    p50 = get_windowed_fleet_latency_p50_ms(_WIN, store=store, now_ms=_NOW)
    generic = get_windowed_fleet_latency_percentile_ms(_WIN, 50.0, store=store, now_ms=_NOW)
    assert abs(p50 - generic) < 1e-12, "p50_ms must equal percentile_ms(50.0)"


def test_fleet_p50_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_p50_ms(_WIN, store={}, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_p50_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fp50_old": [(_NOW - _WIN - float(d), 50.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_p50_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9


def test_fleet_p50_odd_n_matches_median() -> None:
    """For odd n, nearest-rank P50 == arithmetic median (same middle element)."""
    _reset()
    # n=5: sorted [10,30,50,70,90], P50 = ceil(0.5*5)-1 = 2 → 50ms; median=50ms
    store = _make_store(
        {
            "fp50_odd": [
                (_NOW - 900, 10.0, True),
                (_NOW - 750, 30.0, True),
                (_NOW - 600, 50.0, True),
                (_NOW - 450, 70.0, True),
                (_NOW - 300, 90.0, True),
            ],
        }
    )
    p50 = get_windowed_fleet_latency_p50_ms(_WIN, store=store, now_ms=_NOW)
    median = get_windowed_fleet_latency_median_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(p50 - median) < 1e-9, f"odd n: P50={p50} should equal median={median}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fp50_rt": [(_NOW - float(d), float(d), True) for d in range(10, 60, 10)],
        }
    )
    result = get_windowed_fleet_latency_p50_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
