"""Item 1133: get_windowed_fleet_latency_iqr_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide interquartile range (P75-P25) of pooled latencies (ms).
0.0 for empty window. Returns float.

PRIMARY DISC. (pool vs per-tool-then-average; uses 6-call two-tool fixture):
  tool_a lats=[10,20,30] (per-tool IQR: n=3, P25=rank=ceil(0.75)=1,lat=10; P75=rank=ceil(2.25)=3,lat=30; IQR=20)
  tool_b lats=[60,70,80] (per-tool IQR: P25=60; P75=80; IQR=20)
  per-tool-avg IQR = (20+20)/2 = 20ms
  pooled [10,20,30,60,70,80] sorted: n=6
    P25: rank=ceil(0.25*6)=2, idx=1, lat=20
    P75: rank=ceil(0.75*6)=5, idx=4, lat=70
    fleet IQR = 70-20 = 50ms
  (PRIMARY DISC.: kills per-tool-avg=20ms≠50ms;
   correct: pool all latencies, nearest-rank P75-P25, return float=50ms).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_iqr_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_iqr_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled IQR=50ms; kills per-tool-avg=20ms."""
    _reset()
    store = _make_store(
        {
            "fiq_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 20.0, True),
                (_NOW - 700, 30.0, True),
            ],
            "fiq_b": [
                (_NOW - 600, 60.0, True),
                (_NOW - 500, 70.0, True),
                (_NOW - 400, 80.0, True),
            ],
        }
    )
    # pooled sorted [10, 20, 30, 60, 70, 80], n=6
    # P25: rank=ceil(0.25*6)=2, idx=1, lat=20
    # P75: rank=ceil(0.75*6)=5, idx=4, lat=70
    # IQR = 70-20 = 50ms
    result = get_windowed_fleet_latency_iqr_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 50.0) < 1e-9, f"pooled IQR=50ms; kills per-tool-avg=20ms; got {result}"


def test_fleet_iqr_all_same_returns_zero() -> None:
    """All latencies equal -> IQR = 0.0."""
    _reset()
    store = _make_store(
        {
            "fiq_flat_a": [(_NOW - float(d), 42.0, True) for d in [400, 300]],
            "fiq_flat_b": [(_NOW - float(d), 42.0, True) for d in [200, 100]],
        }
    )
    result = get_windowed_fleet_latency_iqr_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"all same -> 0.0; got {result}"


def test_fleet_iqr_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_latency_iqr_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_fleet_iqr_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fiq_old": [(_NOW - _WIN - float(d), float(d), True) for d in [300, 200, 100]],
        }
    )
    assert get_windowed_fleet_latency_iqr_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_iqr_four_calls() -> None:
    """4-call fixture: [10,50,50,90] IQR = P75-P25 = nearest-rank."""
    _reset()
    store = _make_store(
        {
            "fiq_4_a": [(_NOW - 700, 10.0, True), (_NOW - 600, 90.0, True)],
            "fiq_4_b": [(_NOW - 500, 50.0, True), (_NOW - 400, 50.0, True)],
        }
    )
    # pooled sorted [10, 50, 50, 90], n=4
    # P25: rank=ceil(0.25*4)=1, idx=0, lat=10
    # P75: rank=ceil(0.75*4)=3, idx=2, lat=50
    # IQR = 50-10 = 40ms
    result = get_windowed_fleet_latency_iqr_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 40.0) < 1e-9, f"expected 40ms; got {result}"


def test_fleet_iqr_consistent_with_percentile_gap() -> None:
    """IQR == get_windowed_fleet_latency_percentile_gap_ms(window, 25.0, 75.0)."""
    _reset()
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_fleet_latency_percentile_gap_ms

    store = _make_store(
        {
            "fiq_cg_a": [
                (_NOW - float(d), float(10 * (i + 1)), True)
                for i, d in enumerate([900, 800, 700, 600])
            ],
            "fiq_cg_b": [
                (_NOW - float(d), float(10 * (i + 5)), True)
                for i, d in enumerate([500, 400, 300, 200])
            ],
        }
    )
    iqr = get_windowed_fleet_latency_iqr_ms(_WIN, store=store, now_ms=_NOW)
    gap = get_windowed_fleet_latency_percentile_gap_ms(_WIN, 25.0, 75.0, store=store, now_ms=_NOW)
    assert abs(iqr - gap) < 1e-9, f"IQR={iqr} != percentile_gap_ms(25,75)={gap}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fiq_rt_a": [(_NOW - 400, 20.0, True)],
            "fiq_rt_b": [(_NOW - 200, 80.0, True)],
        }
    )
    result = get_windowed_fleet_latency_iqr_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
