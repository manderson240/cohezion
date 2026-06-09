"""Item 1129: get_windowed_fleet_latency_variance_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide population variance of pooled latencies (ms²).
0.0 for empty window or single call. Returns float.

PRIMARY DISC. (unequal-counts pooling):
  tool_a lats=[10,20,30] (n=3), tool_b lat=[100] (n=1)
  per-tool-avg: tool_a var≈66.67, tool_b var=0 (single call), avg≈33.33ms²
  pooled [10,20,30,100] mean=40: variance=(900+400+100+3600)/4=1250ms²
  (PRIMARY DISC.: kills per-tool-avg=33.33ms²≠1250ms²;
   correct: pool all latencies, population variance divides by n, return float=1250).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_variance_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_variance_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled variance=1250ms²; kills per-tool-avg≈33.33ms²."""
    _reset()
    store = _make_store({
        "fv_a": [
            (_NOW - 900, 10.0, True),
            (_NOW - 800, 20.0, True),
            (_NOW - 700, 30.0, True),
        ],
        "fv_b": [
            (_NOW - 600, 100.0, True),
        ],
    })
    # pooled [10, 20, 30, 100], mean=40
    # variance = ((30²+20²+10²+60²)/4) = (900+400+100+3600)/4 = 5000/4 = 1250ms²
    result = get_windowed_fleet_latency_variance_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 1250.0) < 1e-6, (
        f"pooled variance=1250ms²; kills per-tool-avg≈33.33ms²; got {result}"
    )


def test_fleet_variance_all_same_returns_zero() -> None:
    """All latencies equal -> variance = 0.0."""
    _reset()
    store = _make_store({
        "fv_flat_a": [(_NOW - float(d), 42.0, True) for d in [400, 300]],
        "fv_flat_b": [(_NOW - float(d), 42.0, True) for d in [200, 100]],
    })
    result = get_windowed_fleet_latency_variance_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"all same -> 0.0; got {result}"


def test_fleet_variance_single_call_returns_zero() -> None:
    """Only one call -> 0.0 (population variance of a single value is 0)."""
    _reset()
    store = _make_store({
        "fv_one": [(_NOW - 100, 55.0, True)],
    })
    result = get_windowed_fleet_latency_variance_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"single call -> 0.0; got {result}"


def test_fleet_variance_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_latency_variance_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_fleet_variance_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "fv_old": [(_NOW - _WIN - float(d), float(d), True) for d in [300, 200, 100]],
    })
    assert get_windowed_fleet_latency_variance_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_variance_is_stddev_squared() -> None:
    """variance == stddev²; consistent with item-1128 get_windowed_fleet_latency_stddev_ms."""
    _reset()
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_fleet_latency_stddev_ms
    store = _make_store({
        "fv_sq_a": [(_NOW - 700, 10.0, True), (_NOW - 600, 90.0, True)],
        "fv_sq_b": [(_NOW - 500, 50.0, True), (_NOW - 400, 50.0, True)],
    })
    # pooled [10,50,50,90]: stddev=sqrt(800)≈28.28, variance=800
    var_result = get_windowed_fleet_latency_variance_ms(_WIN, store=store, now_ms=_NOW)
    std_result = get_windowed_fleet_latency_stddev_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(var_result - std_result ** 2) < 1e-6, (
        f"variance({var_result}) != stddev²({std_result**2:.4f})"
    )


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fv_rt_a": [(_NOW - 400, 20.0, True)],
        "fv_rt_b": [(_NOW - 200, 80.0, True)],
    })
    result = get_windowed_fleet_latency_variance_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
