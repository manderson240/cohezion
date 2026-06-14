"""Item 982: get_windowed_tool_call_count(tool_name, window_ms, *, store=None, now_ms=None) -> int
-- windowed call count for a single tool; standalone alternative to unpacking telemetry_full.

PRIMARY DISC.: 5 calls in window -> 5 (not success_count, not error_count, not float).
Old calls excluded; returns int; 0 for unknown/no-recent-calls.
Consistent with get_windowed_tool_telemetry_full()["call_count"].
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_call_count,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_call_count_primary_discriminator() -> None:
    """FALSIFIABLE: 3 successes + 2 failures in window -> call_count=5 (not 3, not 2)."""
    _reset()
    store = _make_store(
        {
            "wcc_a": [
                (_NOW - 10, 10.0, True),
                (_NOW - 10, 20.0, True),
                (_NOW - 10, 30.0, True),
                (_NOW - 10, 40.0, False),
                (_NOW - 10, 50.0, False),
            ]
        }
    )
    result = get_windowed_tool_call_count("wcc_a", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 5  # not 3 (successes), not 2 (errors), not float


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0."""
    _reset()
    assert get_windowed_tool_call_count("no_such_wcc", _WIN, store={}, now_ms=_NOW) == 0


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0."""
    store = _make_store(
        {
            "wcc_old": [(_NOW - _WIN - 100, 50.0, True)] * 3,
        }
    )
    assert get_windowed_tool_call_count("wcc_old", _WIN, store=store, now_ms=_NOW) == 0


def test_only_windowed_calls_counted() -> None:
    """Old calls excluded; only recent calls counted."""
    store = _make_store(
        {
            "wcc_mix": [
                (_NOW - _WIN - 100, 10.0, True),  # old, excluded
                (_NOW - 10, 20.0, True),
                (_NOW - 10, 30.0, True),
            ]
        }
    )
    assert get_windowed_tool_call_count("wcc_mix", _WIN, store=store, now_ms=_NOW) == 2


def test_consistent_with_telemetry_full() -> None:
    """call_count == get_windowed_tool_telemetry_full()['call_count']."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_telemetry_full

    store = _make_store({"wcc_full": [(_NOW - 10, float(v), v % 2 == 0) for v in range(1, 8)]})
    standalone = get_windowed_tool_call_count("wcc_full", _WIN, store=store, now_ms=_NOW)
    from_full = get_windowed_tool_telemetry_full("wcc_full", _WIN, store=store, now_ms=_NOW)[
        "call_count"
    ]
    assert standalone == from_full


def test_returns_int_type() -> None:
    """Return type is int (not float)."""
    store = _make_store({"rtype_wcc": [(_NOW - 10, 5.0, True)] * 3})
    result = get_windowed_tool_call_count("rtype_wcc", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, int)
    assert result == 3


def test_single_call_returns_one() -> None:
    """Single call in window -> 1."""
    store = _make_store({"wcc_one": [(_NOW - 10, 42.0, True)]})
    assert get_windowed_tool_call_count("wcc_one", _WIN, store=store, now_ms=_NOW) == 1
