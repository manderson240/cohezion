"""Item 1128: get_windowed_fleet_latency_stddev_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide population stddev of pooled latencies across all tools.
0.0 for empty window or single call. Returns float.

PRIMARY DISC. (pool vs per-tool-then-average):
  tool_a lats=[10,90], tool_b lats=[50,50]
  pooled [10,50,50,90]: mean=50, variance=((40²+0²+0²+40²)/4)=800, stddev≈28.28ms
  (PRIMARY DISC.: kills per-tool-avg: tool_a stddev=40ms, tool_b stddev=0ms, avg=20ms≠28.28ms;
   kills max-tool-stddev=40ms;
   correct: pool all latencies, population stddev divides by n, return float≈28.28).
"""

from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_stddev_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_stddev_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled stddev≈28.28ms; kills per-tool-avg=20ms, kills max=40ms."""
    _reset()
    store = _make_store(
        {
            "fsd_a": [
                (_NOW - 700, 10.0, True),
                (_NOW - 600, 90.0, True),
            ],
            "fsd_b": [
                (_NOW - 500, 50.0, True),
                (_NOW - 400, 50.0, True),
            ],
        }
    )
    # pooled: [10, 50, 50, 90], mean=50
    # variance = ((40²+0²+0²+40²)/4) = (1600+0+0+1600)/4 = 800
    # stddev = sqrt(800) ≈ 28.2843
    result = get_windowed_fleet_latency_stddev_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    expected = math.sqrt(800.0)
    assert abs(result - expected) < 1e-6, (
        f"pooled stddev≈{expected:.4f}; kills per-tool-avg=20ms, kills max=40ms; got {result}"
    )


def test_fleet_stddev_all_same_returns_zero() -> None:
    """All latencies equal -> stddev = 0.0."""
    _reset()
    store = _make_store(
        {
            "fsd_flat_a": [(_NOW - float(d), 42.0, True) for d in [400, 300]],
            "fsd_flat_b": [(_NOW - float(d), 42.0, True) for d in [200, 100]],
        }
    )
    result = get_windowed_fleet_latency_stddev_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"all same -> 0.0; got {result}"


def test_fleet_stddev_single_call_returns_zero() -> None:
    """Only one call in window -> 0.0 (population stddev of a single value is 0)."""
    _reset()
    store = _make_store(
        {
            "fsd_one": [(_NOW - 100, 55.0, True)],
        }
    )
    result = get_windowed_fleet_latency_stddev_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"single call -> 0.0; got {result}"


def test_fleet_stddev_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_latency_stddev_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_fleet_stddev_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fsd_old": [(_NOW - _WIN - float(d), float(d), True) for d in [300, 200, 100]],
        }
    )
    assert get_windowed_fleet_latency_stddev_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_stddev_population_not_sample() -> None:
    """Divides by n (population), not n-1 (sample). 3 calls: [10,20,30], pop-stddev≈8.165."""
    _reset()
    store = _make_store(
        {
            "fsd_pop": [
                (_NOW - 300, 10.0, True),
                (_NOW - 200, 20.0, True),
                (_NOW - 100, 30.0, True),
            ],
        }
    )
    # mean=20, variance=((100+0+100)/3)=200/3, stddev=sqrt(200/3)≈8.1650
    # sample-stddev: variance=((100+0+100)/2)=100, stddev=10.0 (different!)
    result = get_windowed_fleet_latency_stddev_ms(_WIN, store=store, now_ms=_NOW)
    expected_population = math.sqrt(200.0 / 3.0)
    sample_stddev = math.sqrt(100.0)
    assert abs(result - expected_population) < 1e-6, (
        f"population stddev≈{expected_population:.4f}; "
        f"sample stddev={sample_stddev:.4f} (wrong); got {result}"
    )


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fsd_rt_a": [(_NOW - 400, 20.0, True)],
            "fsd_rt_b": [(_NOW - 200, 80.0, True)],
        }
    )
    result = get_windowed_fleet_latency_stddev_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
