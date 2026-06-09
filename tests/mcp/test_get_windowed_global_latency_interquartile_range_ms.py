"""Item 1069: get_windowed_global_latency_interquartile_range_ms(window_ms, *, store=None, now_ms=None) -> float
-- fleet-wide IQR = pooled_Q3 - pooled_Q1.

Pools ALL tool latencies, computes Q3-Q1 on the pooled distribution.
0.0 for empty pool. Thin composition via get_windowed_global_latency_percentile.
Injectable store. Pure function. Fleet dual of item 1068.

PRIMARY DISC.: tool_a=[10,20,30,40,50]+tool_b=[100,200,300] -> pooled n=8
  Q1=idx=0.25*7=1.75 -> 20+0.75*(30-20)=27.5
  Q3=idx=0.75*7=5.25 -> 100+0.25*(200-100)=125.0
  pooled IQR = 125.0 - 27.5 = 97.5
  (PRIMARY DISC.: kills per-tool avg:
     tool_a IQR=Q3(40)-Q1(20)=20, tool_b IQR=Q3(250)-Q1(150)=100, avg=60 != pooled 97.5;
   correct pooled IQR=97.5).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_interquartile_range_ms,
    get_windowed_tool_latency_interquartile_range_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_iqr_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a=[10..50]+tool_b=[100,200,300] -> pooled IQR=97.5.

    Kills per-tool avg: tool_a IQR=20, tool_b IQR=100, avg=60 != 97.5.
    Correct: pooled Q3=125.0, Q1=27.5, IQR=97.5.
    """
    _reset()
    store = _make_store({
        "giqr_a": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]],
        "giqr_b": [(_NOW - 10, float(v), True) for v in [100, 200, 300]],
    })
    result = get_windowed_global_latency_interquartile_range_ms(_WIN, store=store, now_ms=_NOW)
    per_a = get_windowed_tool_latency_interquartile_range_ms("giqr_a", _WIN, store=store, now_ms=_NOW)
    per_b = get_windowed_tool_latency_interquartile_range_ms("giqr_b", _WIN, store=store, now_ms=_NOW)
    assert abs((per_a + per_b) / 2 - 60.0) < 1e-9, f"per-tool avg should be 60.0; got {(per_a+per_b)/2}"
    assert isinstance(result, float)
    assert abs(result - 97.5) < 1e-9, (
        f"pooled IQR=97.5; kills per-tool avg=60; got {result}"
    )


def test_global_iqr_all_equal_returns_zero() -> None:
    """All equal across tools -> Q1=Q3=constant -> IQR=0.0."""
    _reset()
    store = _make_store({
        "giqr_eq_a": [(_NOW - 10, 50.0, True)] * 4,
        "giqr_eq_b": [(_NOW - 10, 50.0, True)] * 4,
    })
    result = get_windowed_global_latency_interquartile_range_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 0.0) < 1e-9, f"all-equal -> IQR=0.0; got {result}"


def test_global_iqr_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_interquartile_range_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_global_iqr_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store({
        "giqr_old": [(_NOW - _WIN - 100, float(v), True) for v in [10, 20, 30, 40, 50]],
    })
    assert get_windowed_global_latency_interquartile_range_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_global_iqr_non_negative() -> None:
    """IQR >= 0 always (Q3 >= Q1 for sorted data)."""
    _reset()
    store = _make_store({
        "giqr_pos_a": [(_NOW - 10, float(v), True) for v in [10, 50, 100]],
        "giqr_pos_b": [(_NOW - 10, float(v), True) for v in [200, 500]],
    })
    result = get_windowed_global_latency_interquartile_range_ms(_WIN, store=store, now_ms=_NOW)
    assert result >= 0.0, f"IQR must be non-negative; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store({"giqr_rt": [(_NOW - 10, float(v), True) for v in [10, 20, 30, 40, 50]]})
    assert isinstance(
        get_windowed_global_latency_interquartile_range_ms(_WIN, store=store, now_ms=_NOW), float
    )
