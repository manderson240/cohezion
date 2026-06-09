"""Item 1061: get_windowed_tool_latency_robust_cv(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- per-tool robust coefficient of variation = IQR / median.

Outlier-resistant relative spread measure. 0.0 for n<4 or median==0.
Uses linear-interpolation Q1/Q3 (same as other percentile functions).
Injectable store. Pure function.

PRIMARY DISC.: lats [10,20,30,40,10000] n=5
  Q1=idx=0.25*4=1.0->20.0, Q3=idx=0.75*4=3.0->40.0, IQR=20, median=30
  robust_CV = IQR/median = 20/30 = 2/3 ≈ 0.6667
  (PRIMARY DISC.: kills CV=std/mean: std≈3990, mean=2020, CV≈1.975 -- extreme outlier 10000
     inflates std/mean dramatically but leaves IQR/median unchanged;
   correct robust_CV = 2/3 ≈ 0.6667).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_robust_cv,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_robust_cv_primary_discriminator() -> None:
    """PRIMARY DISC.: [10,20,30,40,10000] -> robust_CV=2/3≈0.6667.

    Kills CV=std/mean≈1.975 (outlier 10000 inflates std/mean dramatically).
    Correct: IQR=20, median=30, robust_CV=20/30=2/3.
    """
    _reset()
    store = _make_store({
        "rcv_disc": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 10000]],
    })
    result = get_windowed_tool_latency_robust_cv("rcv_disc", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 2 / 3) < 1e-9, (
        f"robust_CV=2/3≈0.6667; kills CV≈1.975; got {result}"
    )


def test_robust_cv_fewer_than_4_returns_zero() -> None:
    """n < 4 -> 0.0."""
    _reset()
    store = _make_store({
        "rcv_few": [(_NOW - 10, float(v), True) for v in [10, 20, 30]],
    })
    result = get_windowed_tool_latency_robust_cv("rcv_few", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"n=3 < 4 -> 0.0; got {result}"


def test_robust_cv_all_equal_returns_zero() -> None:
    """All equal -> IQR=0 -> robust_CV=0.0."""
    _reset()
    store = _make_store({
        "rcv_eq": [(_NOW - 10, 50.0, True)] * 6,
    })
    result = get_windowed_tool_latency_robust_cv("rcv_eq", _WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"all-equal -> robust_CV=0.0; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_robust_cv("no_such_rcv", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "rcv_old": [(_NOW - _WIN - 100, 50.0, True)] * 5,
    })
    assert get_windowed_tool_latency_robust_cv("rcv_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_robust_cv_non_negative() -> None:
    """robust_CV >= 0 (IQR >= 0, median > 0 for positive latencies)."""
    _reset()
    store = _make_store({
        "rcv_pos": [(_NOW - 10, float(v), True) for v in [10, 50, 200, 1000, 2000, 50]],
    })
    result = get_windowed_tool_latency_robust_cv("rcv_pos", _WIN, store=store, now_ms=_NOW)
    assert result >= 0.0, f"robust_CV must be non-negative; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"rcv_rt": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]]})
    assert isinstance(get_windowed_tool_latency_robust_cv("rcv_rt", _WIN, store=store, now_ms=_NOW), float)
