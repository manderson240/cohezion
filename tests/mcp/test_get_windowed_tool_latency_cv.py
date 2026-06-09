"""Item 1012: get_windowed_tool_latency_cv(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool coefficient of variation of latency: stddev_ms / mean_ms.

Dimensionless ratio measuring relative latency spread.
0.0 for unknown/empty or when mean=0 (divide-by-zero guard).
Injectable store. Pure function.
CV > 1 -> high relative variability; CV < 0.5 -> tight/predictable.

PRIMARY DISC.: lats [10, 20, 30, 40, 50]
  mean = (10+20+30+40+50)/5 = 30
  variance = ((10-30)^2+(20-30)^2+(30-30)^2+(40-30)^2+(50-30)^2)/5
           = (400+100+0+100+400)/5 = 1000/5 = 200
  stddev = sqrt(200) ≈ 14.1421
  CV = stddev / mean = 14.1421 / 30 ≈ 0.4714
  (PRIMARY DISC.: kills stddev=14.1421 float; kills mean=30 float; correct CV≈0.4714 float)
"""
from __future__ import annotations
import math

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_cv,
    get_windowed_tool_latency_stddev_ms,
    get_windowed_tool_mean_latency_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_latency_cv_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,20,30,40,50] -> CV = stddev/mean = sqrt(200)/30 ≈ 0.4714.

    Kills impl returning stddev=sqrt(200)≈14.14 (not dimensionless ratio).
    Kills impl returning mean=30 (not dimensionless ratio).
    Kills impl returning variance=200 (not CV).
    """
    _reset()
    store = _make_store({
        "cv_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
    })
    result = get_windowed_tool_latency_cv("cv_a", _WIN, store=store, now_ms=_NOW)
    expected_cv = math.sqrt(200.0) / 30.0  # ≈ 0.47140
    assert isinstance(result, float)
    assert abs(result - expected_cv) < 1e-9, (
        f"CV=stddev/mean=sqrt(200)/30≈{expected_cv:.6f}; got {result}"
    )


def test_cv_equals_stddev_over_mean() -> None:
    """CV == stddev / mean (cross-function consistency)."""
    _reset()
    store = _make_store({
        "cv_cons": [(_NOW - 10, float(v), True) for v in [50, 100, 200, 400, 800]],
    })
    cv = get_windowed_tool_latency_cv("cv_cons", _WIN, store=store, now_ms=_NOW)
    stddev = get_windowed_tool_latency_stddev_ms("cv_cons", _WIN, store=store, now_ms=_NOW)
    mean = get_windowed_tool_mean_latency_ms("cv_cons", _WIN, store=store, now_ms=_NOW)
    assert abs(cv - stddev / mean) < 1e-9, (
        f"cv={cv} must equal stddev/mean={stddev}/{mean}={stddev/mean}"
    )


def test_zero_variance_cv_is_zero() -> None:
    """All latencies equal -> stddev=0 -> CV=0.0."""
    _reset()
    store = _make_store({
        "cv_zero": [(_NOW - 10, 100.0, True)] * 5,
    })
    result = get_windowed_tool_latency_cv("cv_zero", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 0.0) < 1e-9, f"all-equal latencies -> CV=0.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_cv("no_such_cv", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "cv_old": [(_NOW - _WIN - 100, 100.0, True)] * 5,
    })
    assert get_windowed_tool_latency_cv("cv_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_single_call_returns_zero() -> None:
    """Single call -> stddev=0 -> CV=0.0."""
    _reset()
    store = _make_store({
        "cv_one": [(_NOW - 10, 500.0, True)],
    })
    result = get_windowed_tool_latency_cv("cv_one", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 0.0) < 1e-9, f"single call -> CV=0.0; got {result}"


def test_high_variability_cv_gt_one() -> None:
    """High-variance latencies produce CV > 1 (e.g. [1, 100, 10000])."""
    _reset()
    store = _make_store({
        "cv_high": [(_NOW - 10, float(v), True) for v in [1, 100, 10000]],
    })
    result = get_windowed_tool_latency_cv("cv_high", _WIN, store=store, now_ms=_NOW)
    assert result > 1.0, f"highly variable [1,100,10000] should have CV>1; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"cv_rt": [(_NOW - 10, float(v), True) for v in [10, 50, 200]]})
    assert isinstance(get_windowed_tool_latency_cv("cv_rt", _WIN, store=store, now_ms=_NOW), float)
