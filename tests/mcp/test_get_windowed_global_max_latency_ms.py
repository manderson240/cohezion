"""Item 980: get_windowed_global_max_latency_ms(window_ms, *, store=None, now_ms=None) -> float
-- global maximum latency fleet-wide in window.

PRIMARY DISC.: tool_a [10, 30] + tool_b [50, 20] -> global_max=50.0
(not min=10.0, not mean=27.5; not per-tool max of tool_a alone=30.0).
empty -> 0.0; single tool = per-tool max; returns float.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_max_latency_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_global_max_primary_discriminator() -> None:
    """FALSIFIABLE: tool_a [10,30] + tool_b [50,20] -> global_max=50.0 (not min=10, not mean=27.5)."""
    _reset()
    store = _make_store({
        "gmax_a": [(_NOW - 10, 10.0, True), (_NOW - 10, 30.0, True)],
        "gmax_b": [(_NOW - 10, 50.0, True), (_NOW - 10, 20.0, True)],
    })
    result = get_windowed_global_max_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 50.0) < 0.001   # not 10.0 (min), not 27.5 (mean), not 30.0 (tool_a max only)


def test_cross_tool_max() -> None:
    """The global max comes from the tool with the highest latency, not tool_a."""
    store = _make_store({
        "gmax_x": [(_NOW - 10, 30.0, True)],   # tool_a max = 30
        "gmax_y": [(_NOW - 10, 80.0, True)],   # tool_b max = 80 (the winner)
    })
    result = get_windowed_global_max_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 80.0) < 0.001


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    _reset()
    assert get_windowed_global_max_latency_ms(_WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    store = _make_store({
        "gmax_old": [(_NOW - _WIN - 100, 9999.0, True)],
    })
    assert get_windowed_global_max_latency_ms(_WIN, store=store, now_ms=_NOW) == 0.0


def test_old_extreme_excluded() -> None:
    """Old extreme latency excluded; max computed from windowed calls only."""
    store = _make_store({
        "gmax_mix": [
            (_NOW - _WIN - 100, 9999.0, True),   # old high, excluded
            (_NOW - 10, 20.0, True),
            (_NOW - 10, 30.0, True),
        ]
    })
    result = get_windowed_global_max_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(result - 30.0) < 0.001   # 9999 excluded; max of [20, 30] = 30.0


def test_single_tool_equals_per_tool_max() -> None:
    """With a single tool, global max == per-tool max."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_max_latency_ms
    store = _make_store({
        "gmax_single": [(_NOW - 10, float(v), True) for v in [10, 50, 20, 40, 30]],
    })
    per_tool = get_windowed_tool_max_latency_ms("gmax_single", _WIN, store=store, now_ms=_NOW)
    global_max = get_windowed_global_max_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert abs(per_tool - global_max) < 0.001


def test_global_max_ge_global_min() -> None:
    """global_max >= global_min for any non-empty window."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_global_min_latency_ms
    store = _make_store({
        "gmax_mn": [(_NOW - 10, float(v), True) for v in [5, 25, 45, 15, 35]],
    })
    mn = get_windowed_global_min_latency_ms(_WIN, store=store, now_ms=_NOW)
    mx = get_windowed_global_max_latency_ms(_WIN, store=store, now_ms=_NOW)
    assert mx >= mn
    assert abs(mn - 5.0) < 0.001
    assert abs(mx - 45.0) < 0.001


def test_returns_float_type() -> None:
    """Return type is float."""
    store = _make_store({"rtype_gmax": [(_NOW - 10, 7.0, True)]})
    assert isinstance(get_windowed_global_max_latency_ms(_WIN, store=store, now_ms=_NOW), float)
