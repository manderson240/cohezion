"""Item 1156: get_windowed_fleet_latency_below_threshold_rate(window_ms, threshold_ms,
              *, store=None, now_ms=None) -> float
-- fleet-wide fraction of calls with latency < threshold_ms (strict less-than).
Returns float in [0.0, 1.0]. 0.0 for empty window.

PRIMARY DISC.:
  pooled [10, 50, 100, 200], threshold=100ms
  below (<100): [10, 50] → rate=2/4=0.5
  kills above_fraction=1/4=0.25; kills total=1.0; kills always-0.
  At-boundary invariant: below_rate + above_fraction < 1.0 when any call is at threshold.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_below_threshold_rate,
    get_windowed_fleet_above_threshold_fraction,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_below_threshold_rate_primary_discriminator() -> None:
    """PRIMARY DISC.: below_rate=0.5; kills above_fraction=0.25; kills total=1.0."""
    _reset()
    store = _make_store({
        "fbtr_a": [(_NOW - 900, 10.0, True), (_NOW - 800, 100.0, True)],
        "fbtr_b": [(_NOW - 700, 50.0, True), (_NOW - 600, 200.0, True)],
    })
    result = get_windowed_fleet_latency_below_threshold_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 0.5) < 1e-9, (
        f"below_rate=0.5 ([10,50]<100 of [10,50,100,200]); kills above=0.25; got {result}"
    )


def test_fleet_below_rate_plus_above_fraction_less_than_one_at_boundary() -> None:
    """At-boundary: below_rate + above_fraction < 1.0 when a call is exactly at threshold."""
    _reset()
    store = _make_store({
        "fbtr_bnd_a": [(_NOW - 900, 10.0, True), (_NOW - 800, 100.0, True)],
        "fbtr_bnd_b": [(_NOW - 700, 50.0, True), (_NOW - 600, 200.0, True)],
    })
    below = get_windowed_fleet_latency_below_threshold_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    above = get_windowed_fleet_above_threshold_fraction(_WIN, 100.0, store=store, now_ms=_NOW)
    # 100ms call is at boundary — excluded from both <100 and >100
    assert below + above < 1.0, f"below({below})+above({above}) should < 1.0 with boundary call"
    assert abs(below + above - 0.75) < 1e-9, f"expected 0.75 (3/4), got {below+above}"


def test_fleet_below_threshold_rate_all_below() -> None:
    """All calls below threshold -> 1.0."""
    _reset()
    store = _make_store({
        "fbtr_all": [(_NOW - float(d), 5.0, True) for d in [900, 800, 700]],
    })
    result = get_windowed_fleet_latency_below_threshold_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"all below -> 1.0; got {result}"


def test_fleet_below_threshold_rate_all_above_returns_zero() -> None:
    """All calls above threshold -> 0.0."""
    _reset()
    store = _make_store({
        "fbtr_none": [(_NOW - float(d), 200.0, True) for d in [900, 800, 700]],
    })
    result = get_windowed_fleet_latency_below_threshold_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"all above -> 0.0; got {result}"


def test_fleet_below_threshold_rate_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_below_threshold_rate(_WIN, 100.0, store={}, now_ms=_NOW)
    assert abs(result) < 1e-9, f"empty -> 0.0; got {result}"


def test_fleet_below_threshold_rate_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "fbtr_old": [(_NOW - _WIN - float(d), 5.0, True) for d in [300, 200, 100]],
    })
    result = get_windowed_fleet_latency_below_threshold_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"outside window -> 0.0; got {result}"


def test_returns_float_type_and_range() -> None:
    """Return type is float in [0.0, 1.0]."""
    _reset()
    store = _make_store({
        "fbtr_rt": [(_NOW - 400, 30.0, True), (_NOW - 200, 200.0, True)],
    })
    result = get_windowed_fleet_latency_below_threshold_rate(_WIN, 100.0, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0
    assert abs(result - 0.5) < 1e-9  # only 30ms < 100ms
