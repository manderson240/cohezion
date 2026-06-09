"""Item 1066: get_windowed_tool_latency_tail_ratio_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool tail ratio = p99 / p50.

Measures how much worse the worst tail is than the median.
0.0 for empty window or p50==0.0. Thin composition: p99/p50.
Injectable store. Pure function.

PRIMARY DISC.: lats [10,20,30,40,200] n=5
  p50=idx=0.5*4=2.0 -> 30.0 (exact)
  p99=idx=0.99*4=3.96 -> 40+0.96*(200-40)=40+153.6=193.6
  tail_ratio = 193.6/30.0 ≈ 6.4533
  (PRIMARY DISC.: kills p99/mean=193.6/60≈3.227 (mean biased by outlier);
   kills p95/p50=168.0/30.0=5.6 (smaller tail interval);
   correct p99/p50≈6.4533).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_tail_ratio_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_tail_ratio_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,20,30,40,200] -> tail_ratio=p99/p50=193.6/30≈6.4533.

    Kills p99/mean≈3.227 (mean is biased by outlier).
    Kills p95/p50=5.6 (different from p99-based).
    Correct: p99/p50≈6.4533.
    """
    _reset()
    store = _make_store({
        "tr_disc": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 200]],
    })
    result = get_windowed_tool_latency_tail_ratio_ms("tr_disc", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    expected = 193.6 / 30.0
    assert abs(result - expected) < 1e-9, (
        f"tail_ratio=193.6/30≈{expected:.4f}; kills p99/mean≈3.227; got {result}"
    )


def test_tail_ratio_equal_latencies_returns_one() -> None:
    """All equal -> p99=p50=constant -> tail_ratio=1.0."""
    _reset()
    store = _make_store({
        "tr_eq": [(_NOW - 10, 50.0, True)] * 6,
    })
    result = get_windowed_tool_latency_tail_ratio_ms("tr_eq", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"all-equal -> tail_ratio=1.0; got {result}"


def test_tail_ratio_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_tail_ratio_ms("no_such_tr", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "tr_old": [(_NOW - _WIN - 100, 50.0, True)] * 5,
    })
    assert get_windowed_tool_latency_tail_ratio_ms("tr_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_tail_ratio_non_negative() -> None:
    """tail_ratio >= 0 (p99 >= p50 always for positive latencies)."""
    _reset()
    store = _make_store({
        "tr_pos": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200, 500]],
    })
    result = get_windowed_tool_latency_tail_ratio_ms("tr_pos", _WIN, store=store, now_ms=_NOW)
    assert result >= 0.0, f"tail_ratio must be non-negative; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"tr_rt": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50, 100]]})
    assert isinstance(get_windowed_tool_latency_tail_ratio_ms("tr_rt", _WIN, store=store, now_ms=_NOW), float)
