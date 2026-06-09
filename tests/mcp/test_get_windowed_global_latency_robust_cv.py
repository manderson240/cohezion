"""Item 1062: get_windowed_global_latency_robust_cv(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide robust coefficient of variation = pooled_IQR / pooled_median.

Fleet dual of per-tool item 1061. 0.0 for n_pooled<4 or pooled_median==0.
Injectable store. Pure function.

PRIMARY DISC.: tool_a=[10,10,10,10]+tool_b=[90,90,90,90]
  -> pooled=[10,10,10,10,90,90,90,90] n=8
  Q1=idx=0.25*7=1.75->10+0.75*(10-10)=10.0
  Q3=idx=0.75*7=5.25->90+0.25*(90-90)=90.0
  median=idx=0.5*7=3.5->(10+90)/2=50.0
  IQR=80, robust_CV=80/50=1.6
  (PRIMARY DISC.: kills per-tool robust_CV avg:
     each all-same -> IQR=0 per tool -> robust_CV=0, avg=0 != pooled 1.6;
   correct pooled robust_CV=1.6).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_robust_cv,
    get_windowed_tool_latency_robust_cv,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_robust_cv_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=[10]*4 + tool_b=[90]*4 -> pooled robust_CV=1.6.

    Kills per-tool robust_CV avg: each all-same -> IQR=0 -> 0.0, avg=0 != 1.6.
    Correct: pooled Q1=10, Q3=90, IQR=80, median=50, robust_CV=1.6.
    """
    _reset()
    store = _make_store({
        "grcv_a": [(_NOW - 10, 10.0, True)] * 4,
        "grcv_b": [(_NOW - 10, 90.0, True)] * 4,
    })
    result = get_windowed_global_latency_robust_cv(_WIN, store=store, now_ms=_NOW)
    per_a = get_windowed_tool_latency_robust_cv("grcv_a", _WIN, store=store, now_ms=_NOW)
    per_b = get_windowed_tool_latency_robust_cv("grcv_b", _WIN, store=store, now_ms=_NOW)
    assert per_a == 0.0 and per_b == 0.0, "per-tool should be 0 (all-same)"
    assert isinstance(result, float)
    assert abs(result - 1.6) < 1e-9, (
        f"pooled robust_CV=1.6; kills per-tool-avg=0.0; got {result}"
    )


def test_global_robust_cv_fewer_than_4_returns_zero() -> None:
    """n_pooled < 4 -> 0.0."""
    _reset()
    store = _make_store({
        "grcv_few": [(_NOW - 10, float(v), True) for v in [10, 50, 100]],
    })
    result = get_windowed_global_latency_robust_cv(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"n=3 < 4 -> 0.0; got {result}"


def test_global_robust_cv_all_equal_returns_zero() -> None:
    """All-equal pooled -> IQR=0 -> robust_CV=0.0."""
    _reset()
    store = _make_store({
        "grcv_eq": [(_NOW - 10, 50.0, True)] * 8,
    })
    result = get_windowed_global_latency_robust_cv(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"all-equal -> robust_CV=0.0; got {result}"


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_robust_cv(_WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "grcv_old": [(_NOW - _WIN - 100, 50.0, True)] * 5,
    })
    assert get_windowed_global_latency_robust_cv(_WIN, store=store, now_ms=_NOW) == 0.0


def test_global_robust_cv_non_negative() -> None:
    """robust_CV >= 0."""
    _reset()
    store = _make_store({
        "grcv_pos": [(_NOW - 10, float(v), True) for v in [10, 50, 100, 500, 1000, 50]],
    })
    result = get_windowed_global_latency_robust_cv(_WIN, store=store, now_ms=_NOW)
    assert result >= 0.0, f"robust_CV must be non-negative; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"grcv_rt": [(_NOW - 10, float(v), True) for v in [10, 10, 10, 10, 90, 90, 90, 90]]})
    assert isinstance(get_windowed_global_latency_robust_cv(_WIN, store=store, now_ms=_NOW), float)
