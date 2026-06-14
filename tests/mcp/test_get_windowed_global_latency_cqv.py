"""Item 1054: get_windowed_global_latency_cqv(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide coefficient of quartile variation (pooled raw values).

CQV = (global_Q3 - global_Q1) / (global_Q3 + global_Q1)
0.0 when denominator == 0 or fewer than 4 pooled samples.
Uses linear interpolation for Q1/Q3. Fleet dual of per-tool item 1053.

PRIMARY DISC.: tool_a=[10,30]+tool_b=[70,90] -> pooled=[10,30,70,90] n=4
  Q1=idx=0.25*3=0.75 -> 10+0.75*20=25.0
  Q3=idx=0.75*3=2.25 -> 70+0.25*20=75.0
  CQV=(75-25)/(75+25)=50/100=0.5
  (PRIMARY DISC.: kills per-tool CQV avg:
     tool_a=(30-10)/(30+10)=0.5, tool_b=(90-70)/(90+70)=0.125, avg=0.3125 ≠ 0.5;
   correct pooled CQV=0.5).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_cqv,
    get_windowed_global_latency_percentile,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_cqv_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=[10,30]+tool_b=[70,90] -> pooled CQV=0.5.

    Kills per-tool CQV avg=(0.5+0.125)/2=0.3125 (NOT pooled).
    Correct: pooled Q1=25, Q3=75, CQV=50/100=0.5.
    """
    _reset()
    store = _make_store(
        {
            "gcqv_a": [(_NOW - 10, 10.0, True), (_NOW - 10, 30.0, True)],
            "gcqv_b": [(_NOW - 10, 70.0, True), (_NOW - 10, 90.0, True)],
        }
    )
    result = get_windowed_global_latency_cqv(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 0.5) < 1e-9, f"pooled CQV=0.5; kills per-tool-avg=0.3125; got {result}"


def test_cqv_equals_q3_minus_q1_over_sum() -> None:
    """CQV == (global_Q3 - global_Q1) / (global_Q3 + global_Q1) (arithmetic identity)."""
    _reset()
    store = _make_store(
        {
            "gcqv_id": [(_NOW - 10, float(v), True) for v in [10, 20, 50, 100, 200]],
        }
    )
    cqv = get_windowed_global_latency_cqv(_WIN, store=store, now_ms=_NOW)
    q1 = get_windowed_global_latency_percentile(25.0, _WIN, store=store, now_ms=_NOW)
    q3 = get_windowed_global_latency_percentile(75.0, _WIN, store=store, now_ms=_NOW)
    if q3 + q1 > 0:
        expected = (q3 - q1) / (q3 + q1)
        assert abs(cqv - expected) < 1e-9, f"CQV={cqv} != (Q3-Q1)/(Q3+Q1)={expected}"


def test_all_equal_pooled_cqv_zero() -> None:
    """All equal pooled latencies -> Q1=Q3 -> CQV=0.0."""
    _reset()
    store = _make_store(
        {
            "gcqv_eq": [(_NOW - 10, 50.0, True)] * 8,
        }
    )
    result = get_windowed_global_latency_cqv(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"all-equal -> CQV=0.0; got {result}"


def test_fewer_than_4_pooled_returns_zero() -> None:
    """Fewer than 4 pooled -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gcqv_few": [(_NOW - 10, float(v), True) for v in [10, 20, 30]],
        }
    )
    result = get_windowed_global_latency_cqv(_WIN, store=store, now_ms=_NOW)
    assert result == 0.0, f"n_pooled=3 < 4 -> CQV=0.0; got {result}"


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_cqv(_WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gcqv_old": [(_NOW - _WIN - 100, 50.0, True)] * 6,
        }
    )
    assert get_windowed_global_latency_cqv(_WIN, store=store, now_ms=_NOW) == 0.0


def test_cqv_non_negative() -> None:
    """CQV >= 0 (Q3 >= Q1 for sorted data)."""
    _reset()
    store = _make_store(
        {
            "gcqv_pos": [(_NOW - 10, float(v), True) for v in [10, 50, 200, 50, 10, 200]],
        }
    )
    result = get_windowed_global_latency_cqv(_WIN, store=store, now_ms=_NOW)
    assert result >= 0.0, f"CQV must be non-negative; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gcqv_rt": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]]})
    assert isinstance(get_windowed_global_latency_cqv(_WIN, store=store, now_ms=_NOW), float)
