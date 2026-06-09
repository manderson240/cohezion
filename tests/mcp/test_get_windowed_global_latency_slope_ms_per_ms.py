"""Item 1080: get_windowed_global_latency_slope_ms_per_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide latency trend: OLS slope across ALL tool latencies pooled by timestamp.
Positive = fleet worsening; negative = fleet improving.
0.0 for <2 windowed samples or zero time variance. Fleet dual of item 1079.

PRIMARY DISC.: tool_a=[10 at t-200, 50 at t-50], tool_b=[100 at t-100, 20 at t-0]
  pooled sorted by ts: [(t-200,10),(t-100,100),(t-50,50),(t-0,20)]
  relative ts=[0,100,150,200]; t_mean=112.5, l_mean=45.0
  Σ(ti-tm)(li-lm) = 3937.5-687.5+187.5-2187.5 = 1250
  Σ(ti-tm)^2 = 12656.25+156.25+1406.25+7656.25 = 21875
  slope = 1250/21875 ≈ 0.05714 ms/ms
  (PRIMARY DISC.: kills per-tool slope avg: tool_a=0.267, tool_b=-0.8 -> avg=-0.267
   -- opposite sign from pooled; pooled captures fleet-wide temporal trend correctly).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_slope_ms_per_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_slope_primary_discriminator() -> None:
    """PRIMARY DISC.: interleaved tools -> pooled OLS ≈ +0.057 ms/ms.

    Per-tool avg slope = -0.267 ms/ms (opposite sign!).
    Correct: pooled OLS captures the actual fleet-wide temporal trend.
    """
    _reset()
    store = _make_store({
        "gslope_a": [
            (_NOW - 200, 10.0, True),   # oldest, low latency
            (_NOW - 50, 50.0, True),    # recent, higher
        ],
        "gslope_b": [
            (_NOW - 100, 100.0, True),  # middle, very high
            (_NOW - 0, 20.0, True),     # newest, low
        ],
    })
    result = get_windowed_global_latency_slope_ms_per_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - (1250.0 / 21875.0)) < 1e-6, (
        f"pooled OLS≈0.05714; kills per-tool avg=-0.267; got {result}"
    )


def test_global_slope_uniformly_increasing_fleet() -> None:
    """Fleet latency clearly increasing over time -> positive slope."""
    _reset()
    store = _make_store({
        "gslope_inc_a": [(_NOW - 300, 10.0, True)],
        "gslope_inc_b": [(_NOW - 200, 20.0, True)],
        "gslope_inc_c": [(_NOW - 100, 30.0, True)],
        "gslope_inc_d": [(_NOW - 0, 40.0, True)],
    })
    result = get_windowed_global_latency_slope_ms_per_ms(_WIN, store=store, now_ms=_NOW)
    assert result > 0.0, f"increasing fleet -> positive slope; got {result}"


def test_global_slope_uniformly_decreasing_fleet() -> None:
    """Fleet latency clearly decreasing -> negative slope."""
    _reset()
    store = _make_store({
        "gslope_dec_a": [(_NOW - 300, 40.0, True)],
        "gslope_dec_b": [(_NOW - 200, 30.0, True)],
        "gslope_dec_c": [(_NOW - 100, 20.0, True)],
        "gslope_dec_d": [(_NOW - 0, 10.0, True)],
    })
    result = get_windowed_global_latency_slope_ms_per_ms(_WIN, store=store, now_ms=_NOW)
    assert result < 0.0, f"decreasing fleet -> negative slope; got {result}"


def test_global_slope_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_slope_ms_per_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_global_slope_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "gslope_old": [(_NOW - _WIN - 100, float(v), True) for v in [10, 20, 30]],
    })
    assert get_windowed_global_latency_slope_ms_per_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_global_slope_single_sample_returns_zero() -> None:
    """Only one pooled sample -> <2 -> 0.0."""
    _reset()
    store = _make_store({"gslope_single": [(_NOW - 100, 42.0, True)]})
    assert get_windowed_global_latency_slope_ms_per_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_global_slope_zero_time_variance_returns_zero() -> None:
    """All pooled samples at identical timestamps -> zero denominator -> 0.0."""
    _reset()
    store = _make_store({
        "gslope_same_ts_a": [(_NOW - 100, 10.0, True)],
        "gslope_same_ts_b": [(_NOW - 100, 50.0, True)],
    })
    result = get_windowed_global_latency_slope_ms_per_ms(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"zero ts variance -> 0.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({
        "gslope_rt_a": [(_NOW - 200, 10.0, True)],
        "gslope_rt_b": [(_NOW - 100, 20.0, True)],
    })
    result = get_windowed_global_latency_slope_ms_per_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
