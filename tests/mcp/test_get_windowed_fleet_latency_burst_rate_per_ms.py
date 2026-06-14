"""Item 1115: get_windowed_fleet_latency_burst_rate_per_ms(window_ms, burst_threshold_ms, *, store=None, now_ms=None) -> float
-- fleet-wide burst rate = fleet_burst_count / window_ms (bursts per ms).
0.0 for empty window or window_ms <= 0.

PRIMARY DISC.: window=1000ms, fleet_burst_count=4 -> rate=0.004
  (PRIMARY DISC.: kills burst_count=4 (unnormalized int);
   kills per-tool-sum-rate (tool_a 2/1000 + tool_b 2/1000 = 0.004 same here;
     use tool_a 3 bursts, tool_b 1 burst: fleet=4/1000=0.004,
     sum-per-tool = 3/1000 + 1/1000 = 0.004; still same -- use window=500 test
     to kill "span-based" rate; correct: fleet_count / window_ms).
  Window-dependency discriminator: same 4 bursts with window=2000ms -> rate=0.002.)
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_burst_rate_per_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0
_THR = 50.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_burst_rate_primary_discriminator() -> None:
    """PRIMARY DISC.: fleet_burst_count=4, window=1000ms -> rate=0.004."""
    _reset()
    store = _make_store(
        {
            "fbr_a": [
                (_NOW - 900, 80.0, True),  # burst 1
                (_NOW - 800, 10.0, True),  # exit
                (_NOW - 700, 80.0, True),  # burst 2
                (_NOW - 600, 10.0, True),  # exit
                (_NOW - 500, 80.0, True),  # burst 3
                (_NOW - 400, 10.0, True),  # exit
            ],
            "fbr_b": [
                (_NOW - 300, 80.0, True),  # burst 1
                (_NOW - 200, 10.0, True),  # exit
            ],
        }
    )
    result = get_windowed_fleet_latency_burst_rate_per_ms(_WIN, _THR, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 4.0 / _WIN) < 1e-12, (
        f"4 fleet bursts/1000ms=0.004; kills unnormalized=4; got {result}"
    )


def test_fleet_burst_rate_depends_on_window() -> None:
    """Same bursts, different window_ms -> different rate."""
    _reset()
    store = _make_store(
        {
            "fbr_w": [
                (_NOW - 200, 80.0, True),  # burst 1
                (_NOW - 150, 10.0, True),  # exit
                (_NOW - 100, 80.0, True),  # burst 2
                (_NOW - 50, 10.0, True),  # exit
            ],
        }
    )
    rate_1000 = get_windowed_fleet_latency_burst_rate_per_ms(1000.0, _THR, store=store, now_ms=_NOW)
    rate_2000 = get_windowed_fleet_latency_burst_rate_per_ms(2000.0, _THR, store=store, now_ms=_NOW)
    assert abs(rate_1000 - 2.0 / 1000.0) < 1e-12, f"2/1000=0.002; got {rate_1000}"
    assert abs(rate_2000 - 2.0 / 2000.0) < 1e-12, f"2/2000=0.001; got {rate_2000}"


def test_fleet_burst_rate_no_bursts_returns_zero() -> None:
    """No above-threshold calls -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fbr_none": [(_NOW - float(d), 10.0, True) for d in [300, 200, 100]],
        }
    )
    assert get_windowed_fleet_latency_burst_rate_per_ms(_WIN, _THR, store=store, now_ms=_NOW) == 0.0


def test_fleet_burst_rate_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_latency_burst_rate_per_ms(_WIN, _THR, store={}, now_ms=_NOW) == 0.0


def test_fleet_burst_rate_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "fbr_old": [(_NOW - _WIN - 100, 80.0, True)] * 3,
        }
    )
    assert get_windowed_fleet_latency_burst_rate_per_ms(_WIN, _THR, store=store, now_ms=_NOW) == 0.0


def test_fleet_burst_rate_zero_window_returns_zero() -> None:
    """window_ms=0 -> 0.0 (guard against division by zero)."""
    _reset()
    store = _make_store(
        {
            "fbr_zw": [(_NOW - 100, 80.0, True)],
        }
    )
    assert get_windowed_fleet_latency_burst_rate_per_ms(0.0, _THR, store=store, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "fbr_rt": [(_NOW - 500, 80.0, True), (_NOW - 400, 10.0, True)],
        }
    )
    result = get_windowed_fleet_latency_burst_rate_per_ms(_WIN, _THR, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 1.0 / _WIN) < 1e-12
