"""Item 1157: get_windowed_fleet_latency_at_threshold_count(window_ms, threshold_ms,
              *, store=None, now_ms=None) -> int
-- fleet-wide count of calls with latency exactly == threshold_ms.
Returns int. 0 for empty window or no exact matches.

PRIMARY DISC.:
  pooled [10, 50, 100, 200], threshold=100ms
  at-threshold: [100] → count=1
  kills below_count=2; kills above_count=1; kills total=4; kills always-0.
  Composition: below_count + at_count + above_count == total_count.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_at_threshold_count,
    get_windowed_fleet_latency_below_threshold_count,
    get_windowed_fleet_latency_above_threshold_count,
    get_windowed_fleet_latency_count,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_at_threshold_primary_discriminator() -> None:
    """PRIMARY DISC.: at_count=1; kills below=2, above=1, total=4, always-0."""
    _reset()
    store = _make_store(
        {
            "fatc_a": [(_NOW - 900, 10.0, True), (_NOW - 800, 100.0, True)],
            "fatc_b": [(_NOW - 700, 50.0, True), (_NOW - 600, 200.0, True)],
        }
    )
    result = get_windowed_fleet_latency_at_threshold_count(_WIN, 100.0, store=store, now_ms=_NOW)
    assert isinstance(result, int), f"expected int, got {type(result)}"
    assert result == 1, (
        f"at_count=1 ([100] of [10,50,100,200]); kills below=2/above=1/total=4; got {result}"
    )


def test_fleet_below_at_above_sum_to_total() -> None:
    """Composition: below_count + at_count + above_count == total_count."""
    _reset()
    store = _make_store(
        {
            "fatc_comp_a": [
                (_NOW - 900, 10.0, True),  # below
                (_NOW - 800, 100.0, True),  # at
                (_NOW - 700, 200.0, True),  # above
            ],
            "fatc_comp_b": [
                (_NOW - 600, 50.0, True),  # below
                (_NOW - 500, 100.0, True),  # at
            ],
        }
    )
    below = get_windowed_fleet_latency_below_threshold_count(_WIN, 100.0, store=store, now_ms=_NOW)
    at = get_windowed_fleet_latency_at_threshold_count(_WIN, 100.0, store=store, now_ms=_NOW)
    above = get_windowed_fleet_latency_above_threshold_count(_WIN, 100.0, store=store, now_ms=_NOW)
    total = get_windowed_fleet_latency_count(_WIN, store=store, now_ms=_NOW)
    assert below + at + above == total, (
        f"below({below})+at({at})+above({above})={below + at + above} != total({total})"
    )
    assert at == 2, f"expected 2 at-threshold calls; got {at}"


def test_fleet_at_threshold_multiple_matches() -> None:
    """Multiple calls exactly at threshold -> correct count."""
    _reset()
    store = _make_store(
        {
            "fatc_multi_a": [(_NOW - 900, 100.0, True), (_NOW - 800, 100.0, True)],
            "fatc_multi_b": [(_NOW - 700, 100.0, True), (_NOW - 600, 50.0, True)],
        }
    )
    result = get_windowed_fleet_latency_at_threshold_count(_WIN, 100.0, store=store, now_ms=_NOW)
    assert result == 3, f"3 calls at 100.0ms; got {result}"


def test_fleet_at_threshold_no_matches_returns_zero() -> None:
    """No calls exactly at threshold -> 0."""
    _reset()
    store = _make_store(
        {
            "fatc_none": [(_NOW - 900, 50.0, True), (_NOW - 800, 200.0, True)],
        }
    )
    result = get_windowed_fleet_latency_at_threshold_count(_WIN, 100.0, store=store, now_ms=_NOW)
    assert result == 0


def test_fleet_at_threshold_empty_store_returns_zero() -> None:
    """Empty store -> 0."""
    _reset()
    result = get_windowed_fleet_latency_at_threshold_count(_WIN, 100.0, store={}, now_ms=_NOW)
    assert result == 0
    assert isinstance(result, int)


def test_fleet_at_threshold_outside_window_returns_zero() -> None:
    """All calls outside window -> 0."""
    _reset()
    store = _make_store(
        {
            "fatc_old": [(_NOW - _WIN - float(d), 100.0, True) for d in [300, 200, 100]],
        }
    )
    result = get_windowed_fleet_latency_at_threshold_count(_WIN, 100.0, store=store, now_ms=_NOW)
    assert result == 0


def test_returns_int_type() -> None:
    """Return type is int."""
    _reset()
    store = _make_store(
        {
            "fatc_rt": [
                (_NOW - 400, 100.0, True),
                (_NOW - 300, 100.0, True),
                (_NOW - 200, 50.0, True),
            ],
        }
    )
    result = get_windowed_fleet_latency_at_threshold_count(_WIN, 100.0, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 2
