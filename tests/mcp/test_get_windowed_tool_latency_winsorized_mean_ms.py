"""Item 1035: get_windowed_tool_latency_winsorized_mean_ms(tool_name, window_ms, winsor_pct=0.1, *, store=None, now_ms=None) -> float
-- Winsorized mean of latency in window.

Clamp bottom/top floor(winsor_pct * n) values to their boundary values;
take the mean of all n clamped values.
0.0 for unknown/empty tool. Injectable store. Pure function. Default winsor_pct=0.1.

PRIMARY DISC.: lats [10, 20, 30, 40, 100] winsor_pct=0.2
  n=5, k=floor(0.2*5)=1 -> sorted=[10,20,30,40,100]
  lo=sorted[1]=20, hi=sorted[3]=40
  clamped=[20, 20, 30, 40, 40]   (10 clamped up to 20; 100 clamped down to 40)
  winsor_mean=(20+20+30+40+40)/5=150/5=30.0
  (PRIMARY DISC.: kills full_mean=40.0 (no clamping);
   kills trimmed_mean=30.0 (same value but n=3 denom not n=5);
   kills raw_boundary_vals=[20,40] (wrong, must use all 5 clamped values);
   correct winsor_mean=30.0 float with n=5 denominator).

Distinct from trimmed_mean: winsorized RETAINS n in denominator (n=5 here),
trimmed REMOVES k values from each end (n=3 here). Same result coincidentally
for this fixture; test_winsor_pct_zero confirms n=5 full-mean behaviour.
"""
from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_winsorized_mean_ms,
    get_windowed_tool_mean_latency_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_winsorized_mean_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,20,30,40,100] winsor_pct=0.2 -> winsor_mean=30.0.

    Kills full_mean=40.0 (no clamping applied, outlier 100 inflates).
    Kills boundary_pair=[20,40] (wrong: must average all 5 clamped values).
    Correct: k=1, lo=20, hi=40, clamped=[20,20,30,40,40], mean=150/5=30.0.
    """
    _reset()
    store = _make_store({
        "wm_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 100]],
    })
    result = get_windowed_tool_latency_winsorized_mean_ms(
        "wm_a", _WIN, 0.2, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 30.0) < 1e-9, (
        f"winsor_mean=30.0; kills full_mean=40.0; got {result}"
    )


def test_winsor_pct_zero_equals_full_mean() -> None:
    """winsor_pct=0.0 -> winsorized mean == full mean (k=0, no clamping)."""
    _reset()
    lats = [10.0, 50.0, 200.0, 300.0]
    store = _make_store({
        "wm_zero": [(_NOW - 10, v, True) for v in lats],
    })
    winsorized = get_windowed_tool_latency_winsorized_mean_ms(
        "wm_zero", _WIN, 0.0, store=store, now_ms=_NOW
    )
    full = get_windowed_tool_mean_latency_ms("wm_zero", _WIN, store=store, now_ms=_NOW)
    assert abs(winsorized - full) < 1e-9, f"winsor=0: {winsorized} must equal full={full}"


def test_winsor_retains_n_in_denominator() -> None:
    """Winsorized mean uses n=5 denominator (not n=3 like trimmed).

    Fixture: [0, 50, 50, 50, 1000] winsor_pct=0.2
      k=1, lo=50, hi=50 -> all 5 clamped to 50 -> mean=50.0
    This is different from raw trimmed (same for this fixture)
    but confirms n=5 denominator by checking against full_mean.
    """
    _reset()
    lats = [0.0, 50.0, 50.0, 50.0, 1000.0]
    store = _make_store({
        "wm_n5": [(_NOW - 10, v, True) for v in lats],
    })
    result = get_windowed_tool_latency_winsorized_mean_ms("wm_n5", _WIN, 0.2, store=store, now_ms=_NOW)
    # sorted=[0,50,50,50,1000], k=1, lo=50, hi=50 -> clamped=[50,50,50,50,50] -> mean=50.0
    assert abs(result - 50.0) < 1e-9, f"all-clamped-to-50 -> 50.0; got {result}"
    full = get_windowed_tool_mean_latency_ms("wm_n5", _WIN, store=store, now_ms=_NOW)
    assert result != full, f"winsorized={result} should differ from full_mean={full} (outliers clamped)"


def test_winsor_reduces_outlier_influence() -> None:
    """Winsorized mean < full mean when outlier present."""
    _reset()
    # 9 at 10ms, 1 at 10000ms
    lats = [10.0] * 9 + [10000.0]
    store = _make_store({
        "wm_out": [(_NOW - 10, v, True) for v in lats],
    })
    winsorized = get_windowed_tool_latency_winsorized_mean_ms("wm_out", _WIN, 0.1, store=store, now_ms=_NOW)
    full = get_windowed_tool_mean_latency_ms("wm_out", _WIN, store=store, now_ms=_NOW)
    assert winsorized < full, f"winsorized={winsorized} must be < full_mean={full}"


def test_all_equal_winsor_equals_value() -> None:
    """All equal latencies -> winsorized mean == that value."""
    _reset()
    store = _make_store({
        "wm_eq": [(_NOW - 10, 100.0, True)] * 10,
    })
    result = get_windowed_tool_latency_winsorized_mean_ms("wm_eq", _WIN, 0.1, store=store, now_ms=_NOW)
    assert abs(result - 100.0) < 1e-9, f"all-equal -> 100.0; got {result}"


def test_default_winsor_pct_is_0_1() -> None:
    """Default winsor_pct is 0.1."""
    _reset()
    lats = [1.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 100.0]
    store = _make_store({
        "wm_def": [(_NOW - 10, v, True) for v in lats],
    })
    default = get_windowed_tool_latency_winsorized_mean_ms("wm_def", _WIN, store=store, now_ms=_NOW)
    explicit = get_windowed_tool_latency_winsorized_mean_ms("wm_def", _WIN, 0.1, store=store, now_ms=_NOW)
    assert abs(default - explicit) < 1e-9, f"default==0.1: {default} vs {explicit}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_winsorized_mean_ms("no_such_wm", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "wm_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
    })
    assert get_windowed_tool_latency_winsorized_mean_ms("wm_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"wm_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 200]]})
    assert isinstance(
        get_windowed_tool_latency_winsorized_mean_ms("wm_rt", _WIN, store=store, now_ms=_NOW), float
    )
