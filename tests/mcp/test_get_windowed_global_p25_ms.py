"""Item 1011: get_windowed_global_p25_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide 25th-percentile latency in window.

Named convenience alias for get_windowed_global_latency_percentile(25.0, window_ms, ...).
Pools ALL tool latencies. 0.0 for empty store. Injectable store. Pure function.
Completes the global p25/p50/p75/p95/p99 quintet.

PRIMARY DISC.: tool_a [50,100] + tool_b [200,400] pooled sorted [50,100,200,400] (n=4)
  idx = 25/100 * (4-1) = 0.75
  floor=0 -> sorted[0]=50, ceil=1 -> sorted[1]=100
  interpolated = 50 + 0.75*(100-50) = 87.5
  (kills floor=50.0; kills ceil=100.0; correct pooled=87.5).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_p25_ms,
    get_windowed_global_latency_percentile,
    get_windowed_tool_p25_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_p25_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a[50,100] + tool_b[200,400] pooled -> 87.5.

    Pooled sorted [50,100,200,400] (n=4), idx=0.75 -> 50+0.75*50=87.5.
    Kills floor=50.0.
    Kills ceil=100.0.
    Kills per-tool-average approach.
    """
    _reset()
    store = _make_store({
        "gp25_a": [(_NOW - 10, float(v), True) for v in [50, 100]],
        "gp25_b": [(_NOW - 10, float(v), True) for v in [200, 400]],
    })
    result = get_windowed_global_p25_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 87.5) < 1e-9, (
        f"pooled [50,100,200,400] p25=87.5; kills floor=50 or ceil=100; got {result}"
    )


def test_global_p25_equals_generic_global_percentile() -> None:
    """global_p25 == get_windowed_global_latency_percentile(25.0, window, ...)."""
    _reset()
    store = _make_store({
        "gp25_eq_a": [(_NOW - 10, float(v), True) for v in [10, 30, 60]],
        "gp25_eq_b": [(_NOW - 10, float(v), True) for v in [90, 150, 300]],
    })
    p25 = get_windowed_global_p25_ms(_WIN, store=store, now_ms=_NOW)
    generic = get_windowed_global_latency_percentile(25.0, _WIN, store=store, now_ms=_NOW)
    assert abs(p25 - generic) < 1e-9, (
        f"global_p25={p25} must equal generic global percentile={generic}"
    )


def test_single_tool_matches_per_tool_p25() -> None:
    """With one tool, global p25 == per-tool p25."""
    _reset()
    store = _make_store({
        "gp25_one": [(_NOW - 10, float(v), True) for v in [10, 20, 50, 100, 200]],
    })
    global_p25 = get_windowed_global_p25_ms(_WIN, store=store, now_ms=_NOW)
    per_tool_p25 = get_windowed_tool_p25_ms("gp25_one", _WIN, store=store, now_ms=_NOW)
    assert abs(global_p25 - per_tool_p25) < 1e-9, (
        f"single tool: global={global_p25} must equal per_tool={per_tool_p25}"
    )


def test_empty_store_returns_zero() -> None:
    _reset()
    assert get_windowed_global_p25_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "gp25_old": [(_NOW - _WIN - 100, 9999.0, True)] * 5,
    })
    assert get_windowed_global_p25_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_global_p25_le_global_p75() -> None:
    """global p25 <= global p75 for any non-empty window."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_global_p75_ms
    _reset()
    store = _make_store({
        "gp25_ord_a": [(_NOW - 10, float(v), True) for v in [10, 30, 70]],
        "gp25_ord_b": [(_NOW - 10, float(v), True) for v in [90, 150]],
    })
    p25 = get_windowed_global_p25_ms(_WIN, store=store, now_ms=_NOW)
    p75 = get_windowed_global_p75_ms(_WIN, store=store, now_ms=_NOW)
    assert p25 <= p75, f"global p25={p25} must be <= global p75={p75}"


def test_global_iqr_from_p75_minus_p25() -> None:
    """global IQR = global_p75 - global_p25 matches get_windowed_global_latency_iqr_ms."""
    from cohezion.mcp.compound_mcp_telemetry import (
        get_windowed_global_p75_ms,
        get_windowed_global_latency_iqr_ms,
    )
    _reset()
    store = _make_store({
        "gp25_iqr_a": [(_NOW - 10, float(v), True) for v in [10, 50, 200]],
        "gp25_iqr_b": [(_NOW - 10, float(v), True) for v in [300, 500, 1000]],
    })
    p25 = get_windowed_global_p25_ms(_WIN, store=store, now_ms=_NOW)
    p75 = get_windowed_global_p75_ms(_WIN, store=store, now_ms=_NOW)
    iqr = get_windowed_global_latency_iqr_ms(_WIN, store=store, now_ms=_NOW)
    assert abs((p75 - p25) - iqr) < 1e-9, (
        f"global p75-p25={p75-p25} must equal global iqr={iqr}"
    )


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gp25_rt": [(_NOW - 10, float(v), True) for v in [50, 100, 200]]})
    assert isinstance(get_windowed_global_p25_ms(_WIN, store=store, now_ms=_NOW), float)
