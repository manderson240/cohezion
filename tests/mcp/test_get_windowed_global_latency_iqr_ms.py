"""Item 1000: get_windowed_global_latency_iqr_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide interquartile range (IQR = p75 - p25) of pooled latency in window.

Fleet-wide dual of get_windowed_tool_latency_iqr_ms (item 999).
IQR = get_windowed_global_latency_percentile(75, ...) - get_windowed_global_latency_percentile(25, ...)
0.0 when no recent calls. Returns float.

PRIMARY DISC.:
  tool_a [10, 50] + tool_b [20, 30] -> pooled sorted [10, 20, 30, 50]
  p75: idx=0.75*3=2.25 -> 30 + 0.25*(50-30) = 35.0
  p25: idx=0.25*3=0.75 -> 10 + 0.75*(20-10) = 17.5
  IQR = 35.0 - 17.5 = 17.5

  per-tool IQR:
    tool_a [10,50]: p75=idx=0.75*1=0.75 -> 10+0.75*40=40.0; p25=idx=0.25*1=0.25 -> 10+0.25*40=20.0; IQR=20.0
    tool_b [20,30]: p75=idx=0.75*1=0.75 -> 20+0.75*10=27.5; p25=idx=0.25*1=0.25 -> 20+0.25*10=22.5; IQR=5.0
    avg-of-per-tool-IQR = (20.0+5.0)/2 = 12.5  -> WRONG
    pooled IQR = 17.5                            -> CORRECT (different from both)
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_iqr_ms,
    get_windowed_tool_latency_iqr_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_pooled_iqr_not_avg_per_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: pooled IQR=17.5 != avg-of-per-tool-IQR=12.5.

    tool_a [10,50]: p75=40.0, p25=20.0, IQR=20.0
    tool_b [20,30]: p75=27.5, p25=22.5, IQR=5.0
    avg-of-per-tool-IQR = (20.0+5.0)/2 = 12.5  -> WRONG
    pooled [10,20,30,50]: p75=35.0, p25=17.5, IQR=17.5  -> CORRECT
    """
    _reset()
    store = _make_store(
        {
            "giqr_a": [(_NOW - 10, 10.0, True), (_NOW - 10, 50.0, True)],
            "giqr_b": [(_NOW - 10, 20.0, True), (_NOW - 10, 30.0, True)],
        }
    )
    result = get_windowed_global_latency_iqr_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 17.5) < 1e-9, f"pooled IQR=17.5; kills avg-of-per-tool=12.5; got {result}"
    # not avg-of-per-tool
    assert abs(result - 12.5) > 1.0


def test_single_tool_matches_per_tool_iqr() -> None:
    """With one tool, global IQR == per-tool IQR."""
    _reset()
    store = _make_store(
        {
            "giqr_one": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
        }
    )
    global_iqr = get_windowed_global_latency_iqr_ms(_WIN, store=store, now_ms=_NOW)
    per_tool = get_windowed_tool_latency_iqr_ms("giqr_one", _WIN, store=store, now_ms=_NOW)
    assert abs(global_iqr - per_tool) < 1e-9, (
        f"single tool: global_iqr={global_iqr} must equal per_tool_iqr={per_tool}"
    )


def test_empty_store_returns_zero() -> None:
    _reset()
    assert get_windowed_global_latency_iqr_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_old_calls_excluded() -> None:
    """Calls outside window must not contribute to IQR."""
    _reset()
    store = _make_store(
        {
            "giqr_old": [(_NOW - _WIN - 100, 9999.0, True)] * 5
            + [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
        }
    )
    result = get_windowed_global_latency_iqr_ms(_WIN, store=store, now_ms=_NOW)
    # [10,20,30,40,50]: IQR = 40.0 - 20.0 = 20.0
    assert abs(result - 20.0) < 1e-9, f"Old excluded; IQR([10,20,30,40,50])=20.0; got {result}"


def test_non_negative() -> None:
    """Fleet-wide IQR is always non-negative."""
    _reset()
    store = _make_store(
        {
            "giqr_nn": [(_NOW - 10, float(v), True) for v in range(1, 11)],
        }
    )
    result = get_windowed_global_latency_iqr_ms(_WIN, store=store, now_ms=_NOW)
    assert result >= 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"giqr_rt": [(_NOW - 10, float(v), True) for v in [5, 10, 15, 20, 25]]})
    assert isinstance(get_windowed_global_latency_iqr_ms(_WIN, store=store, now_ms=_NOW), float)
