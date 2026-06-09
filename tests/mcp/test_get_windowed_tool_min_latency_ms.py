"""Item 974: get_windowed_tool_min_latency_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- minimum latency in window for a single tool.

PRIMARY DISC.: lats [50, 10, 30] -> min=10.0 (not p50=30.0, not max=50.0, not mean=30.0).
unknown -> 0.0; all same -> that value; returns float.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_min_latency_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_min_not_p50_not_max_primary_discriminator() -> None:
    """FALSIFIABLE: lats [50, 10, 30] -> min=10.0 (not p50=30.0, not max=50.0, not mean=30.0)."""
    _reset()
    store = _make_store({
        "wmin_a": [
            (_NOW - 10, 50.0, True),
            (_NOW - 10, 10.0, True),
            (_NOW - 10, 30.0, True),
        ]
    })
    result = get_windowed_tool_min_latency_ms("wmin_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 10.0) < 0.001   # not 30.0 (p50/mean), not 50.0 (max)


def test_only_windowed_calls() -> None:
    """Old calls outside window excluded from min calculation."""
    store = _make_store({
        "wmin_b": [
            (_NOW - _WIN - 100, 1.0, True),   # old, excluded
            (_NOW - 10, 20.0, True),           # recent
            (_NOW - 10, 30.0, True),           # recent
        ]
    })
    result = get_windowed_tool_min_latency_ms("wmin_b", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 20.0) < 0.001   # 1.0 excluded; min of [20, 30] = 20.0


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_min_latency_ms("no_such_wmin", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    store = _make_store({
        "wmin_old": [(_NOW - _WIN - 100, 5.0, True)] * 3,
    })
    assert get_windowed_tool_min_latency_ms("wmin_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_single_call_returns_that_latency() -> None:
    """Single call -> min == that call's latency."""
    store = _make_store({"wmin_single": [(_NOW - 10, 42.0, True)]})
    assert abs(get_windowed_tool_min_latency_ms("wmin_single", _WIN, store=store, now_ms=_NOW) - 42.0) < 0.001


def test_all_same_latency() -> None:
    """All same latency -> min == that value."""
    store = _make_store({"wmin_same": [(_NOW - 10, 15.0, True)] * 5})
    assert abs(get_windowed_tool_min_latency_ms("wmin_same", _WIN, store=store, now_ms=_NOW) - 15.0) < 0.001


def test_returns_float_type() -> None:
    """Return type is float."""
    store = _make_store({"rtype_wmin": [(_NOW - 10, 5.0, True)]})
    assert isinstance(get_windowed_tool_min_latency_ms("rtype_wmin", _WIN, store=store, now_ms=_NOW), float)


def test_failures_still_counted_for_latency() -> None:
    """Failed calls contribute their latency to the min (latency is measured regardless of outcome)."""
    store = _make_store({
        "wmin_mix": [
            (_NOW - 10, 100.0, True),   # success, high latency
            (_NOW - 10, 5.0, False),    # failure, low latency
        ]
    })
    result = get_windowed_tool_min_latency_ms("wmin_mix", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 5.0) < 0.001   # failure's latency is still the minimum
