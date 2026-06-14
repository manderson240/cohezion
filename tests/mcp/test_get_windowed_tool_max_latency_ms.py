"""Item 975: get_windowed_tool_max_latency_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float
-- maximum latency in window for a single tool (dual of item-974 min).

PRIMARY DISC.: lats [50, 10, 30] -> max=50.0 (not min=10.0, not p50=30.0, not mean=30.0).
failed calls included in max; unknown -> 0.0; returns float.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_max_latency_ms,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_max_not_min_not_p50_primary_discriminator() -> None:
    """FALSIFIABLE: lats [50, 10, 30] -> max=50.0 (not 10.0, not 30.0)."""
    _reset()
    store = _make_store(
        {
            "wmax_a": [
                (_NOW - 10, 50.0, True),
                (_NOW - 10, 10.0, True),
                (_NOW - 10, 30.0, True),
            ]
        }
    )
    result = get_windowed_tool_max_latency_ms("wmax_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, float)
    assert abs(result - 50.0) < 0.001  # not 10.0 (min), not 30.0 (p50/mean)


def test_only_windowed_calls() -> None:
    """Old calls outside window excluded from max calculation."""
    store = _make_store(
        {
            "wmax_b": [
                (_NOW - _WIN - 100, 9999.0, True),  # old, excluded
                (_NOW - 10, 20.0, True),  # recent
                (_NOW - 10, 30.0, True),  # recent
            ]
        }
    )
    result = get_windowed_tool_max_latency_ms("wmax_b", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 30.0) < 0.001  # 9999 excluded; max of [20, 30] = 30.0


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_windowed_tool_max_latency_ms("no_such_wmax", _WIN, store={}, now_ms=_NOW) == 0.0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    store = _make_store(
        {
            "wmax_old": [(_NOW - _WIN - 100, 5.0, True)] * 3,
        }
    )
    assert get_windowed_tool_max_latency_ms("wmax_old", _WIN, store=store, now_ms=_NOW) == 0.0


def test_failures_included_in_max() -> None:
    """Failed calls contribute their latency to the max."""
    store = _make_store(
        {
            "wmax_mix": [
                (_NOW - 10, 5.0, True),  # success, low latency
                (_NOW - 10, 100.0, False),  # failure, high latency
            ]
        }
    )
    result = get_windowed_tool_max_latency_ms("wmax_mix", _WIN, store=store, now_ms=_NOW)
    assert abs(result - 100.0) < 0.001  # failure's latency is the maximum


def test_max_vs_min_dual() -> None:
    """max >= min for any non-empty window."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_min_latency_ms

    store = _make_store(
        {
            "wmax_dual": [(_NOW - 10, float(v), True) for v in [5, 25, 45, 15, 35]],
        }
    )
    mn = get_windowed_tool_min_latency_ms("wmax_dual", _WIN, store=store, now_ms=_NOW)
    mx = get_windowed_tool_max_latency_ms("wmax_dual", _WIN, store=store, now_ms=_NOW)
    assert mx >= mn
    assert abs(mn - 5.0) < 0.001
    assert abs(mx - 45.0) < 0.001


def test_returns_float_type() -> None:
    """Return type is float."""
    store = _make_store({"rtype_wmax": [(_NOW - 10, 5.0, True)]})
    assert isinstance(
        get_windowed_tool_max_latency_ms("rtype_wmax", _WIN, store=store, now_ms=_NOW), float
    )
