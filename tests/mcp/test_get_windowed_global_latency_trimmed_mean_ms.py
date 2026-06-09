"""Item 1038: get_windowed_global_latency_trimmed_mean_ms(window_ms, trim_pct=0.1, *, store=None, now_ms=None) -> float
-- Fleet-wide trimmed (truncated) mean of pooled latency.

Pool ALL latencies across ALL tools, sort, discard floor(trim_pct*n) from
each tail, compute mean of remaining. 0.0 for empty or nothing left after
trimming. Default trim_pct=0.1. Fleet dual of item 1034.

PRIMARY DISC.: tool_a=[10,100] + tool_b=[20,30,40] trim_pct=0.2
  pooled sorted=[10,20,30,40,100], n=5, k=floor(0.2*5)=1
  keep [20,30,40] -> trimmed_mean=90/3=30.0
  (PRIMARY DISC.: kills full_mean=40.0;
   kills per-tool-then-avg: tool_a trim k=floor(0.2*2)=0→55.0, tool_b k=0→30.0 avg=42.5;
   correct pooled_trimmed_mean=30.0).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_trimmed_mean_ms,
    get_windowed_global_mean_latency_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_trimmed_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=[10,100]+tool_b=[20,30,40] trim=0.2 -> 30.0.

    Kills full_mean=40.0 (no trimming removes outlier 100).
    Kills per-tool-then-avg=42.5 (both have k=0 at n=2/n=3 with pct=0.2).
    Correct: pooled 5 values, k=1, keep [20,30,40], mean=30.0.
    """
    _reset()
    store = _make_store({
        "gt_a": [(_NOW - 10, float(v), True) for v in [10, 100]],
        "gt_b": [(_NOW - 10, float(v), True) for v in [20, 30, 40]],
    })
    result = get_windowed_global_latency_trimmed_mean_ms(_WIN, 0.2, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 30.0) < 1e-9, (
        f"pooled_trimmed=30.0; kills full_mean=40.0 + per-tool-avg=42.5; got {result}"
    )


def test_global_trim_zero_equals_full_mean() -> None:
    """trim_pct=0.0 -> trimmed mean == full mean (no data discarded)."""
    _reset()
    store = _make_store({
        "gt_z1": [(_NOW - 10, float(v), True) for v in [10, 50, 200]],
        "gt_z2": [(_NOW - 10, float(v), True) for v in [300, 400]],
    })
    trimmed = get_windowed_global_latency_trimmed_mean_ms(_WIN, 0.0, store=store, now_ms=_NOW)
    full = get_windowed_global_mean_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(trimmed - full) < 1e-9, f"trim=0: {trimmed} must equal full_mean={full}"


def test_single_tool_matches_pooled() -> None:
    """Single tool -> global trimmed mean equals per-tool trimmed mean."""
    _reset()
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_latency_trimmed_mean_ms
    lats = [10.0, 20.0, 30.0, 40.0, 100.0]
    store = _make_store({
        "gt_single": [(_NOW - 10, v, True) for v in lats],
    })
    global_tm = get_windowed_global_latency_trimmed_mean_ms(_WIN, 0.2, store=store, now_ms=_NOW)
    per_tool_tm = get_windowed_tool_latency_trimmed_mean_ms("gt_single", _WIN, 0.2, store=store, now_ms=_NOW)
    assert abs(global_tm - per_tool_tm) < 1e-9, (
        f"single-tool: global={global_tm} must equal per_tool={per_tool_tm}"
    )


def test_default_trim_pct_is_0_1() -> None:
    """Default trim_pct is 0.1."""
    _reset()
    store = _make_store({
        "gt_def": [(_NOW - 10, float(v), True) for v in range(10, 110, 10)],
    })
    default = get_windowed_global_latency_trimmed_mean_ms(_WIN, store=store, now_ms=_NOW)
    explicit = get_windowed_global_latency_trimmed_mean_ms(_WIN, 0.1, store=store, now_ms=_NOW)
    assert abs(default - explicit) < 1e-9, f"default==0.1: {default} vs {explicit}"


def test_trimming_reduces_outlier_influence() -> None:
    """Trimmed fleet mean < full fleet mean when outlier present."""
    _reset()
    store = _make_store({
        "gt_main": [(_NOW - 10, 10.0, True)] * 9,
        "gt_spike": [(_NOW - 10, 10000.0, True)],
    })
    trimmed = get_windowed_global_latency_trimmed_mean_ms(_WIN, 0.1, store=store, now_ms=_NOW)
    full = get_windowed_global_mean_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert trimmed < full, f"trimmed={trimmed} must be < full_mean={full}"


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_trimmed_mean_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_all_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "gt_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
    })
    assert get_windowed_global_latency_trimmed_mean_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gt_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    assert isinstance(
        get_windowed_global_latency_trimmed_mean_ms(_WIN, store=store, now_ms=_NOW), float
    )
