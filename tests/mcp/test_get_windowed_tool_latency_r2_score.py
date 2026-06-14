"""Item 1081: get_windowed_tool_latency_r2_score(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool R² (coefficient of determination) for the linear trend.
R²=1.0 means latency is perfectly linear in time; R²≈0 means no linear trend.
0.0 for <2 samples or zero total variance.

PRIMARY DISC.: ts=[t-300,t-200,t-100,t-0], lats=[10,50,20,40]
  relative ts=[0,100,200,300]; t_mean=150, l_mean=30
  slope=0.06, intercept=21; ŷ=[21,27,33,39]
  SStot=1000, SSres=820, R²=1-820/1000=0.18
  (PRIMARY DISC.: kills correlation r=sqrt(R²)=sqrt(0.18)≈0.424 -- different number;
   kills R²=1 assumption (perfect trend), actual=0.18 (noisy);
   correct R²(OLS)=0.18).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_r2_score,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_r2_primary_discriminator() -> None:
    """PRIMARY DISC.: noisy 4-point series -> R²=0.18.

    Kills correlation r≈0.424 (sqrt of R², different number).
    Kills R²=1.0 (wrong -- data is noisy, not perfectly linear).
    Correct: R²=0.18.
    """
    _reset()
    store = _make_store(
        {
            "r2_disc": [
                (_NOW - 300, 10.0, True),
                (_NOW - 200, 50.0, True),
                (_NOW - 100, 20.0, True),
                (_NOW - 0, 40.0, True),
            ],
        }
    )
    result = get_windowed_tool_latency_r2_score("r2_disc", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 0.18) < 1e-6, f"noisy series R²=0.18; kills r≈0.424; got {result}"


def test_r2_perfect_linear_trend_returns_one() -> None:
    """Perfectly linear latency in time -> R²=1.0."""
    _reset()
    store = _make_store(
        {
            "r2_perfect": [
                (_NOW - 300, 10.0, True),
                (_NOW - 200, 20.0, True),
                (_NOW - 100, 30.0, True),
                (_NOW - 0, 40.0, True),
            ],
        }
    )
    result = get_windowed_tool_latency_r2_score("r2_perfect", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"perfect linear -> R²=1.0; got {result}"


def test_r2_constant_latency_returns_zero() -> None:
    """Constant latency -> zero total variance -> R²=0.0 (not 1.0!)."""
    _reset()
    store = _make_store(
        {
            "r2_const": [(_NOW - float(d), 50.0, True) for d in [300, 200, 100, 0]],
        }
    )
    result = get_windowed_tool_latency_r2_score("r2_const", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"constant latency -> R²=0.0; got {result}"


def test_r2_single_sample_returns_zero() -> None:
    """Single sample -> <2 samples -> 0.0."""
    _reset()
    store = _make_store(
        {
            "r2_single": [(_NOW - 100, 42.0, True)],
        }
    )
    assert get_windowed_tool_latency_r2_score("r2_single", _WIN, store=store, now_ms=_NOW) == 0.0


def test_r2_empty_window_returns_zero() -> None:
    """Empty window -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_r2_score("no_tool", _WIN, store={}, now_ms=_NOW) == 0.0


def test_r2_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "r2_old": [(_NOW - _WIN - 100, float(v), True) for v in [10, 20, 30, 40]],
        }
    )
    assert get_windowed_tool_latency_r2_score("r2_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_r2_in_range_zero_to_one() -> None:
    """R² must be in [0, 1] for any valid dataset."""
    _reset()
    store = _make_store(
        {
            "r2_range": [
                (_NOW - float(d), float(v), True)
                for d, v in [(400, 50), (300, 10), (200, 80), (100, 20), (0, 40)]
            ],
        }
    )
    result = get_windowed_tool_latency_r2_score("r2_range", _WIN, store=store, now_ms=_NOW)
    assert 0.0 <= result <= 1.0, f"R² must be in [0,1]; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "r2_rt": [
                (_NOW - float(d), float(v), True)
                for d, v in [(300, 10), (200, 20), (100, 30), (0, 40)]
            ],
        }
    )
    assert isinstance(
        get_windowed_tool_latency_r2_score("r2_rt", _WIN, store=store, now_ms=_NOW), float
    )
