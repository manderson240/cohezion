"""Item 969: get_windowed_global_latency_percentile(percentile, window_ms, *, store=None, now_ms=None) -> float
-- arbitrary-percentile of ALL windowed latencies fleet-wide (pooled).

PRIMARY DISC.: tool_a [10,50] + tool_b [20,30], p50 of pooled [10,20,30,50] = 25.0.
Kills impl averaging per-tool p50 values: (30.0+25.0)/2 = 27.5 != 25.0.
empty -> 0.0; returns float.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_latency_percentile,
    get_windowed_latency_percentile,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_pooled_not_averaged_primary_discriminator() -> None:
    """FALSIFIABLE: tool_a [10,50] + tool_b [20,30], p50 of pooled [10,20,30,50] = 25.0.
    Average-of-per-tool impl: (30.0+25.0)/2 = 27.5 (WRONG)."""
    _reset()
    store = _make_store({
        "wglp_a": [(_NOW - 10, 10.0, True), (_NOW - 10, 50.0, True)],
        "wglp_b": [(_NOW - 10, 20.0, True), (_NOW - 10, 30.0, True)],
    })
    result = get_windowed_global_latency_percentile(50.0, _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 25.0) < 0.001   # pooled [10,20,30,50] p50=25.0, NOT avg 27.5


def test_average_of_per_tool_would_differ() -> None:
    """Explicit check that the wrong impl (27.5) would fail this test."""
    store = _make_store({
        "wglp_c": [(_NOW - 10, 10.0, True), (_NOW - 10, 50.0, True)],
        "wglp_d": [(_NOW - 10, 20.0, True), (_NOW - 10, 30.0, True)],
    })
    result = get_windowed_global_latency_percentile(50.0, _WIN, store=store, now_ms=_NOW)
    wrong_avg_impl = 27.5
    assert abs(result - wrong_avg_impl) > 0.1   # must NOT equal the wrong answer


def test_only_windowed_calls_pooled() -> None:
    """Old calls outside window are excluded from pool."""
    _reset()
    store = _make_store({
        "wglp_e": [
            (_NOW - _WIN - 100, 9999.0, True),  # old, excluded
            (_NOW - 10, 5.0, True),              # recent
        ],
        "wglp_f": [(_NOW - 10, 15.0, True)],    # recent
    })
    # Pool = [5.0, 15.0]; p50 of 2 points = 10.0 (interp idx=0.5)
    result = get_windowed_global_latency_percentile(50.0, _WIN, store=store, now_ms=_NOW)
    assert result < 100.0   # 9999.0 excluded; if included p50 would be huge


def test_single_tool_equals_per_tool_function() -> None:
    """Single-tool store: global result equals get_windowed_latency_percentile() result."""
    _reset()
    store = _make_store({
        "wglp_single": [(_NOW - 10, float(v), True) for v in [5, 15, 25, 35, 45]],
    })
    global_val = get_windowed_global_latency_percentile(80.0, _WIN, store=store, now_ms=_NOW)
    per_tool = get_windowed_latency_percentile("wglp_single", 80.0, _WIN, store=store, now_ms=_NOW)
    assert abs(global_val - per_tool) < 0.001


def test_empty_store_returns_zero() -> None:
    """No tools -> 0.0."""
    _reset()
    assert get_windowed_global_latency_percentile(50.0, _WIN, store={}, now_ms=_NOW) == 0.0


def test_all_calls_outside_window_returns_zero() -> None:
    """No recent calls -> 0.0."""
    store = _make_store({
        "wglp_old": [(_NOW - _WIN - 100, 50.0, True)] * 3,
    })
    assert get_windowed_global_latency_percentile(50.0, _WIN, store=store, now_ms=_NOW) == 0.0


def test_returns_float_type() -> None:
    """Return type is float."""
    store = _make_store({"rtype_wglp": [(_NOW - 10, 5.0, True)]})
    assert isinstance(
        get_windowed_global_latency_percentile(50.0, _WIN, store=store, now_ms=_NOW), float
    )
