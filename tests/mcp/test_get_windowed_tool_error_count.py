"""Item 972: get_windowed_tool_error_count(tool_name, window_ms, *, store=None, now_ms=None) -> int
-- count of failed calls in window for a single tool (dual of item-970 success count).

PRIMARY DISC.: 5 calls with 2 failures -> error_count=2 (not 5, not 3, not 0.4).
Kills impl returning call_count=5.
Kills impl returning success_count=3.
Kills impl returning error_rate=0.4 (float, wrong type).
returns int not float; unknown -> 0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_error_count,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_error_count_primary_discriminator() -> None:
    """FALSIFIABLE: 5 calls 2 failures -> error_count=2 (not 5, not 3, not 0.4)."""
    _reset()
    store = _make_store(
        {
            "wec_a": [
                *[(_NOW - 10, 5.0, True)] * 3,
                *[(_NOW - 10, 5.0, False)] * 2,
            ]
        }
    )
    result = get_windowed_tool_error_count("wec_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 2  # not 5 (total), not 3 (successes), not 0.4 (rate)


def test_returns_int_not_float() -> None:
    """Return type must be int, not float."""
    store = _make_store({"int_wec": [(_NOW - 10, 5.0, False)] * 2 + [(_NOW - 10, 5.0, True)] * 3})
    result = get_windowed_tool_error_count("int_wec", _WIN, store=store, now_ms=_NOW)
    assert type(result) is int  # strict type check


def test_all_successful_returns_zero() -> None:
    """All calls succeed -> error_count=0."""
    store = _make_store({"wec_ok": [(_NOW - 10, 5.0, True)] * 5})
    assert get_windowed_tool_error_count("wec_ok", _WIN, store=store, now_ms=_NOW) == 0


def test_all_failures_returns_total() -> None:
    """All calls fail -> error_count == call_count."""
    store = _make_store({"wec_all_fail": [(_NOW - 10, 5.0, False)] * 6})
    assert get_windowed_tool_error_count("wec_all_fail", _WIN, store=store, now_ms=_NOW) == 6


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0."""
    _reset()
    assert get_windowed_tool_error_count("no_such_wec", _WIN, store={}, now_ms=_NOW) == 0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0."""
    store = _make_store(
        {
            "wec_old": [(_NOW - _WIN - 100, 5.0, False)] * 3,
        }
    )
    assert get_windowed_tool_error_count("wec_old", _WIN, store=store, now_ms=_NOW) == 0


def test_consistent_with_windowed_tool_telemetry_full() -> None:
    """error_count == get_windowed_tool_telemetry_full()['error_count']."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_telemetry_full

    _reset()
    store = _make_store(
        {
            "wec_consist": [(_NOW - 10, 5.0, True)] * 4 + [(_NOW - 10, 5.0, False)] * 3,
        }
    )
    ec = get_windowed_tool_error_count("wec_consist", _WIN, store=store, now_ms=_NOW)
    full = get_windowed_tool_telemetry_full("wec_consist", _WIN, store=store, now_ms=_NOW)
    assert ec == full["error_count"]
    assert ec == 3
