"""Item 976: get_windowed_tool_latency_range_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- latency range (max - min) in window for a single tool.

PRIMARY DISC.: lats [50, 10, 30] -> range=40.0 (50-10).
Kills impl returning max=50.0 alone or min=10.0 alone or mean=30.0.
single call -> 0.0; all same -> 0.0; unknown -> 0.0; returns float.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_latency_range_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_range_primary_discriminator() -> None:
    """FALSIFIABLE: lats [50, 10, 30] -> range=40.0 (not 50.0, not 10.0, not 30.0)."""
    _reset()
    store = _make_store(
        {
            "wrange_a": [
                (_NOW - 10, 50.0, True),
                (_NOW - 10, 10.0, True),
                (_NOW - 10, 30.0, True),
            ]
        }
    )
    result = get_windowed_tool_latency_range_ms("wrange_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 40.0) < 0.001  # max(50)-min(10)=40; not 50.0, not 10.0, not 30.0


def test_single_call_returns_zero() -> None:
    """Single call -> range is 0.0 (max == min)."""
    store = _make_store({"wrange_single": [(_NOW - 10, 42.0, True)]})
    assert (
        abs(get_windowed_tool_latency_range_ms("wrange_single", _WIN, store=store, now_ms=_NOW))
        < 0.001
    )


def test_all_same_returns_zero() -> None:
    """All same latency -> range is 0.0."""
    store = _make_store({"wrange_same": [(_NOW - 10, 15.0, True)] * 5})
    assert (
        abs(get_windowed_tool_latency_range_ms("wrange_same", _WIN, store=store, now_ms=_NOW))
        < 0.001
    )


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_latency_range_ms("no_such_wrange", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    store = _make_store(
        {
            "wrange_old": [(_NOW - _WIN - 100, 50.0, True)] * 3,
        }
    )
    assert get_windowed_tool_latency_range_ms("wrange_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_old_extreme_excluded() -> None:
    """Old extreme latency excluded; range computed from windowed calls only."""
    store = _make_store(
        {
            "wrange_mix": [
                (_NOW - _WIN - 100, 9999.0, True),  # old high, excluded
                (_NOW - 10, 10.0, True),
                (_NOW - 10, 20.0, True),
            ]
        }
    )
    result = get_windowed_tool_latency_range_ms("wrange_mix", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 10.0) < 0.001  # max(20)-min(10)=10, not 9999-10


def test_range_equals_max_minus_min() -> None:
    """range = max - min is the definitional relationship."""
    from cohezion.mcp.compound_mcp_telemetry import (
        get_windowed_tool_max_latency_ms,
        get_windowed_tool_min_latency_ms,
    )

    store = _make_store(
        {
            "wrange_def": [(_NOW - 10, float(v), True) for v in [5, 25, 45, 15, 35]],
        }
    )
    mn = get_windowed_tool_min_latency_ms("wrange_def", _WIN, store=store, now_ms=_NOW)
    mx = get_windowed_tool_max_latency_ms("wrange_def", _WIN, store=store, now_ms=_NOW)
    rng = get_windowed_tool_latency_range_ms("wrange_def", _WIN, store=store, now_ms=_NOW)
    assert abs(rng - (mx - mn)) < 0.001


def test_returns_float_type() -> None:
    """Return type is float."""
    store = _make_store({"rtype_wrange": [(_NOW - 10, 5.0, True), (_NOW - 10, 10.0, True)]})
    assert isinstance(
        get_windowed_tool_latency_range_ms("rtype_wrange", _WIN, store=store, now_ms=_NOW), float
    )
