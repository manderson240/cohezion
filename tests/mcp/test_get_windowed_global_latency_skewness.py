"""Item 1040: get_windowed_global_latency_skewness(window_ms, *, store=None, now_ms=None) -> float
-- Fleet-wide population skewness of pooled latency.

Pool ALL latencies across ALL tools; then
  skewness = sum((lat - mean)^3) / (n * pop_stddev^3)
0.0 for n < 3 or pop_stddev = 0.0. Injectable store. Pure function.
Fleet dual of item 1022 (per-tool skewness).

PRIMARY DISC.: tool_a=[10,10,10] + tool_b=[100]
  pooled=[10,10,10,100], n=4, mean=32.5, pop_var=1518.75,
  pop_std=38.971..., sum_cubed=273375.0,
  skewness = 2/sqrt(3) ≈ 1.1547
  (PRIMARY DISC.: kills per-tool-avg=0.0 — tool_a all-equal→0, tool_b n=1<3→0;
   kills skewness=0.0 (symmetric assumption);
   correct positive pooled_skewness≈1.1547).
"""
from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_skewness,
    get_windowed_tool_latency_skewness,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_skewness_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=[10,10,10]+tool_b=[100] -> pooled≈1.1547.

    Kills per-tool-avg=0.0 (tool_a all-equal→0, tool_b n<3→0).
    Kills skewness=0.0 (data is right-skewed, not symmetric).
    Correct: pooled n=4 mean=32.5, sum_cubed/n/std^3=2/sqrt(3)≈1.1547.
    """
    _reset()
    store = _make_store({
        "gs_a": [(_NOW - 10, 10.0, True)] * 3,
        "gs_b": [(_NOW - 10, 100.0, True)],
    })
    result = get_windowed_global_latency_skewness(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    expected = 2.0 / math.sqrt(3.0)
    assert abs(result - expected) < 1e-6, (
        f"pooled_skewness≈{expected:.6f} (2/sqrt(3)); kills per-tool-avg=0.0; got {result}"
    )


def test_global_skewness_pools_not_averages() -> None:
    """Pooled skewness ≠ average of per-tool skewness values."""
    _reset()
    store = _make_store({
        "gs_c": [(_NOW - 10, 10.0, True)] * 3,
        "gs_d": [(_NOW - 10, 100.0, True)],
    })
    global_skew = get_windowed_global_latency_skewness(_WIN, store=store, now_ms=_NOW)
    skew_c = get_windowed_tool_latency_skewness("gs_c", _WIN, store=store, now_ms=_NOW)
    skew_d = get_windowed_tool_latency_skewness("gs_d", _WIN, store=store, now_ms=_NOW)
    naive_avg = (skew_c + skew_d) / 2
    assert abs(global_skew - naive_avg) > 1e-9, (
        f"pooled_skew={global_skew} must differ from per_tool_avg={naive_avg}"
    )


def test_single_tool_matches_per_tool_skewness() -> None:
    """Single tool -> global skewness equals per-tool skewness."""
    _reset()
    lats = [10.0, 20.0, 30.0, 40.0, 100.0]
    store = _make_store({
        "gs_single": [(_NOW - 10, v, True) for v in lats],
    })
    global_skew = get_windowed_global_latency_skewness(_WIN, store=store, now_ms=_NOW)
    per_tool_skew = get_windowed_tool_latency_skewness("gs_single", _WIN, store=store, now_ms=_NOW)
    assert abs(global_skew - per_tool_skew) < 1e-9, (
        f"single-tool: global={global_skew} must equal per_tool={per_tool_skew}"
    )


def test_symmetric_data_skewness_near_zero() -> None:
    """Symmetric distribution -> skewness near 0.0."""
    _reset()
    # Symmetric: [10, 20, 30, 40, 50] — mean=30, symmetric devs
    store = _make_store({
        "gs_sym": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
    })
    result = get_windowed_global_latency_skewness(_WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"symmetric -> skewness≈0.0; got {result}"


def test_n_less_than_3_returns_zero() -> None:
    """n < 3 pooled -> 0.0 (not enough data)."""
    _reset()
    store = _make_store({
        "gs_small1": [(_NOW - 10, 10.0, True)],
        "gs_small2": [(_NOW - 10, 20.0, True)],
    })
    # pooled n=2
    result = get_windowed_global_latency_skewness(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"n=2 pooled -> 0.0; got {result}"


def test_all_equal_returns_zero() -> None:
    """All equal pooled latencies -> skewness=0.0 (stddev=0 guard)."""
    _reset()
    store = _make_store({
        "gs_eq1": [(_NOW - 10, 100.0, True)] * 5,
        "gs_eq2": [(_NOW - 10, 100.0, True)] * 3,
    })
    result = get_windowed_global_latency_skewness(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"all-equal -> skewness=0.0; got {result}"


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_skewness(_WIN, store={}, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gs_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200, 500]]})
    assert isinstance(get_windowed_global_latency_skewness(_WIN, store=store, now_ms=_NOW), float)
