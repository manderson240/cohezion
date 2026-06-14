"""Item 1117: get_windowed_fleet_latency_above_threshold_count(window_ms, threshold_ms, *, store=None, now_ms=None) -> int
-- fleet-wide int count of calls with latency strictly > threshold_ms across ALL tools.
Returns int. 0 for empty window.

PRIMARY DISC. (three-tool): tool_a 1 above, tool_b 2 above, tool_c 0 above -> fleet_total=3
  (PRIMARY DISC.: kills per-tool-max=2 (max not sum);
   kills per-tool-first=1 (first tool only);
   kills float_fraction=3/9=0.333 (count not fraction);
   correct: pool all records, count lat>threshold, return int=3).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_above_threshold_count,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_above_threshold_count_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled 3 calls above threshold; kills max=2, first=1, fraction=0.333."""
    _reset()
    store = _make_store(
        {
            "fatc_a": [
                (_NOW - 800, 10.0, True),  # below threshold
                (_NOW - 700, 60.0, True),  # ABOVE threshold
                (_NOW - 600, 40.0, True),  # below threshold
            ],  # tool_a: 1 above
            "fatc_b": [
                (_NOW - 500, 20.0, True),  # below threshold
                (_NOW - 400, 70.0, True),  # ABOVE threshold
                (_NOW - 300, 80.0, True),  # ABOVE threshold
                (_NOW - 200, 30.0, True),  # below threshold
            ],  # tool_b: 2 above
            "fatc_c": [
                (_NOW - 150, 50.0, True),  # exactly threshold: NOT above (strict >)
                (_NOW - 100, 40.0, True),  # below threshold
            ],  # tool_c: 0 above
        }
    )
    result = get_windowed_fleet_latency_above_threshold_count(_WIN, 50.0, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 3, (
        f"1+2+0=3 above threshold; kills max=2; kills first=1; kills fraction=0.333; got {result}"
    )


def test_fleet_above_threshold_count_strict_greater_than() -> None:
    """Exactly at threshold is NOT counted (strict >)."""
    _reset()
    store = _make_store(
        {
            "fatc_exact": [
                (_NOW - 300, 50.0, True),  # == threshold, NOT counted
                (_NOW - 200, 51.0, True),  # > threshold, counted
                (_NOW - 100, 49.0, True),  # < threshold, NOT counted
            ],
        }
    )
    result = get_windowed_fleet_latency_above_threshold_count(_WIN, 50.0, store=store, now_ms=_NOW)
    assert result == 1, f"only lat=51 counted; got {result}"


def test_fleet_above_threshold_count_all_above() -> None:
    """All calls above threshold -> count = total."""
    _reset()
    store = _make_store(
        {
            "fatc_all_a": [(_NOW - float(d), 100.0, True) for d in [300, 200]],
            "fatc_all_b": [(_NOW - float(d), 100.0, True) for d in [150, 100, 50]],
        }
    )
    assert (
        get_windowed_fleet_latency_above_threshold_count(_WIN, 50.0, store=store, now_ms=_NOW) == 5
    )


def test_fleet_above_threshold_count_none_above() -> None:
    """All calls at or below threshold -> 0."""
    _reset()
    store = _make_store(
        {
            "fatc_none": [(_NOW - float(d), 30.0, True) for d in [300, 200, 100]],
        }
    )
    assert (
        get_windowed_fleet_latency_above_threshold_count(_WIN, 50.0, store=store, now_ms=_NOW) == 0
    )


def test_fleet_above_threshold_count_empty_store_returns_zero() -> None:
    """Empty store -> 0."""
    _reset()
    assert get_windowed_fleet_latency_above_threshold_count(_WIN, 50.0, store={}, now_ms=_NOW) == 0


def test_fleet_above_threshold_count_outside_window_returns_zero() -> None:
    """All calls outside window -> 0."""
    _reset()
    store = _make_store(
        {
            "fatc_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
        }
    )
    assert (
        get_windowed_fleet_latency_above_threshold_count(_WIN, 50.0, store=store, now_ms=_NOW) == 0
    )


def test_returns_int_type() -> None:
    """Return type is int, not float."""
    _reset()
    store = _make_store(
        {
            "fatc_rt": [(_NOW - 200, 80.0, True), (_NOW - 100, 10.0, True)],
        }
    )
    result = get_windowed_fleet_latency_above_threshold_count(_WIN, 50.0, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 1
