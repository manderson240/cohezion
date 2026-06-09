"""Item 1143: get_windowed_fleet_latency_trimmed_mean_ms(window_ms, trim_frac=0.1, *, store=None, now_ms=None) -> float
-- fleet-wide trimmed mean of pooled latencies (ms).
Discards the bottom trim_frac and top trim_frac fraction (floor(n*trim_frac) from each end).
0.0 for empty window or all-trimmed window. Returns float.

PRIMARY DISC. (trim-fraction discriminator):
  pooled sorted [1, 10, 20, 30, 100], n=5, trim_frac=0.2
  floor(5*0.2) = 1 trimmed from each end -> keep [10, 20, 30]
  trimmed_mean = (10+20+30)/3 = 20ms
  full mean = (1+10+20+30+100)/5 = 32.2ms
  (PRIMARY DISC.: kills untrimmed mean=32.2ms; correct=20ms).
"""
from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_trimmed_mean_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_trimmed_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: trimmed_mean=20ms (trim_frac=0.2); kills full mean=32.2ms."""
    _reset()
    store = _make_store({
        "ftm_a": [
            (_NOW - 900, 1.0, True),    # will be trimmed from bottom
            (_NOW - 800, 10.0, True),
            (_NOW - 700, 20.0, True),
        ],
        "ftm_b": [
            (_NOW - 600, 30.0, True),
            (_NOW - 500, 100.0, True),  # will be trimmed from top
        ],
    })
    # pooled sorted [1, 10, 20, 30, 100], n=5, floor(5*0.2)=1 each end -> [10,20,30]
    result = get_windowed_fleet_latency_trimmed_mean_ms(_WIN, 0.2, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 20.0) < 1e-9, (
        f"trimmed_mean=20ms; kills full_mean=32.2ms; got {result}"
    )


def test_fleet_trimmed_mean_default_frac() -> None:
    """Default trim_frac=0.1 trims nothing from n<10 (floor(n*0.1)=0)."""
    _reset()
    store = _make_store({
        "ftm_def_a": [(_NOW - 700, 10.0, True), (_NOW - 600, 20.0, True)],
        "ftm_def_b": [(_NOW - 500, 30.0, True), (_NOW - 400, 40.0, True)],
    })
    # n=4, floor(4*0.1)=0 trimmed -> mean of all 4 = 25ms
    result = get_windowed_fleet_latency_trimmed_mean_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 25.0) < 1e-9, f"default 10% trim, n=4 -> 0 trimmed, mean=25ms; got {result}"


def test_fleet_trimmed_mean_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_trimmed_mean_ms(_WIN, store={}, now_ms=_NOW)
    assert result == 0.0


def test_fleet_trimmed_mean_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "ftm_old": [(_NOW - _WIN - float(d), float(d), True) for d in [300, 200, 100]],
    })
    result = get_windowed_fleet_latency_trimmed_mean_ms(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0


def test_fleet_trimmed_mean_all_trimmed_returns_zero() -> None:
    """When trim removes all values (trim_frac=0.5 for n=2 -> floor(2*0.5)=1 each side -> 0 left) -> 0.0."""
    _reset()
    store = _make_store({
        "ftm_alltr": [(_NOW - 700, 10.0, True), (_NOW - 600, 90.0, True)],
    })
    # n=2, floor(2*0.5)=1 each end -> 0 values remaining -> 0.0
    result = get_windowed_fleet_latency_trimmed_mean_ms(_WIN, 0.5, store=store, now_ms=_NOW)
    assert result == 0.0, f"all trimmed -> 0.0; got {result}"


def test_fleet_trimmed_mean_symmetric() -> None:
    """Symmetric distribution: trimmed mean == untrimmed mean."""
    _reset()
    # [10, 20, 30, 40, 50] mean=30, trim_frac=0.2 removes 1 each end -> [20,30,40] mean=30
    store = _make_store({
        "ftm_sym": [(_NOW - float(d), float(v), True)
                    for d, v in zip([900, 800, 700, 600, 500], [10, 20, 30, 40, 50])],
    })
    result = get_windowed_fleet_latency_trimmed_mean_ms(_WIN, 0.2, store=store, now_ms=_NOW)
    assert abs(result - 30.0) < 1e-9, f"symmetric -> trimmed=untrimmed=30ms; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "ftm_rt": [(_NOW - float(d), float(v), True)
                   for d, v in zip([900, 800, 700, 600, 500], [10, 20, 30, 40, 50])],
    })
    result = get_windowed_fleet_latency_trimmed_mean_ms(_WIN, 0.2, store=store, now_ms=_NOW)
    assert isinstance(result, float)
