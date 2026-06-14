"""Item 1041: get_windowed_global_latency_kurtosis(window_ms, *, store=None, now_ms=None) -> float
-- Fleet-wide excess kurtosis of pooled latency (Fisher definition).

Pool ALL latencies across ALL tools; then:
  raw_kurtosis = sum((lat - mean)^4) / (n * pop_stddev^4)
  excess_kurtosis = raw_kurtosis - 3.0
0.0 for n < 4 or pop_stddev = 0.0. Injectable store. Pure function.
Fleet dual of item 1030 (per-tool kurtosis).

PRIMARY DISC.: tool_a=[10,10,10,10] + tool_b=[100]
  pooled=[10,10,10,10,100], n=5, mean=28.0, pop_var=1296.0, pop_std=36.0,
  sum4=4*(10-28)^4+(100-28)^4=4*104976+26873856=27293760,
  raw_kurt=27293760/(5*36^4)=27293760/8398080=3.25,
  excess_kurtosis=3.25-3.0=0.25
  (PRIMARY DISC.: kills per-tool-avg: tool_a all-equal→0.0, tool_b n<4→0.0;
   kills raw_kurt=3.25 without -3 offset;
   correct excess_kurtosis=0.25 float).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_kurtosis,
    get_windowed_tool_latency_kurtosis,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_kurtosis_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=[10,10,10,10]+tool_b=[100] -> excess_kurtosis=0.25.

    Kills per-tool-avg=0.0 (tool_a all-equal→0, tool_b n<4→0).
    Kills raw_kurt=3.25 (missing -3 Fisher correction).
    Correct: pooled n=5, exact excess_kurtosis=0.25.
    """
    _reset()
    store = _make_store(
        {
            "gk_a": [(_NOW - 10, 10.0, True)] * 4,
            "gk_b": [(_NOW - 10, 100.0, True)],
        }
    )
    result = get_windowed_global_latency_kurtosis(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 0.25) < 1e-9, (
        f"excess_kurtosis=0.25; kills per-tool-avg=0.0/raw_kurt=3.25; got {result}"
    )


def test_global_kurtosis_pools_not_averages() -> None:
    """Pooled kurtosis ≠ average of per-tool kurtosis values."""
    _reset()
    store = _make_store(
        {
            "gk_c": [(_NOW - 10, 10.0, True)] * 4,
            "gk_d": [(_NOW - 10, 100.0, True)],
        }
    )
    global_kurt = get_windowed_global_latency_kurtosis(_WIN, store=store, now_ms=_NOW)
    kurt_c = get_windowed_tool_latency_kurtosis("gk_c", _WIN, store=store, now_ms=_NOW)
    kurt_d = get_windowed_tool_latency_kurtosis("gk_d", _WIN, store=store, now_ms=_NOW)
    naive_avg = (kurt_c + kurt_d) / 2
    assert abs(global_kurt - naive_avg) > 1e-9, (
        f"pooled_kurt={global_kurt} must differ from per_tool_avg={naive_avg}"
    )


def test_single_tool_matches_per_tool_kurtosis() -> None:
    """Single tool -> global kurtosis equals per-tool kurtosis."""
    _reset()
    lats = [10.0, 20.0, 30.0, 40.0, 100.0]
    store = _make_store(
        {
            "gk_single": [(_NOW - 10, v, True) for v in lats],
        }
    )
    global_kurt = get_windowed_global_latency_kurtosis(_WIN, store=store, now_ms=_NOW)
    per_tool_kurt = get_windowed_tool_latency_kurtosis("gk_single", _WIN, store=store, now_ms=_NOW)
    assert abs(global_kurt - per_tool_kurt) < 1e-9, (
        f"single-tool: global={global_kurt} must equal per_tool={per_tool_kurt}"
    )


def test_normal_like_distribution_near_zero() -> None:
    """Normal-like distribution -> excess kurtosis near 0.0."""
    _reset()
    # Gaussian-like data: small excess kurtosis
    store = _make_store(
        {
            "gk_norm": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
        }
    )
    result = get_windowed_global_latency_kurtosis(_WIN, store=store, now_ms=_NOW)
    # Uniform [10..50] has negative excess kurtosis (platykurtic)
    assert result < 0.0, f"uniform-like dist -> negative excess kurtosis; got {result}"


def test_n_less_than_4_returns_zero() -> None:
    """n < 4 pooled -> 0.0 (not enough data)."""
    _reset()
    store = _make_store(
        {
            "gk_small": [(_NOW - 10, float(v), True) for v in [10, 20, 30]],
        }
    )
    assert get_windowed_global_latency_kurtosis(_WIN, store=store, now_ms=_NOW) == 0.0


def test_all_equal_returns_zero() -> None:
    """All equal pooled latencies -> 0.0 (pop_stddev=0 guard)."""
    _reset()
    store = _make_store(
        {
            "gk_eq": [(_NOW - 10, 100.0, True)] * 6,
        }
    )
    assert get_windowed_global_latency_kurtosis(_WIN, store=store, now_ms=_NOW) == 0.0


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_kurtosis(_WIN, store={}, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gk_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200, 500]]})
    assert isinstance(get_windowed_global_latency_kurtosis(_WIN, store=store, now_ms=_NOW), float)
