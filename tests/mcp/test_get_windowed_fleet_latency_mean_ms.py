"""Item 1141: get_windowed_fleet_latency_mean_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide arithmetic mean of pooled latencies (ms).
0.0 for empty window. Returns float.

PRIMARY DISC. (fleet-pooling vs per-tool-avg of means):
  tool_a lats=[10,20,30] (mean=20ms), tool_b lats=[40,60] (mean=50ms)
  per-tool-avg-mean = (20+50)/2 = 35ms
  fleet_mean = (10+20+30+40+60)/5 = 160/5 = 32ms
  (PRIMARY DISC.: kills per-tool-avg=35ms≠32ms;
   correct: sum_all / count_all, return float=32ms).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_mean_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: fleet_mean=32ms; kills per-tool-avg-mean=35ms."""
    _reset()
    store = _make_store({
        "fmn_a": [
            (_NOW - 900, 10.0, True),
            (_NOW - 800, 20.0, True),
            (_NOW - 700, 30.0, True),
        ],
        "fmn_b": [
            (_NOW - 600, 40.0, True),
            (_NOW - 500, 60.0, True),
        ],
    })
    # pooled [10,20,30,40,60]: mean = 160/5 = 32ms
    result = get_windowed_fleet_latency_mean_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 32.0) < 1e-9, (
        f"fleet_mean=32ms; kills per-tool-avg=35ms; got {result}"
    )


def test_fleet_mean_single_tool() -> None:
    """Single-tool fleet mean equals that tool's mean."""
    _reset()
    store = _make_store({
        "fmn_one": [
            (_NOW - 700, 10.0, True),
            (_NOW - 600, 20.0, True),
            (_NOW - 500, 30.0, True),
        ],
    })
    result = get_windowed_fleet_latency_mean_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 20.0) < 1e-9, f"expected 20ms; got {result}"


def test_fleet_mean_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_mean_ms(_WIN, store={}, now_ms=_NOW)
    assert result == 0.0
    assert isinstance(result, float)


def test_fleet_mean_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "fmn_old": [(_NOW - _WIN - float(d), float(d), True) for d in [300, 200, 100]],
    })
    result = get_windowed_fleet_latency_mean_ms(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0


def test_fleet_mean_single_call() -> None:
    """Single call -> mean = that latency."""
    _reset()
    store = _make_store({
        "fmn_sc": [(_NOW - 100, 55.0, True)],
    })
    result = get_windowed_fleet_latency_mean_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 55.0) < 1e-9, f"single call -> mean=55.0; got {result}"


def test_fleet_mean_consistent_with_sum_and_count() -> None:
    """mean == sum / count (consistency with sum and count functions)."""
    _reset()
    from cohezion.mcp.compound_mcp_telemetry import (
        get_windowed_fleet_latency_sum_ms,
        get_windowed_fleet_latency_count,
    )
    store = _make_store({
        "fmn_cons_a": [(_NOW - float(d), float(10 * (i + 1)), True)
                       for i, d in enumerate([900, 800, 700])],
        "fmn_cons_b": [(_NOW - float(d), float(10 * (i + 4)), True)
                       for i, d in enumerate([600, 500])],
    })
    mean = get_windowed_fleet_latency_mean_ms(_WIN, store=store, now_ms=_NOW)
    s = get_windowed_fleet_latency_sum_ms(_WIN, store=store, now_ms=_NOW)
    c = get_windowed_fleet_latency_count(_WIN, store=store, now_ms=_NOW)
    assert c > 0
    assert abs(mean - s / c) < 1e-9, f"mean={mean} != sum/count={s/c}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fmn_rt_a": [(_NOW - 400, 30.0, True)],
        "fmn_rt_b": [(_NOW - 200, 70.0, True)],
    })
    result = get_windowed_fleet_latency_mean_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 50.0) < 1e-9
