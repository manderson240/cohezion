"""Item 1144: get_windowed_fleet_latency_winsorized_mean_ms(window_ms, winsor_frac=0.1, *, store=None, now_ms=None) -> float
-- fleet-wide Winsorized mean of pooled latencies (ms).
Clamp bottom winsor_frac and top winsor_frac fractions to their boundary values,
then compute mean of the clamped array. 0.0 for empty window. Returns float.

PRIMARY DISC. (Winsorize vs trim — they give different results):
  pooled sorted [1, 10, 20, 30, 100, 200], n=6, winsor_frac=0.2
  floor(6*0.2) = 1
  trimmed (removes 1 each end): [10, 20, 30, 100], mean=40ms
  winsorized (clamps 1 each end): [10, 10, 20, 30, 100, 100], mean=270/6=45ms
  (PRIMARY DISC.: kills trimmed_mean=40ms≠45ms;
   correct: clamp boundary values, keep n, divide by full n=45ms).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_winsorized_mean_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_winsorized_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: winsorized_mean=45ms (winsor_frac=0.2); kills trimmed_mean=40ms."""
    _reset()
    store = _make_store({
        "fwm_a": [
            (_NOW - 950, 1.0, True),
            (_NOW - 850, 10.0, True),
            (_NOW - 750, 20.0, True),
        ],
        "fwm_b": [
            (_NOW - 650, 30.0, True),
            (_NOW - 550, 100.0, True),
            (_NOW - 450, 200.0, True),
        ],
    })
    # pooled sorted [1,10,20,30,100,200], n=6, floor(6*0.2)=1
    # winsorized: [10,10,20,30,100,100], mean=270/6=45ms
    result = get_windowed_fleet_latency_winsorized_mean_ms(_WIN, 0.2, store=store, now_ms=_NOW)
    assert isinstance(result, float), f"expected float, got {type(result)}"
    assert abs(result - 45.0) < 1e-9, (
        f"winsorized_mean=45ms; kills trimmed_mean=40ms; got {result}"
    )


def test_fleet_winsorized_mean_no_winsorizing() -> None:
    """winsor_frac=0 (or floor(n*frac)=0): result equals full mean."""
    _reset()
    store = _make_store({
        "fwm_nw": [(_NOW - float(d), float(v), True)
                   for d, v in zip([700, 600, 500], [10, 20, 30])],
    })
    result = get_windowed_fleet_latency_winsorized_mean_ms(_WIN, 0.0, store=store, now_ms=_NOW)
    # mean of [10, 20, 30] = 20ms
    assert abs(result - 20.0) < 1e-9, f"no winsorizing -> full mean=20ms; got {result}"


def test_fleet_winsorized_mean_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    result = get_windowed_fleet_latency_winsorized_mean_ms(_WIN, store={}, now_ms=_NOW)
    assert result == 0.0


def test_fleet_winsorized_mean_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "fwm_old": [(_NOW - _WIN - float(d), float(d), True) for d in [300, 200, 100]],
    })
    result = get_windowed_fleet_latency_winsorized_mean_ms(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0


def test_fleet_winsorized_mean_all_same() -> None:
    """All same -> winsorized = original = same value."""
    _reset()
    store = _make_store({
        "fwm_flat": [(_NOW - float(d), 42.0, True) for d in [900, 800, 700, 600]],
    })
    result = get_windowed_fleet_latency_winsorized_mean_ms(_WIN, 0.25, store=store, now_ms=_NOW)
    assert abs(result - 42.0) < 1e-9, f"all same -> 42.0; got {result}"


def test_fleet_winsorized_mean_known_value() -> None:
    """Known value: [10, 50, 50, 90], winsor_frac=0.25, k=1; winsorized=[50,50,50,50], mean=50."""
    _reset()
    store = _make_store({
        "fwm_kv_a": [(_NOW - 700, 10.0, True), (_NOW - 600, 90.0, True)],
        "fwm_kv_b": [(_NOW - 500, 50.0, True), (_NOW - 400, 50.0, True)],
    })
    # sorted [10, 50, 50, 90], k=1; lo=50, hi=50; winsorized=[50,50,50,50], mean=50
    result = get_windowed_fleet_latency_winsorized_mean_ms(_WIN, 0.25, store=store, now_ms=_NOW)
    assert abs(result - 50.0) < 1e-9, f"expected 50ms; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fwm_rt": [(_NOW - float(d), float(v), True)
                   for d, v in zip([700, 600, 500, 400, 300], [1, 10, 20, 30, 100])],
    })
    result = get_windowed_fleet_latency_winsorized_mean_ms(_WIN, 0.2, store=store, now_ms=_NOW)
    assert isinstance(result, float)
