"""Item 1132: get_windowed_fleet_latency_mad_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide mean absolute deviation of pooled latencies (ms).
MAD = mean(|lat - mean_lat|). 0.0 for empty window. Returns float.

PRIMARY DISC. (unequal-count fixture kills per-tool-then-average):
  tool_a lats=[10,20,30] (n=3), tool_b lat=[100] (n=1)
  per-tool-avg: tool_a MAD=(20+10+0)/3=10ms → wait: mean=20, |10-20|+|20-20|+|30-20|=10+0+10=20, MAD=20/3≈6.67ms
                tool_b MAD=0ms (single value); per-tool-avg=(6.67+0)/2=3.33ms
  pooled [10,20,30,100] mean=40: MAD=(|10-40|+|20-40|+|30-40|+|100-40|)/4=(30+20+10+60)/4=120/4=30ms
  (PRIMARY DISC.: kills per-tool-avg=3.33ms≠30ms; correct: pool all latencies,
   compute mean of |lat-pooled_mean|, return float=30ms).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_mad_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_mad_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled MAD=30ms; kills per-tool-avg≈3.33ms."""
    _reset()
    store = _make_store(
        {
            "fmad_a": [
                (_NOW - 900, 10.0, True),
                (_NOW - 800, 20.0, True),
                (_NOW - 700, 30.0, True),
            ],
            "fmad_b": [
                (_NOW - 600, 100.0, True),
            ],
        }
    )
    # pooled [10, 20, 30, 100], mean=40
    # MAD = (|10-40|+|20-40|+|30-40|+|100-40|)/4 = (30+20+10+60)/4 = 120/4 = 30ms
    result = get_windowed_fleet_latency_mad_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 30.0) < 1e-9, f"pooled MAD=30ms; kills per-tool-avg≈3.33ms; got {result}"


def test_fleet_mad_all_same_returns_zero() -> None:
    """All latencies equal -> MAD = 0.0."""
    _reset()
    store = _make_store(
        {
            "fmad_flat_a": [(_NOW - float(d), 42.0, True) for d in [400, 300]],
            "fmad_flat_b": [(_NOW - float(d), 42.0, True) for d in [200, 100]],
        }
    )
    result = get_windowed_fleet_latency_mad_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"all same -> 0.0; got {result}"


def test_fleet_mad_symmetric_two_tools() -> None:
    """Symmetric two-tool fixture: verify correct pooled MAD value."""
    _reset()
    store = _make_store(
        {
            "fmad_sym_a": [(_NOW - 700, 10.0, True), (_NOW - 600, 90.0, True)],
            "fmad_sym_b": [(_NOW - 500, 50.0, True), (_NOW - 400, 50.0, True)],
        }
    )
    # pooled [10, 90, 50, 50], mean=50
    # MAD = (|10-50|+|90-50|+|50-50|+|50-50|)/4 = (40+40+0+0)/4 = 20ms
    result = get_windowed_fleet_latency_mad_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 20.0) < 1e-9, f"expected 20ms; got {result}"


def test_fleet_mad_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_latency_mad_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_fleet_mad_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fmad_old": [(_NOW - _WIN - float(d), float(d), True) for d in [300, 200, 100]],
        }
    )
    assert get_windowed_fleet_latency_mad_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_mad_single_call_returns_zero() -> None:
    """Single call -> MAD=0.0 (|lat-mean| where mean=lat)."""
    _reset()
    store = _make_store(
        {
            "fmad_one": [(_NOW - 100, 55.0, True)],
        }
    )
    result = get_windowed_fleet_latency_mad_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"single call -> 0.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fmad_rt_a": [(_NOW - 400, 20.0, True), (_NOW - 300, 80.0, True)],
            "fmad_rt_b": [(_NOW - 200, 50.0, True)],
        }
    )
    result = get_windowed_fleet_latency_mad_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
