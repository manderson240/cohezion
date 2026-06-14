"""Item 1067: get_windowed_global_latency_tail_ratio_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide tail ratio = global_p99 / global_p50.

Pools ALL tool latencies, computes p99/p50 on the pooled distribution.
0.0 for empty pool or p50==0.0. Thin composition: global_p99/global_p50.
Injectable store. Pure function. Fleet dual of item 1066.

PRIMARY DISC.: tool_a=[10,20,30]+tool_b=[40,50,200] -> pooled=[10,20,30,40,50,200] n=6
  p50=idx=0.5*5=2.5 -> 30+0.5*(40-30)=35.0
  p99=idx=0.99*5=4.95 -> 50+0.95*(200-50)=192.5
  pooled tail_ratio = 192.5/35.0 = 5.5
  (PRIMARY DISC.: kills per-tool tail_ratio avg:
     tool_a: p50=20.0,p99=29.8 -> ratio≈1.49
     tool_b: p50=50.0,p99=197.0 -> ratio≈3.94
     avg = (1.49+3.94)/2 ≈ 2.715 != pooled 5.5;
   correct pooled tail_ratio=5.5).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_tail_ratio_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_tail_ratio_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=[10,20,30]+tool_b=[40,50,200] -> pooled tail_ratio=5.5.

    Kills per-tool avg≈2.715.
    Correct: pooled p99=192.5, p50=35.0, ratio=5.5.
    """
    _reset()
    store = _make_store(
        {
            "gtr_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30]],
            "gtr_b": [(_NOW - 10, float(v), True) for v in [40, 50, 200]],
        }
    )
    result = get_windowed_global_latency_tail_ratio_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    expected = 192.5 / 35.0
    assert abs(result - expected) < 1e-9, (
        f"pooled tail_ratio=192.5/35.0={expected:.4f}; kills per-tool avg≈2.715; got {result}"
    )


def test_global_tail_ratio_equal_latencies_returns_one() -> None:
    """All equal across tools -> p99=p50=constant -> tail_ratio=1.0."""
    _reset()
    store = _make_store(
        {
            "gtr_eq_a": [(_NOW - 10, 50.0, True)] * 4,
            "gtr_eq_b": [(_NOW - 10, 50.0, True)] * 4,
        }
    )
    result = get_windowed_global_latency_tail_ratio_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 1.0) < 1e-9, f"all-equal -> tail_ratio=1.0; got {result}"


def test_global_tail_ratio_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_tail_ratio_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_global_tail_ratio_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "gtr_old": [(_NOW - _WIN - 100, 50.0, True)] * 5,
        }
    )
    assert get_windowed_global_latency_tail_ratio_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_global_tail_ratio_non_negative() -> None:
    """tail_ratio >= 1.0 for any distribution (p99 >= p50 for non-negative latencies)."""
    _reset()
    store = _make_store(
        {
            "gtr_pos_a": [(_NOW - 10, float(v), True) for v in [10, 50, 100]],
            "gtr_pos_b": [(_NOW - 10, float(v), True) for v in [200, 500]],
        }
    )
    result = get_windowed_global_latency_tail_ratio_ms(_WIN, store=store, now_ms=_NOW)
    assert result >= 1.0, f"tail_ratio must be >= 1.0 for positive latencies; got {result}"


def test_global_tail_ratio_single_value_per_tool() -> None:
    """Single value per tool: p99=p50=that value -> tail_ratio=1.0."""
    _reset()
    store = _make_store(
        {
            "gtr_sv_a": [(_NOW - 10, 30.0, True)],
            "gtr_sv_b": [(_NOW - 10, 80.0, True)],
        }
    )
    result = get_windowed_global_latency_tail_ratio_ms(_WIN, store=store, now_ms=_NOW)
    # With 2 values sorted=[30, 80]: p50=idx=0.5 -> 30+0.5*(80-30)=55.0; p99=idx=0.99 -> 30+0.99*50=79.5
    # tail_ratio=79.5/55.0
    expected = 79.5 / 55.0
    assert abs(result - expected) < 1e-9, f"two-value tail_ratio={expected:.4f}; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"gtr_rt": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 100]]})
    assert isinstance(
        get_windowed_global_latency_tail_ratio_ms(_WIN, store=store, now_ms=_NOW), float
    )
