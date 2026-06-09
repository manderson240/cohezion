"""Item 1078: get_windowed_global_latency_ewma_ms(window_ms, alpha, *, store=None, now_ms=None) -> float
-- fleet-wide EWMA across ALL tool latencies ordered by timestamp.

Pools all (ts, lat) pairs from all tools, sorts by timestamp ascending,
applies EWMA with smoothing factor alpha.
0.0 for empty pool. Fleet dual of item 1077.

PRIMARY DISC.: tool_a at t1 (lat=10), tool_b at t2 (lat=50), tool_c at t3 (lat=20)
  pooled sorted by ts: [(t1,10),(t2,50),(t3,20)], alpha=0.5
  v0=10; v1=0.5*50+0.5*10=30.0; v2=0.5*20+0.5*30=25.0
  global EWMA=25.0
  (PRIMARY DISC.: kills per-tool EWMA avg: each tool is single-sample ->
   (EWMA(a)+EWMA(b)+EWMA(c))/3=(10+50+20)/3=26.67 != pooled 25.0;
   kills simple mean=26.67 (same coincidence -- different for other alpha values);
   correct global EWMA(alpha=0.5)=25.0).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_ewma_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_ewma_primary_discriminator() -> None:
    """PRIMARY DISC.: 3 tools each with 1 call at different ts, alpha=0.5 -> 25.0.

    Kills per-tool EWMA avg = 26.67 (single-sample tools, avg differs).
    Kills simple mean = 26.67.
    Correct: global EWMA(0.5) = 25.0.
    """
    _reset()
    store = _make_store({
        "gewma_a": [(_NOW - 300, 10.0, True)],  # oldest
        "gewma_b": [(_NOW - 200, 50.0, True)],
        "gewma_c": [(_NOW - 100, 20.0, True)],  # newest
    })
    result = get_windowed_global_latency_ewma_ms(_WIN, 0.5, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 25.0) < 1e-9, (
        f"global EWMA(0.5)=25.0; kills per-tool avg=26.67; got {result}"
    )


def test_global_ewma_alpha_one_returns_most_recent() -> None:
    """alpha=1.0 -> EWMA = most recently timestamped call across fleet."""
    _reset()
    store = _make_store({
        "gewma_a1_a": [(_NOW - 300, 100.0, True)],
        "gewma_a1_b": [(_NOW - 100, 20.0, True)],  # most recent
        "gewma_a1_c": [(_NOW - 200, 50.0, True)],
    })
    result = get_windowed_global_latency_ewma_ms(_WIN, 1.0, store=store, now_ms=_NOW)
    assert abs(result - 20.0) < 1e-9, f"alpha=1 -> most_recent=20.0; got {result}"


def test_global_ewma_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_ewma_ms(_WIN, 0.5, store={}, now_ms=_NOW) == 0.0


def test_global_ewma_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "gewma_old": [(_NOW - _WIN - 100, 50.0, True)] * 3,
    })
    assert get_windowed_global_latency_ewma_ms(_WIN, 0.5, store=store, now_ms=_NOW) == 0.0


def test_global_ewma_timestamp_ordering_matters() -> None:
    """Interleaved cross-tool timestamps: pooled ts-order EWMA != per-tool EWMA."""
    _reset()
    # Tool X has [100 (at t-400), 200 (at t-200)]
    # Tool Y has [10 (at t-300), 20 (at t-100)]
    # Pooled sorted: [(t-400,100), (t-300,10), (t-200,200), (t-100,20)]
    # EWMA(0.5): v0=100; v1=0.5*10+0.5*100=55; v2=0.5*200+0.5*55=127.5; v3=0.5*20+0.5*127.5=73.75
    store = _make_store({
        "gewma_ts_x": [(_NOW - 400, 100.0, True), (_NOW - 200, 200.0, True)],
        "gewma_ts_y": [(_NOW - 300, 10.0, True), (_NOW - 100, 20.0, True)],
    })
    result = get_windowed_global_latency_ewma_ms(_WIN, 0.5, store=store, now_ms=_NOW)
    assert abs(result - 73.75) < 1e-9, f"interleaved EWMA(0.5)=73.75; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gewma_rt": [(_NOW - 10, 50.0, True)] * 3})
    assert isinstance(get_windowed_global_latency_ewma_ms(_WIN, 0.5, store=store, now_ms=_NOW), float)
