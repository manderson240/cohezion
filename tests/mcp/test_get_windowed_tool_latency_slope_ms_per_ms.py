"""Item 1079: get_windowed_tool_latency_slope_ms_per_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool latency trend: OLS linear regression slope (ms latency / ms time).
Positive = worsening; negative = improving.
0.0 for <2 samples or no time variance.

PRIMARY DISC.: ts=[t-200, t-50, t-0], lats=[10,50,20]
  relative ts: [0, 150, 200]
  t_mean=116.667, l_mean=26.667
  Σ(ti-tm)(li-lm) = (-116.667)(-16.667)+(33.333)(23.333)+(83.333)(-6.667) = 2166.67
  Σ(ti-tm)^2 = 13611.11+1111.11+6944.44 = 21666.67
  slope = 2166.67/21666.67 = 0.1 ms/ms
  (PRIMARY DISC.: kills naive=(last-first)/span=(20-10)/200=0.05 ms/ms).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_slope_ms_per_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_slope_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,50,20] at ts [t-200,t-50,t], OLS slope=0.1 ms/ms.

    Kills naive=(last-first)/span=0.05 ms/ms (endpoint only, ignores middle).
    Correct: OLS slope=0.1 ms/ms.
    """
    _reset()
    store = _make_store(
        {
            "slope_disc": [
                (_NOW - 200, 10.0, True),  # oldest, lowest latency
                (_NOW - 50, 50.0, True),  # middle, highest latency
                (_NOW - 0, 20.0, True),  # newest
            ],
        }
    )
    result = get_windowed_tool_latency_slope_ms_per_ms("slope_disc", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 0.1) < 1e-6, f"OLS slope=0.1 ms/ms; kills naive=0.05 ms/ms; got {result}"


def test_slope_negative_trend() -> None:
    """Latency decreasing over time -> negative slope."""
    _reset()
    # [100, 60, 20] at ts [t-200, t-100, t-0]
    # relative ts: [0, 100, 200]; t_mean=100, l_mean=60
    # Σ(ti-tm)(li-lm) = (-100)(40)+(0)(0)+(100)(-40) = -4000-4000 = -8000
    # Σ(ti-tm)^2 = 10000+0+10000 = 20000
    # slope = -8000/20000 = -0.4
    store = _make_store(
        {
            "slope_neg": [
                (_NOW - 200, 100.0, True),
                (_NOW - 100, 60.0, True),
                (_NOW - 0, 20.0, True),
            ],
        }
    )
    result = get_windowed_tool_latency_slope_ms_per_ms("slope_neg", _WIN, store=store, now_ms=_NOW)
    assert result < 0.0, f"decreasing trend -> negative slope; got {result}"
    assert abs(result - (-0.4)) < 1e-6, f"OLS slope=-0.4; got {result}"


def test_slope_zero_variance_timestamps_returns_zero() -> None:
    """All samples at same timestamp -> no time variance -> 0.0."""
    _reset()
    store = _make_store(
        {
            "slope_zero_ts": [
                (_NOW - 100, 10.0, True),
                (_NOW - 100, 50.0, True),
                (_NOW - 100, 20.0, True),
            ],
        }
    )
    result = get_windowed_tool_latency_slope_ms_per_ms(
        "slope_zero_ts", _WIN, store=store, now_ms=_NOW
    )
    assert result == 0.0, f"zero ts variance -> 0.0; got {result}"


def test_slope_single_sample_returns_zero() -> None:
    """Single sample -> <2 samples -> 0.0."""
    _reset()
    store = _make_store(
        {
            "slope_single": [(_NOW - 100, 42.0, True)],
        }
    )
    result = get_windowed_tool_latency_slope_ms_per_ms(
        "slope_single", _WIN, store=store, now_ms=_NOW
    )
    assert result == 0.0, f"single sample -> 0.0; got {result}"


def test_slope_empty_window_returns_zero() -> None:
    """Empty window -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_slope_ms_per_ms("no_tool", _WIN, store={}, now_ms=_NOW) == 0.0


def test_slope_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "slope_old": [(_NOW - _WIN - 100, float(v), True) for v in [10, 20, 30]],
        }
    )
    result = get_windowed_tool_latency_slope_ms_per_ms("slope_old", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"all outside window -> 0.0; got {result}"


def test_slope_flat_trend_returns_near_zero() -> None:
    """Constant latency -> slope ≈ 0."""
    _reset()
    store = _make_store(
        {
            "slope_flat": [(_NOW - float(d), 50.0, True) for d in [300, 200, 100, 0]],
        }
    )
    result = get_windowed_tool_latency_slope_ms_per_ms("slope_flat", _WIN, store=store, now_ms=_NOW)
    assert abs(result) < 1e-9, f"constant latency -> slope≈0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "slope_rt": [
                (_NOW - float(d), float(v), True) for d, v in [(200, 10), (100, 30), (0, 20)]
            ],
        }
    )
    assert isinstance(
        get_windowed_tool_latency_slope_ms_per_ms("slope_rt", _WIN, store=store, now_ms=_NOW), float
    )
