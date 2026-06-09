"""Item 1039: get_windowed_global_latency_winsorized_mean_ms(window_ms, winsor_pct=0.1, *, store=None, now_ms=None) -> float
-- Fleet-wide winsorized mean of pooled latency.

Pool ALL latencies across ALL tools, sort, clamp bottom/top floor(winsor_pct*n)
values to their boundary values, mean of all n clamped values.
0.0 for empty store. Default winsor_pct=0.1. Fleet dual of item 1035.

PRIMARY DISC.: tool_a=[10,100] + tool_b=[20,30,40] winsor_pct=0.2
  pooled sorted=[10,20,30,40,100], n=5, k=floor(0.2*5)=1
  lo=sorted[1]=20, hi=sorted[3]=40
  clamped=[20, 20, 30, 40, 40]
  mean=(20+20+30+40+40)/5=150/5=30.0
  (PRIMARY DISC.: kills full_mean=40.0;
   kills pooled_trimmed=30.0 (same value but n=3 denom, not n=5);
   kills boundary_pair=[20,40] (must average all 5 clamped);
   correct pooled_winsor_mean=30.0 with n=5 denominator).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_winsorized_mean_ms,
    get_windowed_global_mean_latency_ms,
    get_windowed_global_latency_trimmed_mean_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_winsorized_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=[10,100]+tool_b=[20,30,40] pct=0.2 -> 30.0.

    Kills full_mean=40.0 (no clamping, outlier 100 inflates).
    Kills pooled_trimmed=30.0 (same result but n=3 denominator, not n=5).
    Kills boundary_pair=[20,40] (must mean all 5 clamped values).
    Correct: k=1, lo=20, hi=40, clamped=[20,20,30,40,40], mean=150/5=30.0.
    """
    _reset()
    store = _make_store({
        "gw_a": [(_NOW - 10, float(v), True) for v in [10, 100]],
        "gw_b": [(_NOW - 10, float(v), True) for v in [20, 30, 40]],
    })
    result = get_windowed_global_latency_winsorized_mean_ms(_WIN, 0.2, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 30.0) < 1e-9, (
        f"pooled_winsor=30.0; kills full_mean=40.0; got {result}"
    )


def test_global_winsor_zero_equals_full_mean() -> None:
    """winsor_pct=0.0 -> winsorized mean == full mean (k=0, no clamping)."""
    _reset()
    store = _make_store({
        "gw_z1": [(_NOW - 10, float(v), True) for v in [10, 50, 200]],
        "gw_z2": [(_NOW - 10, float(v), True) for v in [300, 400]],
    })
    winsorized = get_windowed_global_latency_winsorized_mean_ms(_WIN, 0.0, store=store, now_ms=_NOW)
    full = get_windowed_global_mean_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(winsorized - full) < 1e-9, f"winsor=0: {winsorized} must equal full_mean={full}"


def test_global_winsor_retains_n_denominator() -> None:
    """Winsorized uses n denominator; trimmed uses (n - 2k) denominator.

    When the fixture causes k>0, trimmed and winsorized can differ.
    [0, 50, 50, 50, 1000] pct=0.2: k=1, lo=50, hi=50 -> all clamped to 50
    winsor_mean=50.0 (n=5) == trim_mean=50.0 (n=3 but all same).
    Use a fixture where they differ: [0, 20, 100, 100, 1000] pct=0.2
      sorted=[0,20,100,100,1000], k=1, lo=20, hi=100
      clamped=[20,20,100,100,100], sum=340, winsor_mean=340/5=68.0
      trim: keep [20,100,100], sum=220, trim_mean=220/3≈73.33 ≠ 68.0
    """
    _reset()
    store = _make_store({
        "gw_n5": [(_NOW - 10, float(v), True) for v in [0, 20, 100, 100, 1000]],
    })
    winsor = get_windowed_global_latency_winsorized_mean_ms(_WIN, 0.2, store=store, now_ms=_NOW)
    trimmed = get_windowed_global_latency_trimmed_mean_ms(_WIN, 0.2, store=store, now_ms=_NOW)
    assert abs(winsor - 68.0) < 1e-9, f"winsor_mean=68.0; got {winsor}"
    assert abs(trimmed - 220 / 3) < 1e-9, f"trim_mean=220/3≈73.33; got {trimmed}"
    assert abs(winsor - trimmed) > 1e-6, (
        f"winsor={winsor} must differ from trim={trimmed} (different denominators)"
    )


def test_default_winsor_pct_is_0_1() -> None:
    """Default winsor_pct is 0.1."""
    _reset()
    store = _make_store({
        "gw_def": [(_NOW - 10, float(v), True) for v in range(10, 110, 10)],
    })
    default = get_windowed_global_latency_winsorized_mean_ms(_WIN, store=store, now_ms=_NOW)
    explicit = get_windowed_global_latency_winsorized_mean_ms(_WIN, 0.1, store=store, now_ms=_NOW)
    assert abs(default - explicit) < 1e-9, f"default==0.1: {default} vs {explicit}"


def test_winsor_reduces_outlier_influence() -> None:
    """Winsorized fleet mean < full fleet mean when outlier present."""
    _reset()
    store = _make_store({
        "gw_main": [(_NOW - 10, 10.0, True)] * 9,
        "gw_spike": [(_NOW - 10, 10000.0, True)],
    })
    winsorized = get_windowed_global_latency_winsorized_mean_ms(_WIN, 0.1, store=store, now_ms=_NOW)
    full = get_windowed_global_mean_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert winsorized < full, f"winsorized={winsorized} must be < full_mean={full}"


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_winsorized_mean_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_all_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "gw_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
    })
    assert get_windowed_global_latency_winsorized_mean_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gw_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    assert isinstance(
        get_windowed_global_latency_winsorized_mean_ms(_WIN, store=store, now_ms=_NOW), float
    )
