"""Item 1126: get_windowed_tool_latency_percentile_gap_ms(tool_name, window_ms, p_low, p_high, *, store=None, now_ms=None) -> float
-- gap between two percentiles using nearest-rank: P(p_high) - P(p_low).
0.0 for empty window. Returns float.

PRIMARY DISC.: lats=[10..100] (10 values), p_low=10, p_high=90
  nearest-rank P10=10ms (rank=ceil(10/100*10)=1, idx=0)
  nearest-rank P90=90ms (rank=ceil(90/100*10)=9, idx=8)
  gap = 90-10 = 80ms
  (PRIMARY DISC.: kills linear-interp gap=(86.5-14.5)=72ms;
   kills IQR at p=25/75 gap=(80-20)=60ms (wrong percentiles);
   correct: nearest-rank both, subtract, return float=80ms).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_percentile_gap_ms,
)

_NOW = 1_000_000.0
_WIN = 1000.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_percentile_gap_primary_discriminator() -> None:
    """PRIMARY DISC.: P90-P10 nearest-rank=80ms; kills linear-interp gap=72ms."""
    _reset()
    store = _make_store(
        {
            "pg_disc": [
                (_NOW - float(1000 - 100 * i), float(10 * (i + 1)), True)
                for i in range(10)  # lats = [10,20,30,40,50,60,70,80,90,100]
            ],
        }
    )
    result = get_windowed_tool_latency_percentile_gap_ms(
        "pg_disc", _WIN, 10.0, 90.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
    assert abs(result - 80.0) < 1e-9, (
        f"P90(90ms)-P10(10ms)=80ms nearest-rank; kills linear-interp=72ms; got {result}"
    )


def test_percentile_gap_iqr_is_special_case() -> None:
    """IQR = P75-P25, consistent with get_windowed_tool_latency_iqr_ms."""
    _reset()
    store = _make_store(
        {
            "pg_iqr": [
                (_NOW - float(1000 - 100 * i), float(10 * (i + 1)), True)
                for i in range(10)  # lats=[10,20,...,100]
            ],
        }
    )
    # P25: rank=ceil(25/100*10)=3, idx=2, lat=30
    # P75: rank=ceil(75/100*10)=8, idx=7, lat=80
    result = get_windowed_tool_latency_percentile_gap_ms(
        "pg_iqr", _WIN, 25.0, 75.0, store=store, now_ms=_NOW
    )
    assert abs(result - 50.0) < 1e-9, f"P75(80)-P25(30)=50ms; got {result}"


def test_percentile_gap_same_percentile_returns_zero() -> None:
    """p_low == p_high -> gap = 0.0."""
    _reset()
    store = _make_store(
        {
            "pg_same": [(_NOW - float(d), float(d), True) for d in [100, 200, 300, 400, 500]],
        }
    )
    result = get_windowed_tool_latency_percentile_gap_ms(
        "pg_same", _WIN, 50.0, 50.0, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9, f"p_low==p_high -> 0.0; got {result}"


def test_percentile_gap_empty_window_returns_zero() -> None:
    """Empty window -> 0.0."""
    _reset()
    assert (
        get_windowed_tool_latency_percentile_gap_ms(
            "no_tool", _WIN, 25.0, 75.0, store={}, now_ms=_NOW
        )
        == 0.0
    )


def test_percentile_gap_outside_window_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    _reset()
    store = _make_store(
        {
            "pg_old": [(_NOW - _WIN - float(d), 50.0, True) for d in [300, 200, 100]],
        }
    )
    assert (
        get_windowed_tool_latency_percentile_gap_ms(
            "pg_old", _WIN, 25.0, 75.0, store=store, now_ms=_NOW
        )
        == 0.0
    )


def test_percentile_gap_all_same_latency() -> None:
    """All latencies equal -> gap = 0.0."""
    _reset()
    store = _make_store(
        {
            "pg_flat": [(_NOW - float(d), 42.0, True) for d in [400, 300, 200, 100]],
        }
    )
    result = get_windowed_tool_latency_percentile_gap_ms(
        "pg_flat", _WIN, 10.0, 90.0, store=store, now_ms=_NOW
    )
    assert abs(result) < 1e-9, f"all same lat -> gap=0.0; got {result}"


def test_returns_float_type() -> None:
    """Return type is float."""
    _reset()
    store = _make_store(
        {
            "pg_rt": [(_NOW - float(d), float(d), True) for d in [100, 200, 300, 400, 500]],
        }
    )
    result = get_windowed_tool_latency_percentile_gap_ms(
        "pg_rt", _WIN, 20.0, 80.0, store=store, now_ms=_NOW
    )
    assert isinstance(result, float)
