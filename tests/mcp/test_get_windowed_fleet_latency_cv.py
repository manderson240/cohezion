"""Item 1140: get_windowed_fleet_latency_cv(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide coefficient of variation (stddev / mean) of pooled latencies.
Returns float. 0.0 for empty window or zero mean.
Thin composition: stddev_ms / mean_ms.

PRIMARY DISC. (CV non-linearity — pooled ≠ per-tool-avg-of-CVs):
  Use the unequal-count fixture (tool_a=[10,20,30], tool_b=[100]) from item 1132:
  pooled [10,20,30,100], mean=40, stddev=sqrt((900+400+100+3600)/4)=sqrt(1250)≈35.355
  CV_pooled = 35.355/40 ≈ 0.8839
  per-tool CV_a: mean=20, stddev=sqrt((100+0+100)/3)=sqrt(200/3)≈8.165; CV_a=8.165/20≈0.408
  per-tool CV_b: single value → stddev=0 → CV_b=0
  per-tool-avg-CV = (0.408+0)/2 = 0.204 ≠ 0.884
  (PRIMARY DISC.: kills per-tool-avg-CV=0.204; correct: CV(pooled)≈0.884).
"""
from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_cv,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _pool_cv(lats: list[float]) -> float:
    n = len(lats)
    if n < 2:
        return 0.0
    mean = sum(lats) / n
    if mean == 0.0:
        return 0.0
    variance = sum((x - mean) ** 2 for x in lats) / n
    return (variance ** 0.5) / mean


def _reset():
    clear_telemetry_stores()


def test_fleet_cv_primary_discriminator() -> None:
    """PRIMARY DISC.: CV(pooled)≈0.884; kills per-tool-avg-CV=0.204."""
    _reset()
    store = _make_store({
        "fcv_a": [
            (_NOW - 900, 10.0, True),
            (_NOW - 800, 20.0, True),
            (_NOW - 700, 30.0, True),
        ],
        "fcv_b": [
            (_NOW - 600, 100.0, True),
        ],
    })
    # pooled [10, 20, 30, 100], mean=40
    expected = _pool_cv([10.0, 20.0, 30.0, 100.0])
    result = get_windowed_fleet_latency_cv(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - expected) < 1e-9, (
        f"CV(pooled)≈{expected:.6f}; kills per-tool-avg-CV≈0.204; got {result}"
    )
    # Extra: ensure it's not the per-tool-avg (a wrong implementation would return ~0.204)
    assert abs(result - 0.204) > 0.1, f"result looks like per-tool-avg-CV: {result}"


def test_fleet_cv_all_same_returns_zero() -> None:
    """All latencies equal -> stddev=0 -> CV=0.0."""
    _reset()
    store = _make_store({
        "fcv_flat_a": [(_NOW - float(d), 42.0, True) for d in [400, 300]],
        "fcv_flat_b": [(_NOW - float(d), 42.0, True) for d in [200, 100]],
    })
    result = get_windowed_fleet_latency_cv(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"all same -> 0.0; got {result}"


def test_fleet_cv_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_latency_cv(_WIN, store={}, now_ms=_NOW) == 0.0


def test_fleet_cv_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "fcv_old": [(_NOW - _WIN - float(d), float(d), True) for d in [300, 200, 100]],
    })
    assert get_windowed_fleet_latency_cv(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_cv_single_call_returns_zero() -> None:
    """Single call -> n<2 -> 0.0."""
    _reset()
    store = _make_store({
        "fcv_one": [(_NOW - 100, 55.0, True)],
    })
    result = get_windowed_fleet_latency_cv(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"single call -> 0.0; got {result}"


def test_fleet_cv_known_value() -> None:
    """Verify CV against a hand-computable fixture: [10, 90], mean=50, stddev=40, CV=0.8."""
    _reset()
    store = _make_store({
        "fcv_kv_a": [(_NOW - 700, 10.0, True)],
        "fcv_kv_b": [(_NOW - 600, 90.0, True)],
    })
    # mean=50, stddev=sqrt(((10-50)^2+(90-50)^2)/2)=sqrt((1600+1600)/2)=sqrt(1600)=40
    # CV = 40/50 = 0.8
    result = get_windowed_fleet_latency_cv(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 0.8) < 1e-9, f"expected CV=0.8; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fcv_rt_a": [(_NOW - 400, 20.0, True)],
        "fcv_rt_b": [(_NOW - 200, 80.0, True)],
    })
    result = get_windowed_fleet_latency_cv(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
