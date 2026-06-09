"""Item 1015: get_windowed_tool_last_call_success(tool_name, window_ms, *, store=None, now_ms=None) -> bool | None
-- outcome of most-recent call in window.

True  if the most-recent call succeeded.
False if the most-recent call errored.
None  if no recent calls (unknown/empty or all outside window).

Instant health pulse — no rate aggregation.

PRIMARY DISC.: records where last call (highest ts) has success=False -> returns False.
  Kills: returning float error_rate; returning True (wrong); returning None (wrong).
  Strictly checks the MOST RECENT call by timestamp (not first, not majority).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_last_call_success,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_last_call_failed_returns_false() -> None:
    """PRIMARY DISC.: most-recent call (highest ts) success=False -> False.

    Earlier calls succeeded, latest failed.
    Kills: returning True (majority wins); returning error_rate float; returning None.
    """
    _reset()
    store = _make_store({
        "lcs_a": [
            (_NOW - 30, 10.0, True),
            (_NOW - 20, 20.0, True),
            (_NOW - 10, 30.0, False),  # most recent: failed
        ],
    })
    result = get_windowed_tool_last_call_success("lcs_a", _WIN, store=store, now_ms=_NOW)
    assert result is False, f"most-recent failed -> False; got {result}"
    assert isinstance(result, bool)


def test_last_call_succeeded_returns_true() -> None:
    """Most-recent call succeeded -> True."""
    _reset()
    store = _make_store({
        "lcs_b": [
            (_NOW - 30, 10.0, False),
            (_NOW - 20, 20.0, False),
            (_NOW - 10, 30.0, True),  # most recent: succeeded
        ],
    })
    result = get_windowed_tool_last_call_success("lcs_b", _WIN, store=store, now_ms=_NOW)
    assert result is True, f"most-recent succeeded -> True; got {result}"


def test_uses_highest_timestamp_not_list_order() -> None:
    """Returns outcome of call with HIGHEST timestamp, not first/last in list.

    Records stored out-of-order in list; function must pick by ts.
    """
    _reset()
    store = _make_store({
        "lcs_ts": [
            (_NOW - 10, 10.0, False),  # newest ts, stored first in list: failed
            (_NOW - 20, 20.0, True),   # older ts, stored second: succeeded
            (_NOW - 30, 30.0, False),  # oldest
        ],
    })
    # Most recent by ts = (_NOW-10, False)
    result = get_windowed_tool_last_call_success("lcs_ts", _WIN, store=store, now_ms=_NOW)
    assert result is False, (
        f"highest-ts call (failed) -> False; not list-order-first; got {result}"
    )


def test_unknown_tool_returns_none() -> None:
    """Unknown tool -> None."""
    _reset()
    result = get_windowed_tool_last_call_success("no_such_lcs", _WIN, store={}, now_ms=_NOW)
    assert result is None, f"unknown tool -> None; got {result}"


def test_no_recent_calls_returns_none() -> None:
    """All calls outside window -> None."""
    _reset()
    store = _make_store({
        "lcs_old": [(_NOW - _WIN - 100, 10.0, True)] * 3,
    })
    result = get_windowed_tool_last_call_success("lcs_old", _WIN, store=store, now_ms=_NOW)
    assert result is None, f"no recent calls -> None; got {result}"


def test_single_success_returns_true() -> None:
    """Single success call -> True."""
    _reset()
    store = _make_store({
        "lcs_one_ok": [(_NOW - 10, 10.0, True)],
    })
    assert get_windowed_tool_last_call_success("lcs_one_ok", _WIN, store=store, now_ms=_NOW) is True


def test_single_failure_returns_false() -> None:
    """Single failure call -> False."""
    _reset()
    store = _make_store({
        "lcs_one_fail": [(_NOW - 10, 10.0, False)],
    })
    assert get_windowed_tool_last_call_success("lcs_one_fail", _WIN, store=store, now_ms=_NOW) is False


def test_return_type_is_bool_not_none() -> None:
    """When calls exist, return type is bool (True or False), not None."""
    _reset()
    store = _make_store({
        "lcs_type": [(_NOW - 10, 10.0, True)] * 3,
    })
    result = get_windowed_tool_last_call_success("lcs_type", _WIN, store=store, now_ms=_NOW)
    assert isinstance(result, bool) and result is not None
