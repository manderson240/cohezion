"""Item 1149: get_windowed_fleet_latency_below_threshold_count(window_ms, threshold_ms, *, store=None, now_ms=None) -> int
-- fleet-wide count of calls with latency < threshold_ms in the window.
Returns int. 0 for empty or all-above window.

PRIMARY DISC. (below-threshold discriminator):
  pooled [10, 50, 200, 300], threshold=100ms
  below-threshold: lat < 100 → [10, 50] → count=2
  above-threshold: lat > 100 → [200, 300] → count=2
  sum=4 (symmetric split verifies dual symmetry with above)
  (PRIMARY DISC.: kills always-0; kills count-all=4; correct: count lat<threshold, return int=2).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_below_threshold_count,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_below_threshold_primary_discriminator() -> None:
    """PRIMARY DISC.: below-threshold=2 for [10,50,200,300] threshold=100ms."""
    _reset()
    store = _make_store({
        "fbtc_a": [(_NOW - 900, 10.0, True), (_NOW - 800, 200.0, True)],
        "fbtc_b": [(_NOW - 700, 50.0, True), (_NOW - 600, 300.0, True)],
    })
    result = get_windowed_fleet_latency_below_threshold_count(_WIN, 100.0, store=store, now_ms=_NOW)
    assert isinstance(result, int), f"expected int, got {type(result)}"
    assert result == 2, (
        f"below-threshold=2 for [10,50,200,300] threshold=100ms; got {result}"
    )


def test_fleet_below_threshold_all_below() -> None:
    """All calls below threshold -> count = total calls."""
    _reset()
    store = _make_store({
        "fbtc_all": [(_NOW - float(d), 5.0, True) for d in [900, 800, 700, 600]],
    })
    result = get_windowed_fleet_latency_below_threshold_count(_WIN, 100.0, store=store, now_ms=_NOW)
    assert result == 4, f"all below -> 4; got {result}"


def test_fleet_below_threshold_all_above_returns_zero() -> None:
    """All calls above threshold -> 0."""
    _reset()
    store = _make_store({
        "fbtc_none": [(_NOW - float(d), 200.0, True) for d in [900, 800, 700]],
    })
    result = get_windowed_fleet_latency_below_threshold_count(_WIN, 100.0, store=store, now_ms=_NOW)
    assert result == 0


def test_fleet_below_threshold_empty_store_returns_zero() -> None:
    """Empty store -> 0."""
    _reset()
    result = get_windowed_fleet_latency_below_threshold_count(_WIN, 100.0, store={}, now_ms=_NOW)
    assert result == 0
    assert isinstance(result, int)


def test_fleet_below_threshold_outside_window_returns_zero() -> None:
    """All calls outside window -> 0."""
    _reset()
    store = _make_store({
        "fbtc_old": [(_NOW - _WIN - float(d), 5.0, True) for d in [300, 200, 100]],
    })
    result = get_windowed_fleet_latency_below_threshold_count(_WIN, 100.0, store=store, now_ms=_NOW)
    assert result == 0


def test_fleet_below_above_sum_to_total() -> None:
    """below_count + above_count == total_count (for strict inequalities, threshold-exact excluded)."""
    _reset()
    from cohezion.mcp.compound_mcp_telemetry import (
        get_windowed_fleet_latency_above_threshold_count,
        get_windowed_fleet_latency_count,
    )
    store = _make_store({
        "fbtc_sym_a": [(_NOW - 900, 10.0, True), (_NOW - 800, 200.0, True)],
        "fbtc_sym_b": [(_NOW - 700, 50.0, True), (_NOW - 600, 300.0, True)],
    })
    below = get_windowed_fleet_latency_below_threshold_count(_WIN, 100.0, store=store, now_ms=_NOW)
    above = get_windowed_fleet_latency_above_threshold_count(_WIN, 100.0, store=store, now_ms=_NOW)
    total = get_windowed_fleet_latency_count(_WIN, store=store, now_ms=_NOW)
    # No values exactly at threshold=100 → below+above == total
    assert below + above == total, f"below({below})+above({above}) != total({total})"


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    store = _make_store({
        "fbtc_rt": [(_NOW - 400, 30.0, True), (_NOW - 200, 70.0, True)],
    })
    result = get_windowed_fleet_latency_below_threshold_count(_WIN, 50.0, store=store, now_ms=_NOW)
    assert isinstance(result, int), f"expected int, got {type(result).__name__}"
    assert result == 1  # only 30ms < 50ms
