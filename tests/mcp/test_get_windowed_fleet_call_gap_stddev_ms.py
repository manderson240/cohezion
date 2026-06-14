"""Item 1121: get_windowed_fleet_call_gap_stddev_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide population stddev of consecutive call-arrival gaps treating all tools as one stream.
0.0 for <3 fleet calls. Returns float.

PRIMARY DISC. (two-tool interleaved): fleet sorted gaps=[100,100,200,200]ms -> stddev=50ms
  (PRIMARY DISC.: kills per-tool-then-avg = (0+50)/2=25ms;
   kills max_gap=200ms; kills mean_gap=150ms;
   correct: pool all timestamps chronologically, compute population stddev of gaps=50ms).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_call_gap_stddev_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_gap_stddev_primary_discriminator() -> None:
    """PRIMARY DISC.: fleet gaps=[100,100,200,200] -> pop_stddev=50ms != per-tool-avg=25ms."""
    _reset()
    store = _make_store(
        {
            "fgs_a": [
                (_NOW - 700, 10.0, True),
                (_NOW - 500, 10.0, True),
            ],
            "fgs_b": [
                (_NOW - 600, 10.0, True),
                (_NOW - 300, 10.0, True),
                (_NOW - 100, 10.0, True),
            ],
        }
    )
    # fleet sorted: [700,600,500,300,100] -> gaps=[100,100,200,200]
    # mean=150, var=2500, stddev=50
    result = get_windowed_fleet_call_gap_stddev_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 50.0) < 1e-9, (
        f"fleet gaps=[100,100,200,200] -> pop_stddev=50ms; kills per-tool-avg=25ms; got {result}"
    )


def test_fleet_gap_stddev_uniform_gaps_returns_zero() -> None:
    """All fleet gaps equal -> stddev=0.0."""
    _reset()
    store = _make_store(
        {
            "fgs_unif_a": [(_NOW - 600, 10.0, True), (_NOW - 400, 10.0, True)],
            "fgs_unif_b": [(_NOW - 200, 10.0, True)],
        }
    )
    # sorted=[600,400,200] -> gaps=[200,200] -> stddev=0
    result = get_windowed_fleet_call_gap_stddev_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"uniform gaps -> 0.0; got {result}"


def test_fleet_gap_stddev_fewer_than_three_calls_returns_zero() -> None:
    """Fewer than 3 fleet calls -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fgs_two": [(_NOW - 500, 10.0, True), (_NOW - 200, 10.0, True)],
        }
    )
    assert get_windowed_fleet_call_gap_stddev_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_gap_stddev_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_call_gap_stddev_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_fleet_gap_stddev_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fgs_old": [(_NOW - _WIN - float(d), 10.0, True) for d in [300, 200, 100]],
        }
    )
    assert get_windowed_fleet_call_gap_stddev_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_fleet_gap_stddev_known_case() -> None:
    """3 fleet calls, gaps=[100,300]ms -> pop_stddev=100ms."""
    _reset()
    store = _make_store(
        {
            "fgs_k_a": [(_NOW - 500, 10.0, True)],
            "fgs_k_b": [(_NOW - 400, 10.0, True), (_NOW - 100, 10.0, True)],
        }
    )
    # sorted=[500,400,100] -> gaps=[100,300]; mean=200; deviations=[-100,100]; var=10000; std=100
    result = get_windowed_fleet_call_gap_stddev_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 100.0) < 1e-9, f"pop_stddev=100ms; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fgs_rt_a": [(_NOW - 600, 10.0, True), (_NOW - 400, 10.0, True)],
            "fgs_rt_b": [(_NOW - 200, 10.0, True)],
        }
    )
    assert isinstance(get_windowed_fleet_call_gap_stddev_ms(_WIN, store=store, now_ms=_NOW), float)
