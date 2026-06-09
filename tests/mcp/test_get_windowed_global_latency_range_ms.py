"""Item 981: get_windowed_global_latency_range_ms(window_ms, *, store=None, now_ms=None) -> float
-- global latency range (global_max - global_min) fleet-wide in window.

PRIMARY DISC.: tool_a [10, 50] + tool_b [20, 90]
  -> global_range = 90 - 10 = 80.0
  (not max_per_tool_range: max(50-10, 90-20)=70.0; not max=90.0 alone; not mean=42.5)
single call fleet-wide -> 0.0; all-same -> 0.0; empty -> 0.0; returns float.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_range_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_range_primary_discriminator() -> None:
    """FALSIFIABLE: tool_a [10,50] + tool_b [20,90] -> range=80.0 (not per-tool range max=70.0)."""
    _reset()
    store = _make_store({
        "gr_a": [(_NOW - 10, 10.0, True), (_NOW - 10, 50.0, True)],
        "gr_b": [(_NOW - 10, 20.0, True), (_NOW - 10, 90.0, True)],
    })
    result = get_windowed_global_latency_range_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    # global_max=90, global_min=10, range=80.0
    # NOT max per-tool range: max(50-10, 90-20) = max(40, 70) = 70.0
    assert abs(result - 80.0) < 0.001   # not 70.0 (per-tool range max), not 90.0 alone


def test_single_fleet_call_returns_zero() -> None:
    """Single call across entire fleet -> range 0.0 (max == min)."""
    store = _make_store({"gr_single": [(_NOW - 10, 42.0, True)]})
    assert abs(get_windowed_global_latency_range_ms(_WIN, store=store, now_ms=_NOW)) < 0.001


def test_all_same_latency_returns_zero() -> None:
    """All calls same latency (across tools) -> 0.0."""
    store = _make_store({
        "gr_s1": [(_NOW - 10, 15.0, True)] * 3,
        "gr_s2": [(_NOW - 10, 15.0, True)] * 2,
    })
    assert abs(get_windowed_global_latency_range_ms(_WIN, store=store, now_ms=_NOW)) < 0.001


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_latency_range_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    store = _make_store({
        "gr_old": [(_NOW - _WIN - 100, 9999.0, True)] * 3,
    })
    assert get_windowed_global_latency_range_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_old_extreme_excluded() -> None:
    """Old extreme latency excluded; range computed from windowed calls only."""
    store = _make_store({
        "gr_mix": [
            (_NOW - _WIN - 100, 9999.0, True),   # old high, excluded
            (_NOW - _WIN - 100, 1.0, True),       # old low, excluded
            (_NOW - 10, 20.0, True),
            (_NOW - 10, 40.0, True),
        ]
    })
    result = get_windowed_global_latency_range_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 20.0) < 0.001   # 40-20=20; not 9999-1=9998


def test_equals_global_max_minus_global_min() -> None:
    """range == global_max - global_min definitional check."""
    from cohezion.mcp.compound_mcp_telemetry import (
        get_windowed_global_max_latency_ms,
        get_windowed_global_min_latency_ms,
    )
    store = _make_store({
        "gr_def1": [(_NOW - 10, float(v), True) for v in [5, 35, 25]],
        "gr_def2": [(_NOW - 10, float(v), True) for v in [15, 45, 55]],
    })
    mn = get_windowed_global_min_latency_ms(_WIN, store=store, now_ms=_NOW)
    mx = get_windowed_global_max_latency_ms(_WIN, store=store, now_ms=_NOW)
    rng = get_windowed_global_latency_range_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(rng - (mx - mn)) < 0.001


def test_returns_float_type() -> None:
    """Return type is float."""
    store = _make_store({"rtype_gr": [(_NOW - 10, 5.0, True), (_NOW - 10, 15.0, True)]})
    assert isinstance(get_windowed_global_latency_range_ms(_WIN, store=store, now_ms=_NOW), float)
