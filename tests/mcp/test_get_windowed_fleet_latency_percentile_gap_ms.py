"""Item 1127: get_windowed_fleet_latency_percentile_gap_ms(window_ms, p_low, p_high, *, store=None, now_ms=None) -> float
-- fleet-wide gap between two percentiles using pooled nearest-rank latencies.
0.0 for empty window. Returns float.

PRIMARY DISC. (P10/P90 pooling): tool_a lats=[10,90], tool_b lats=[50,50]
  pooled [10,50,50,90]: P10=nearest-rank(rank=ceil(0.1*4)=1,idx=0,lat=10)
                         P90=nearest-rank(rank=ceil(0.9*4)=4,idx=3,lat=90)
  gap = 90-10 = 80ms
  (PRIMARY DISC.: kills per-tool-avg: tool_a gap=80ms, tool_b gap=0ms, avg=40ms != 80ms;
   kills IQR at p=25/75 pooled gap=40ms (different percentiles);
   correct: pool all latencies, nearest-rank both, subtract, return float=80ms).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_percentile_gap_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_percentile_gap_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled P90-P10=80ms; kills per-tool-avg=40ms."""
    _reset()
    store = _make_store(
        {
            "fpg_a": [
                (_NOW - 700, 10.0, True),
                (_NOW - 600, 90.0, True),
            ],
            "fpg_b": [
                (_NOW - 500, 50.0, True),
                (_NOW - 400, 50.0, True),
            ],
        }
    )
    # pooled sorted: [10, 50, 50, 90]
    # P10: rank=ceil(10/100*4)=1, idx=0 -> lat=10
    # P90: rank=ceil(90/100*4)=4, idx=3 -> lat=90
    # gap = 80ms; per-tool-avg = (80+0)/2 = 40ms
    result = get_windowed_fleet_latency_percentile_gap_ms(
        _WIN, 10.0, 90.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 80.0) < 1e-9, f"pooled P90-P10=80ms; kills per-tool-avg=40ms; got {result}"


def test_fleet_percentile_gap_iqr() -> None:
    """IQR = P75-P25 via fleet pooling."""
    _reset()
    store = _make_store(
        {
            "fpg_iqr_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 20.0, True),
            ],
            "fpg_iqr_b": [
                (_NOW - 700, 30.0, True),
                (_NOW - 600, 40.0, True),
            ],
        }
    )
    # pooled sorted: [10, 20, 30, 40]
    # P25: rank=ceil(0.25*4)=1, idx=0 -> 10
    # P75: rank=ceil(0.75*4)=3, idx=2 -> 30
    result = get_windowed_fleet_latency_percentile_gap_ms(
        _WIN, 25.0, 75.0, store=store, now_ms=_NOW
    )
    assert abs(result - 20.0) < 1e-9, f"P75(30)-P25(10)=20ms; got {result}"


def test_fleet_percentile_gap_all_same_returns_zero() -> None:
    """All latencies equal -> gap = 0.0."""
    _reset()
    store = _make_store(
        {
            "fpg_flat_a": [(_NOW - float(d), 42.0, True) for d in [400, 300]],
            "fpg_flat_b": [(_NOW - float(d), 42.0, True) for d in [200, 100]],
        }
    )
    result = get_windowed_fleet_latency_percentile_gap_ms(
        _WIN, 10.0, 90.0, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9, f"all same -> 0.0; got {result}"


def test_fleet_percentile_gap_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert (
        get_windowed_fleet_latency_percentile_gap_ms(_WIN, 25.0, 75.0, store={}, now_ms=_NOW) == 0.0
    )


def test_fleet_percentile_gap_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fpg_old": [(_NOW - _WIN - float(d), float(d), True) for d in [300, 200, 100]],
        }
    )
    assert (
        get_windowed_fleet_latency_percentile_gap_ms(_WIN, 25.0, 75.0, store=store, now_ms=_NOW)
        == 0.0
    )


def test_fleet_percentile_gap_same_percentile_returns_zero() -> None:
    """p_low == p_high -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fpg_same": [(_NOW - float(d), float(d), True) for d in [400, 300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_percentile_gap_ms(
        _WIN, 50.0, 50.0, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9, f"same p -> 0.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fpg_rt_a": [(_NOW - 400, 20.0, True)],
            "fpg_rt_b": [(_NOW - 200, 80.0, True)],
        }
    )
    result = get_windowed_fleet_latency_percentile_gap_ms(
        _WIN, 25.0, 75.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
