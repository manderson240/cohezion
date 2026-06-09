"""Item 1094: get_windowed_fleet_latency_percentile_ms(window_ms, percentile, *, store=None, now_ms=None) -> float
-- fleet-wide p-th percentile latency (ms) using nearest-rank over ALL pooled windowed latencies.
0.0 for empty pool. Fleet dual of item 1093.

PRIMARY DISC.: tool_a lats=[10,90]ms, tool_b lats=[50,50,50]ms
  pooled sorted=[10,50,50,50,90], n=5, p80:
  ceil(0.8*5)=4, index=3, value=50ms
  (PRIMARY DISC.: kills per-tool-avg-percentile:
    tool_a p80: ceil(0.8*2)=2, index=1, value=90ms;
    tool_b p80: ceil(0.8*3)=3, index=2, value=50ms;
    avg=(90+50)/2=70ms != 50ms;
    pooled distribution is correct: 50ms).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fleet_latency_percentile_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_fleet_latency_percentile_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled p80=50ms kills per-tool-avg p80=70ms."""
    _reset()
    store = _make_store({
        "fpct_disc_a": [
            (_NOW - 500, 10.0, True),
            (_NOW - 300, 90.0, True),
        ],
        "fpct_disc_b": [
            (_NOW - 400, 50.0, True),
            (_NOW - 200, 50.0, True),
            (_NOW - 100, 50.0, True),
        ],
    })
    result = get_windowed_fleet_latency_percentile_ms(_WIN, 80.0, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    # pooled sorted=[10,50,50,50,90], p80: ceil(0.8*5)=4, index=3, value=50ms
    assert abs(result - 50.0) < 1e-9, (
        f"pooled p80=50ms; kills per-tool-avg=70ms; got {result}"
    )


def test_fleet_latency_percentile_p100_max_across_all_tools() -> None:
    """p100 always returns the global maximum across all tools."""
    _reset()
    store = _make_store({
        "fpct_max_a": [(_NOW - 500, 30.0, True), (_NOW - 400, 70.0, True)],
        "fpct_max_b": [(_NOW - 300, 200.0, True), (_NOW - 200, 10.0, True)],
    })
    result = get_windowed_fleet_latency_percentile_ms(_WIN, 100.0, store=store, now_ms=_NOW)
    assert abs(result - 200.0) < 1e-9, f"p100=global_max=200ms; got {result}"


def test_fleet_latency_percentile_single_tool_matches_per_tool() -> None:
    """Single tool -> fleet percentile equals per-tool percentile."""
    _reset()
    store = _make_store({
        "fpct_single": [
            (_NOW - 400, 10.0, True),
            (_NOW - 300, 50.0, True),
            (_NOW - 200, 90.0, True),
            (_NOW - 100, 100.0, True),
        ],
    })
    result = get_windowed_fleet_latency_percentile_ms(_WIN, 75.0, store=store, now_ms=_NOW)
    # sorted=[10,50,90,100], p75: ceil(0.75*4)=3, index=2, value=90ms
    assert abs(result - 90.0) < 1e-9, f"p75 single tool=90ms; got {result}"


def test_fleet_latency_percentile_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_fleet_latency_percentile_ms(_WIN, 95.0, store={}, now_ms=_NOW) == 0.0


def test_fleet_latency_percentile_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "fpct_old": [(_NOW - _WIN - 100, 50.0, True)] * 5,
    })
    assert get_windowed_fleet_latency_percentile_ms(_WIN, 50.0, store=store, now_ms=_NOW) == 0.0


def test_fleet_latency_percentile_p50_pooled() -> None:
    """p50 on pooled 6-value set."""
    _reset()
    # tool_a: [20, 40], tool_b: [10, 30, 50, 60]
    # pooled sorted: [10,20,30,40,50,60], n=6, p50: ceil(0.5*6)=3, index=2, value=30ms
    store = _make_store({
        "fpct_p50_a": [(_NOW - 500, 20.0, True), (_NOW - 400, 40.0, True)],
        "fpct_p50_b": [
            (_NOW - 300, 10.0, True),
            (_NOW - 200, 30.0, True),
            (_NOW - 100, 50.0, True),
            (_NOW - 50, 60.0, True),
        ],
    })
    result = get_windowed_fleet_latency_percentile_ms(_WIN, 50.0, store=store, now_ms=_NOW)
    assert abs(result - 30.0) < 1e-9, f"pooled p50=30ms; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "fpct_rt_a": [(_NOW - 500, 10.0, True)],
        "fpct_rt_b": [(_NOW - 300, 20.0, True)],
    })
    assert isinstance(get_windowed_fleet_latency_percentile_ms(_WIN, 50.0, store=store, now_ms=_NOW), float)
