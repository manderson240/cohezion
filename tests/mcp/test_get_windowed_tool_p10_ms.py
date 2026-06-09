"""Item 1027: get_windowed_tool_p10_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- 10th percentile of latency_ms in window (linear interpolation).

p10 uses idx = 0.10 * (n-1) with linear interpolation between floor/ceil indices.
None for unknown/empty tool (consistent with other p-series thin delegates).

PRIMARY DISC.: lats [10, 20, 30, 40, 50] sorted
  idx = 0.10 * (5-1) = 0.4
  lo = sorted[0] = 10, hi = sorted[1] = 20, frac = 0.4
  p10 = 10 + 0.4*(20-10) = 14.0
  (kills min=10.0; kills p25=(10+0.25*4*(20-10))=17.5; correct=14.0 float).

NOTE: verified against numpy/scipy convention:
  np.percentile([10,20,30,40,50], 10, interpolation='linear') == 14.0
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_p10_ms,
    get_windowed_latency_percentile,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_p10_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,20,30,40,50] -> p10=14.0.

    Kills min=10.0 (off-by-fraction).
    Kills p25=17.5 (wrong percentile level).
    Correct: idx=0.4 -> 10 + 0.4*(20-10) = 14.0.
    """
    _reset()
    store = _make_store({
        "p10_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
    })
    result = get_windowed_tool_p10_ms("p10_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 14.0) < 1e-9, (
        f"p10=14.0; kills min=10 or p25=17.5; got {result}"
    )


def test_p10_delegates_to_percentile_function() -> None:
    """p10 must equal get_windowed_latency_percentile(tool, 10.0, ...)."""
    _reset()
    store = _make_store({
        "p10_del": [(_NOW - 10, float(v), True) for v in [100, 200, 300, 400, 500]],
    })
    p10 = get_windowed_tool_p10_ms("p10_del", _WIN, store=store, now_ms=_NOW)
    ref = get_windowed_latency_percentile("p10_del", 10.0, _WIN, store=store, now_ms=_NOW)
    assert p10 == ref, f"p10={p10} must equal percentile(10.0)={ref}"


def test_p10_single_call_returns_that_latency() -> None:
    """Single call -> p10 == that call's latency (trivial case, n=1)."""
    _reset()
    store = _make_store({
        "p10_one": [(_NOW - 10, 75.0, True)],
    })
    result = get_windowed_tool_p10_ms("p10_one", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 75.0) < 1e-9, f"single call -> p10=75.0; got {result}"


def test_p10_uniform_returns_min() -> None:
    """All equal latencies -> p10 == that value."""
    _reset()
    store = _make_store({
        "p10_eq": [(_NOW - 10, 50.0, True)] * 5,
    })
    result = get_windowed_tool_p10_ms("p10_eq", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 50.0) < 1e-9, f"all equal -> p10=50.0; got {result}"


def test_p10_lower_than_p25() -> None:
    """p10 <= p25 always (ordering invariant)."""
    _reset()
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_p25_ms
    store = _make_store({
        "p10_ord": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50, 60, 70, 80]],
    })
    p10 = get_windowed_tool_p10_ms("p10_ord", _WIN, store=store, now_ms=_NOW)
    p25 = get_windowed_tool_p25_ms("p10_ord", _WIN, store=store, now_ms=_NOW)
    assert p10 <= p25, f"p10={p10} must be <= p25={p25}"


def test_unknown_tool_returns_none_or_zero() -> None:
    """Unknown tool -> 0.0 (consistent with other p-series aliases)."""
    _reset()
    result = get_windowed_tool_p10_ms("no_such_p10", _WIN, store={}, now_ms=_NOW)
    # Thin delegate: returns same as get_windowed_latency_percentile for missing tool
    assert result == 0.0 or result is None, f"unknown tool should give 0.0 or None; got {result}"


def test_no_recent_calls_returns_zero_or_none() -> None:
    """All calls outside window -> 0.0 or None."""
    _reset()
    store = _make_store({
        "p10_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
    })
    result = get_windowed_tool_p10_ms("p10_old", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0 or result is None, f"no recent calls -> 0.0 or None; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"p10_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    result = get_windowed_tool_p10_ms("p10_rt", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
