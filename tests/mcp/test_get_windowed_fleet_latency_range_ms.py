"""Item 1134: get_windowed_fleet_latency_range_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide range (max - min) of pooled latencies (ms).
0.0 for empty window or single call. Returns float.

PRIMARY DISC. (pool vs per-tool-then-average):
  tool_a lats=[10,50]ms (range=40ms), tool_b lats=[60,90]ms (range=30ms)
  per-tool-avg range = (40+30)/2 = 35ms
  max-per-tool = 40ms (also wrong)
  pooled [10,50,60,90]: range = 90-10 = 80ms
  (PRIMARY DISC.: kills per-tool-avg=35ms; kills max-per-tool=40ms;
   correct: max(pooled)-min(pooled), return float=80ms).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_range_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_range_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled range=80ms; kills per-tool-avg=35ms and max-per-tool=40ms."""
    _reset()
    store = _make_store({
        "frng_a": [
            (_NOW - 700, 10.0, True),
            (_NOW - 600, 50.0, True),
        ],
        "frng_b": [
            (_NOW - 500, 60.0, True),
            (_NOW - 400, 90.0, True),
        ],
    })
    # pooled [10, 50, 60, 90]: range = 90-10 = 80ms
    result = get_windowed_fleet_latency_range_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 80.0) < 1e-9, (
        f"pooled range=80ms; kills per-tool-avg=35ms, kills max=40ms; got {result}"
    )


def test_fleet_range_all_same_returns_zero() -> None:
    """All latencies equal -> range = 0.0."""
    _reset()
    store = _make_store({
        "frng_flat_a": [(_NOW - float(d), 42.0, True) for d in [400, 300]],
        "frng_flat_b": [(_NOW - float(d), 42.0, True) for d in [200, 100]],
    })
    result = get_windowed_fleet_latency_range_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"all same -> 0.0; got {result}"


def test_fleet_range_single_call_returns_zero() -> None:
    """Single call -> range = 0.0."""
    _reset()
    store = _make_store({
        "frng_one": [(_NOW - 100, 55.0, True)],
    })
    result = get_windowed_fleet_latency_range_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"single call -> 0.0; got {result}"


def test_fleet_range_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_latency_range_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_fleet_range_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "frng_old": [(_NOW - _WIN - float(d), float(d), True) for d in [300, 200, 100]],
    })
    assert get_windowed_fleet_latency_range_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_range_is_max_minus_min() -> None:
    """Range = global max - global min across all tools."""
    _reset()
    store = _make_store({
        "frng_mm_a": [(_NOW - 600, 5.0, True), (_NOW - 500, 55.0, True)],
        "frng_mm_b": [(_NOW - 400, 30.0, True), (_NOW - 300, 100.0, True)],
        "frng_mm_c": [(_NOW - 200, 20.0, True)],
    })
    # global min=5, global max=100, range=95ms
    result = get_windowed_fleet_latency_range_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 95.0) < 1e-9, f"expected 95ms; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "frng_rt_a": [(_NOW - 400, 20.0, True)],
        "frng_rt_b": [(_NOW - 200, 80.0, True)],
    })
    result = get_windowed_fleet_latency_range_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 60.0) < 1e-9
