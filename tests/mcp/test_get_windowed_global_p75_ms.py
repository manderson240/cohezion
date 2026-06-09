"""Item 1009: get_windowed_global_p75_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide 75th-percentile latency in window.

Named convenience alias for get_windowed_global_latency_percentile(75.0, window_ms, ...).
Pools ALL tool latencies. 0.0 for empty store. Injectable store. Pure function.

PRIMARY DISC.: tool_a [50,100] + tool_b [200,400] pooled sorted [50,100,200,400] (n=4)
  idx = 75/100 * (4-1) = 2.25
  floor=2 -> sorted[2]=200, ceil=3 -> sorted[3]=400
  interpolated = 200 + 0.25*(400-200) = 250.0
  (kills per-tool-avg-of-p75s: p75_a=(50+0.75*50=87.5), p75_b=(200+0.75*200=350); avg=218.75)
  (correct pooled=250.0 != avg-of-per-tool=218.75).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_p75_ms,
    get_windowed_global_latency_percentile,
    get_windowed_tool_p75_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_p75_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a[50,100] + tool_b[200,400] pooled -> 250.0.

    Pooled sorted [50,100,200,400] (n=4), idx=2.25 -> 200+0.25*200=250.0.
    Kills per-tool-average approach.
    Kills floor=200.0 without interpolation.
    """
    _reset()
    store = _make_store({
        "gp75_a": [(_NOW - 10, float(v), True) for v in [50, 100]],
        "gp75_b": [(_NOW - 10, float(v), True) for v in [200, 400]],
    })
    result = get_windowed_global_p75_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 250.0) < 1e-9, (
        f"pooled [50,100,200,400] p75=250.0; kills avg-per-tool or floor=200; got {result}"
    )


def test_global_p75_equals_generic_global_percentile() -> None:
    """global_p75 == get_windowed_global_latency_percentile(75.0, window, ...)."""
    _reset()
    store = _make_store({
        "gp75_eq_a": [(_NOW - 10, float(v), True) for v in [10, 30, 60]],
        "gp75_eq_b": [(_NOW - 10, float(v), True) for v in [90, 150, 300]],
    })
    p75 = get_windowed_global_p75_ms(_WIN, store=store, now_ms=_NOW)
    generic = get_windowed_global_latency_percentile(75.0, _WIN, store=store, now_ms=_NOW)
    assert abs(p75 - generic) < 1e-9, (
        f"global_p75={p75} must equal generic global percentile={generic}"
    )


def test_single_tool_matches_per_tool_p75() -> None:
    """With one tool, global p75 == per-tool p75."""
    _reset()
    store = _make_store({
        "gp75_one": [(_NOW - 10, float(v), True) for v in [10, 20, 50, 100, 200]],
    })
    global_p75 = get_windowed_global_p75_ms(_WIN, store=store, now_ms=_NOW)
    per_tool_p75 = get_windowed_tool_p75_ms("gp75_one", _WIN, store=store, now_ms=_NOW)
    assert abs(global_p75 - per_tool_p75) < 1e-9, (
        f"single tool: global={global_p75} must equal per_tool={per_tool_p75}"
    )


def test_empty_store_returns_zero() -> None:
    _reset()
    assert get_windowed_global_p75_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "gp75_old": [(_NOW - _WIN - 100, 9999.0, True)] * 5,
    })
    assert get_windowed_global_p75_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_global_p75_ge_global_p50() -> None:
    """global p75 >= global p50 for any non-empty window."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_global_p50_ms
    _reset()
    store = _make_store({
        "gp75_ord_a": [(_NOW - 10, float(v), True) for v in [10, 30, 70]],
        "gp75_ord_b": [(_NOW - 10, float(v), True) for v in [90, 150]],
    })
    p75 = get_windowed_global_p75_ms(_WIN, store=store, now_ms=_NOW)
    p50 = get_windowed_global_p50_ms(_WIN, store=store, now_ms=_NOW)
    assert p75 >= p50, f"global p75={p75} must be >= global p50={p50}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gp75_rt": [(_NOW - 10, float(v), True) for v in [50, 100, 200]]})
    assert isinstance(get_windowed_global_p75_ms(_WIN, store=store, now_ms=_NOW), float)
