"""Item 1142: get_windowed_fleet_latency_median_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide median of pooled latencies (ms).
0.0 for empty window. Returns float.
Even-n: average of the two middle values (linear interpolation).

PRIMARY DISC. (fleet-pooled median vs per-tool-avg-of-medians):
  tool_a lats=[10,20,30] (median=20ms)
  tool_b lats=[1,100] (median=(1+100)/2=50.5ms)
  per-tool-avg-median = (20+50.5)/2 = 35.25ms
  pooled sorted=[1,10,20,30,100] n=5, median=idx=2, lat=20ms
  (PRIMARY DISC.: kills per-tool-avg=35.25ms≠20ms;
   correct: sort ALL pooled latencies, return middle value=20ms).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_median_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_median_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled median=20ms; kills per-tool-avg-median=35.25ms."""
    _reset()
    store = _make_store({
        "fmed_a": [
            (_NOW - 900, 10.0, True),
            (_NOW - 800, 20.0, True),
            (_NOW - 700, 30.0, True),
        ],
        "fmed_b": [
            (_NOW - 600, 1.0, True),
            (_NOW - 500, 100.0, True),
        ],
    })
    # pooled sorted [1, 10, 20, 30, 100], n=5, median=idx2=20ms
    result = get_windowed_fleet_latency_median_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 20.0) < 1e-9, (
        f"pooled median=20ms; kills per-tool-avg=35.25ms; got {result}"
    )


def test_fleet_median_even_count() -> None:
    """Even n -> average of two middle values."""
    _reset()
    store = _make_store({
        "fmed_ev_a": [(_NOW - 700, 10.0, True), (_NOW - 600, 20.0, True)],
        "fmed_ev_b": [(_NOW - 500, 30.0, True), (_NOW - 400, 40.0, True)],
    })
    # pooled sorted [10, 20, 30, 40], n=4, median=(20+30)/2=25ms
    result = get_windowed_fleet_latency_median_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 25.0) < 1e-9, f"even n -> 25ms; got {result}"


def test_fleet_median_single_call() -> None:
    """Single call -> median = that latency."""
    _reset()
    store = _make_store({
        "fmed_sc": [(_NOW - 100, 55.0, True)],
    })
    result = get_windowed_fleet_latency_median_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 55.0) < 1e-9, f"single call -> 55.0; got {result}"


def test_fleet_median_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_median_ms(_WIN, store={}, now_ms=_NOW)
    assert result == 0.0


def test_fleet_median_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "fmed_old": [(_NOW - _WIN - float(d), float(d), True) for d in [300, 200, 100]],
    })
    result = get_windowed_fleet_latency_median_ms(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0


def test_fleet_median_outlier_robustness() -> None:
    """Outlier does NOT shift median (unlike mean)."""
    _reset()
    # [10, 20, 30, 100_000] — mean ≈ 25010, median=(20+30)/2=25
    store = _make_store({
        "fmed_out": [
            (_NOW - 900, 10.0, True),
            (_NOW - 800, 20.0, True),
            (_NOW - 700, 30.0, True),
            (_NOW - 600, 100_000.0, True),
        ],
    })
    result = get_windowed_fleet_latency_median_ms(_WIN, store=store, now_ms=_NOW)
    # median = (20+30)/2 = 25ms — not inflated by outlier
    assert abs(result - 25.0) < 1e-9, f"outlier doesn't shift median; expected 25ms; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fmed_rt_a": [(_NOW - 400, 30.0, True)],
        "fmed_rt_b": [(_NOW - 200, 70.0, True)],
    })
    result = get_windowed_fleet_latency_median_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 50.0) < 1e-9
