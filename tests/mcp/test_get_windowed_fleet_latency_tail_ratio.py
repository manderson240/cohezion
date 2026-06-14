"""Item 1147: get_windowed_fleet_latency_tail_ratio(window_ms, tail_frac=0.1, *, store=None, now_ms=None) -> float
-- fleet-wide tail ratio: P(100*(1-tail_frac)) / P50 of pooled latencies.
Returns float. 1.0 for empty or zero-median window. Measures tail extremity vs median.
Uses nearest-rank for both percentiles.

PRIMARY DISC. (tail-ratio discriminator):
  pooled sorted [10, 20, 30, 100], tail_frac=0.25
  P75 = nearest-rank: rank=ceil(0.75*4)=3, idx=2, lat=30ms
  P50 = median = (20+30)/2 = 25ms
  ratio = 30/25 = 1.2
  flat [50,50,50,50] → P75=50, P50=50, ratio=1.0
  (PRIMARY DISC.: kills always-1.0; correct=1.2 for skewed data).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_tail_ratio,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_tail_ratio_primary_discriminator() -> None:
    """PRIMARY DISC.: tail_ratio=1.2 for [10,20,30,100] tail_frac=0.25; kills always-1.0."""
    _reset()
    store = _make_store(
        {
            "ftr_a": [(_NOW - 900, 10.0, True), (_NOW - 800, 20.0, True)],
            "ftr_b": [(_NOW - 700, 30.0, True), (_NOW - 600, 100.0, True)],
        }
    )
    # pooled sorted [10, 20, 30, 100]
    # P75: rank=ceil(0.75*4)=3, idx=2, lat=30ms
    # P50: median = (20+30)/2 = 25ms
    # ratio = 30/25 = 1.2
    result = get_windowed_fleet_latency_tail_ratio(_WIN, 0.25, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 1.2) < 1e-9, f"tail_ratio=1.2; kills always-1.0; got {result}"


def test_fleet_tail_ratio_flat_distribution_is_one() -> None:
    """All same latencies -> P_tail = P50 -> ratio=1.0."""
    _reset()
    store = _make_store(
        {
            "ftr_flat": [(_NOW - float(d), 50.0, True) for d in [900, 800, 700, 600]],
        }
    )
    result = get_windowed_fleet_latency_tail_ratio(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"flat -> ratio=1.0; got {result}"


def test_fleet_tail_ratio_empty_store_returns_one() -> None:
    """Empty store -> 1.0 (vacuous no-tail)."""
    _reset()
    result = get_windowed_fleet_latency_tail_ratio(_WIN, store={}, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"empty -> 1.0; got {result}"


def test_fleet_tail_ratio_outside_window_returns_one() -> None:
    """All calls outside window -> 1.0."""
    _reset()
    store = _make_store(
        {
            "ftr_old": [(_NOW - _WIN - float(d), float(d), True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_tail_ratio(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"no in-window calls -> 1.0; got {result}"


def test_fleet_tail_ratio_single_call_returns_one() -> None:
    """Single call -> P_tail=lat, P50=lat -> ratio=1.0."""
    _reset()
    store = _make_store(
        {
            "ftr_sc": [(_NOW - 100, 55.0, True)],
        }
    )
    result = get_windowed_fleet_latency_tail_ratio(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"single call -> ratio=1.0; got {result}"


def test_fleet_tail_ratio_always_ge_one() -> None:
    """Tail ratio >= 1.0 by definition (P_tail >= P50)."""
    _reset()
    store = _make_store(
        {
            "ftr_ge": [
                (_NOW - float(d), float(v), True)
                for d, v in zip([900, 800, 700, 600, 500], [10, 20, 30, 80, 200])
            ],
        }
    )
    result = get_windowed_fleet_latency_tail_ratio(_WIN, store=store, now_ms=_NOW)
    assert result >= 1.0, f"tail ratio must be >= 1.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "ftr_rt_a": [(_NOW - 400, 20.0, True)],
            "ftr_rt_b": [(_NOW - 200, 80.0, True)],
        }
    )
    result = get_windowed_fleet_latency_tail_ratio(_WIN, 0.25, store=store, now_ms=_NOW)
    assert isinstance(result, float)
