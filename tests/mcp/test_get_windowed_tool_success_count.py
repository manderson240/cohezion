"""Item 970: get_windowed_tool_success_count(tool_name, window_ms, *, store=None, now_ms=None) -> int
-- count of successful calls in window for a single tool.

PRIMARY DISC.: 5 calls with 2 failures -> success_count=3 (not 5, not 2, not 0.6).
Kills impl returning total call_count=5.
Kills impl returning error_count=2.
Kills impl returning success_rate=0.6 (float not int).
returns int; unknown -> 0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_success_count,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_success_count_primary_discriminator() -> None:
    """FALSIFIABLE: 5 calls 2 failures -> success_count=3 (not 5, not 2, not 0.6)."""
    _reset()
    store = _make_store(
        {
            "wsc_a": [
                *[(_NOW - 10, 5.0, True)] * 3,
                *[(_NOW - 10, 5.0, False)] * 2,
            ]
        }
    )
    result = get_windowed_tool_success_count("wsc_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 3  # not 5 (total), not 2 (errors), not 0.6 (rate)


def test_returns_int_not_float() -> None:
    """Return type must be int, not float."""
    store = _make_store({"int_wsc": [(_NOW - 10, 5.0, True)] * 3 + [(_NOW - 10, 5.0, False)]})
    result = get_windowed_tool_success_count("int_wsc", _WIN, store=store, now_ms=_NOW)
    assert type(result) is int  # strict type check (not just isinstance)


def test_all_successful() -> None:
    """All calls succeed -> success_count == call_count."""
    store = _make_store({"wsc_ok": [(_NOW - 10, 5.0, True)] * 6})
    assert get_windowed_tool_success_count("wsc_ok", _WIN, store=store, now_ms=_NOW) == 6


def test_all_failures() -> None:
    """All calls fail -> success_count == 0."""
    store = _make_store({"wsc_fail": [(_NOW - 10, 5.0, False)] * 4})
    assert get_windowed_tool_success_count("wsc_fail", _WIN, store=store, now_ms=_NOW) == 0


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0."""
    _reset()
    assert get_windowed_tool_success_count("no_such_wsc", _WIN, store={}, now_ms=_NOW) == 0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0."""
    store = _make_store(
        {
            "wsc_old": [(_NOW - _WIN - 100, 5.0, True)] * 5,
        }
    )
    assert get_windowed_tool_success_count("wsc_old", _WIN, store=store, now_ms=_NOW) == 0


def test_only_windowed_successes_counted() -> None:
    """Old successes outside window don't count."""
    store = _make_store(
        {
            "wsc_mix": [
                (_NOW - _WIN - 100, 5.0, True),  # old success, excluded
                (_NOW - 10, 5.0, True),  # recent success, counted
                (_NOW - 10, 5.0, False),  # recent failure, not counted
            ],
        }
    )
    result = get_windowed_tool_success_count("wsc_mix", _WIN, store=store, now_ms=_NOW)
    assert result == 1  # only 1 recent success


def test_consistent_with_windowed_tool_telemetry_full() -> None:
    """success_count == call_count - error_count from get_windowed_tool_telemetry_full."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_telemetry_full

    _reset()
    store = _make_store(
        {
            "wsc_consist": [(_NOW - 10, 5.0, True)] * 4 + [(_NOW - 10, 5.0, False)] * 2,
        }
    )
    success_count = get_windowed_tool_success_count("wsc_consist", _WIN, store=store, now_ms=_NOW)
    full = get_windowed_tool_telemetry_full("wsc_consist", _WIN, store=store, now_ms=_NOW)
    expected = full["call_count"] - full["error_count"]
    assert success_count == expected
