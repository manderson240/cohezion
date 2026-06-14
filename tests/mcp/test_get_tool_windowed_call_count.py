"""Item 924: get_tool_windowed_call_count(tool_name, window_ms, ...) -> int.

PRIMARY DISC.: 3 recent + 2 old calls -> 3 (kills impl counting all calls);
returns int not float; unknown tool -> 0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_tool_windowed_call_count,
)

NOW = 40_000.0


def _reset():
    clear_telemetry_stores()


def test_window_excludes_old_calls_primary_discriminator() -> None:
    """FALSIFIABLE: 3 recent + 2 old -> count=3.
    Kills impl that counts all calls (ignoring window)."""
    _reset()
    store: dict = {
        "cnt_tool": [
            (NOW - 500, 10.0, True),  # in window
            (NOW - 300, 10.0, True),  # in window
            (NOW - 100, 10.0, True),  # in window
            (NOW - 5000, 10.0, True),  # outside 2000ms window
            (NOW - 8000, 10.0, True),  # outside 2000ms window
        ]
    }
    result = get_tool_windowed_call_count("cnt_tool", window_ms=2000.0, store=store, now_ms=NOW)
    assert result == 3


def test_returns_int_not_float() -> None:
    """Return type must be int."""
    _reset()
    store: dict = {"typed": [(NOW - 100, 10.0, True)]}
    result = get_tool_windowed_call_count("typed", window_ms=5000.0, store=store, now_ms=NOW)
    assert isinstance(result, int)


def test_unknown_tool_returns_zero_int() -> None:
    _reset()
    store: dict = {}
    result = get_tool_windowed_call_count("unknown", window_ms=5000.0, store=store, now_ms=NOW)
    assert result == 0
    assert isinstance(result, int)


def test_all_calls_outside_window_returns_zero() -> None:
    _reset()
    store: dict = {"stale": [(NOW - 99000, 10.0, True), (NOW - 50000, 10.0, False)]}
    result = get_tool_windowed_call_count("stale", window_ms=1000.0, store=store, now_ms=NOW)
    assert result == 0


def test_all_calls_in_window_counted() -> None:
    _reset()
    store: dict = {"fresh": [(NOW - i * 100, 5.0, True) for i in range(1, 6)]}
    result = get_tool_windowed_call_count("fresh", window_ms=5000.0, store=store, now_ms=NOW)
    assert result == 5
