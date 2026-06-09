"""Item 954: get_windowed_global_call_count(window_ms, *, store=None, now_ms=None) -> int
-- total call count across all tools in the recent window.

PRIMARY DISC.: 3 tools with [2, 3, 1] recent calls -> 6 total.
Kills impl returning tool count=3 or most-active tool count=3.
empty -> 0; returns int not float.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_global_call_count,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_three_tools_total_not_tool_count_primary_discriminator() -> None:
    """FALSIFIABLE: 3 tools with [2, 3, 1] recent calls -> total=6.
    Kills impl returning tool_count=3 or max_calls=3."""
    _reset()
    store = _make_store({
        "wgc_a": [(_NOW - 10, 5.0, True)] * 2,
        "wgc_b": [(_NOW - 10, 5.0, True)] * 3,
        "wgc_c": [(_NOW - 10, 5.0, True)] * 1,
    })
    result = get_windowed_global_call_count(_WIN, store=store, now_ms=_NOW)
    assert result == 6         # total calls, not tool count or max
    assert result != 3         # NOT tool count
    assert isinstance(result, int)


def test_empty_store_returns_zero() -> None:
    """No windowed calls -> 0."""
    _reset()
    assert get_windowed_global_call_count(_WIN, store={}, now_ms=_NOW) == 0


def test_returns_int_not_float() -> None:
    """Return type is int."""
    store = _make_store({"int_wgc": [(_NOW - 1, 5.0, True)]})
    result = get_windowed_global_call_count(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, int)


def test_calls_outside_window_excluded() -> None:
    """Calls older than window_ms are excluded from count."""
    store = _make_store({
        "wgc_mix": [
            (_NOW - _WIN - 1, 5.0, True),   # outside window
            (_NOW - _WIN - 1, 5.0, True),   # outside window
            (_NOW - 10, 5.0, True),          # inside window
        ]
    })
    result = get_windowed_global_call_count(_WIN, store=store, now_ms=_NOW)
    assert result == 1


def test_all_calls_outside_window_returns_zero() -> None:
    """All calls outside window -> 0."""
    store = _make_store({
        "wgc_old": [(_NOW - _WIN - 100, 5.0, True)],
    })
    assert get_windowed_global_call_count(_WIN, store=store, now_ms=_NOW) == 0


def test_single_tool_consistent_with_windowed_call_count() -> None:
    """Single tool: global windowed count equals per-tool windowed call count."""
    from cohezion.mcp.compound_mcp_telemetry import get_tool_windowed_call_count
    store = _make_store({
        "consist_wgc": [(_NOW - 10, 5.0, True)] * 4
    })
    global_count = get_windowed_global_call_count(_WIN, store=store, now_ms=_NOW)
    tool_count = get_tool_windowed_call_count("consist_wgc", _WIN, store=store, now_ms=_NOW)
    assert global_count == tool_count == 4


def test_errors_and_successes_both_counted() -> None:
    """Both successful and failed calls count toward total."""
    store = _make_store({
        "wgc_errs": [
            (_NOW - 10, 5.0, True),
            (_NOW - 10, 5.0, False),
            (_NOW - 10, 5.0, False),
        ]
    })
    result = get_windowed_global_call_count(_WIN, store=store, now_ms=_NOW)
    assert result == 3
