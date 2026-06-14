"""Item 1037: get_windowed_global_latency_mad_ms(window_ms, *, store=None, now_ms=None) -> float
-- Fleet-wide Median Absolute Deviation (MAD) of pooled latency.

Pool ALL latencies across ALL tools in window; then
  MAD = median(|lat - median(pooled)|).
0.0 for empty store or all calls outside window.
Injectable store. Pure function.

PRIMARY DISC.: tool_a=[10,20,30] + tool_b=[100]
  pooled (sorted) = [10, 20, 30, 100]
  median (n=4) = (20+30)/2 = 25.0
  abs_devs = [|10-25|, |20-25|, |30-25|, |100-25|] = [15, 5, 5, 75]
  sorted_devs = [5, 5, 15, 75]
  MAD = median (n=4) = (5+15)/2 = 10.0
  (PRIMARY DISC.: kills avg_per_tool=(10+0)/2=5.0 (per-tool MAD then average);
   kills mean_abs_dev=(15+5+5+75)/4=25.0 (mean not median of devs);
   kills pooled_median=25.0 (the median before subtraction);
   correct pooled_MAD=10.0).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_mad_ms,
    get_windowed_tool_latency_mad_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_mad_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=[10,20,30] + tool_b=[100] -> pooled_MAD=10.0.

    Kills avg_per_tool=(10+0)/2=5.0 (wrong: per-tool then average).
    Kills mean_abs_dev=25.0 (uses mean not median of devs).
    Correct: pooled=[10,20,30,100], median=25.0,
    sorted_devs=[5,5,15,75], MAD=(5+15)/2=10.0.
    """
    _reset()
    store = _make_store(
        {
            "gm_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30]],
            "gm_b": [(_NOW - 10, 100.0, True)],
        }
    )
    result = get_windowed_global_latency_mad_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 10.0) < 1e-9, (
        f"pooled_MAD=10.0; kills per-tool-avg=5.0/mean_abs=25.0; got {result}"
    )


def test_global_mad_pools_not_averages() -> None:
    """Pooled MAD ≠ average of per-tool MADs (PRIMARY distinction)."""
    _reset()
    store = _make_store(
        {
            "gm_c": [(_NOW - 10, float(v), True) for v in [10, 20, 30]],
            "gm_d": [(_NOW - 10, 100.0, True)],
        }
    )
    global_mad = get_windowed_global_latency_mad_ms(_WIN, store=store, now_ms=_NOW)
    mad_c = get_windowed_tool_latency_mad_ms("gm_c", _WIN, store=store, now_ms=_NOW)
    mad_d = get_windowed_tool_latency_mad_ms("gm_d", _WIN, store=store, now_ms=_NOW)
    naive_avg = (mad_c + mad_d) / 2
    assert abs(global_mad - naive_avg) > 1e-9, (
        f"pooled_MAD={global_mad} must differ from avg_per_tool={naive_avg}"
    )


def test_single_tool_matches_per_tool_mad() -> None:
    """Single tool in store -> global MAD equals per-tool MAD."""
    _reset()
    lats = [10.0, 20.0, 30.0, 40.0, 100.0]
    store = _make_store(
        {
            "gm_single": [(_NOW - 10, v, True) for v in lats],
        }
    )
    global_mad = get_windowed_global_latency_mad_ms(_WIN, store=store, now_ms=_NOW)
    per_tool_mad = get_windowed_tool_latency_mad_ms("gm_single", _WIN, store=store, now_ms=_NOW)
    assert abs(global_mad - per_tool_mad) < 1e-9, (
        f"single-tool: global={global_mad} must equal per_tool={per_tool_mad}"
    )


def test_all_equal_global_mad_zero() -> None:
    """All identical latencies across all tools -> global MAD=0.0."""
    _reset()
    store = _make_store(
        {
            "gm_eq1": [(_NOW - 10, 100.0, True)] * 5,
            "gm_eq2": [(_NOW - 10, 100.0, True)] * 3,
        }
    )
    result = get_windowed_global_latency_mad_ms(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"all-equal -> global_MAD=0.0; got {result}"


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_mad_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_all_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gm_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
        }
    )
    assert get_windowed_global_latency_mad_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_global_mad_robust_to_outlier() -> None:
    """Fleet-wide MAD is much smaller than fleet-wide stddev with extreme outlier."""
    _reset()
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_global_latency_stddev_ms

    # 9 tools each with 1 call at 10ms, 1 call at 10000ms
    store = _make_store(
        {
            "gm_rob_main": [(_NOW - 10, 10.0, True)] * 9,
            "gm_rob_spike": [(_NOW - 10, 10000.0, True)],
        }
    )
    mad = get_windowed_global_latency_mad_ms(_WIN, store=store, now_ms=_NOW)
    stddev = get_windowed_global_latency_stddev_ms(_WIN, store=store, now_ms=_NOW)
    assert mad < stddev, f"global MAD={mad} must be << global stddev={stddev} with outlier"
    assert mad == 0.0, f"median of 9x10ms+1x10000ms=10ms; MAD of mostly-10s=0.0; got {mad}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gm_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    assert isinstance(get_windowed_global_latency_mad_ms(_WIN, store=store, now_ms=_NOW), float)
