"""Item 1015: get_windowed_tool_last_call_success() — most-recent call outcome.

get_windowed_tool_last_call_success(tool_name, window_ms, *, store=None, now_ms=None) -> bool | None

True = most-recent call succeeded, False = errored, None = no recent calls.
Uses HIGHEST TIMESTAMP as most-recent, not list order.

Discriminating tests:
  1. PRIMARY DISC.: records where last call (highest ts) has success=False -> returns False
       (kills impl checking first record; kills returning float error_rate)
  2. MOST RECENT BY TIMESTAMP: ts-ordered records where latest entry differs from first -> latest wins
  3. None when no recent calls (empty window)
  4. True when last call succeeded
  5. Old calls excluded -> None (not the old outcome)
  6. Returns bool or None (not float, not int)
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_last_call_success,
)

NOW_MS = 100_000.0
WINDOW_MS = 10_000.0


@pytest.fixture(autouse=True)
def _clean():
    _WINDOWED_TELEMETRY.clear()
    yield
    _WINDOWED_TELEMETRY.clear()


def _add(store: dict, tool: str, ok: bool, ts: float, lat: float = 10.0) -> None:
    store.setdefault(tool, []).append((ts, lat, ok))


def _recent_ts(offset: float = 0.0) -> float:
    return NOW_MS - 5_000.0 + offset


def _old_ts() -> float:
    return NOW_MS - WINDOW_MS - 1_000.0


def test_last_call_false_primary_discriminator() -> None:
    """PRIMARY DISC.: multiple successes then a failure -> returns False.

    Kills impl returning error_rate (float).
    Kills impl returning success_count (int).
    Kills impl checking FIRST record (would return True).
    """
    store: dict = {}
    # 3 successes first, then 1 failure (latest ts)
    for i in range(3):
        _add(store, "lcs_t", True, _recent_ts(float(i)))
    _add(store, "lcs_t", False, _recent_ts(3.0))  # latest

    result = get_windowed_tool_last_call_success("lcs_t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result is False, (
        f"Last call failed; kills first-record=True or error_rate=0.25; got {result}"
    )
    assert isinstance(result, bool)


def test_highest_timestamp_wins_not_list_order() -> None:
    """MOST RECENT BY TIMESTAMP: latest ts wins regardless of insertion order.

    Kills impl using list[-1] instead of max(ts).
    """
    store: dict = {}
    # Insert in reverse order: newest first (ts=100), then oldest
    _add(store, "lcs_ts", True, _recent_ts(3.0))   # ts=later → SUCCESS
    _add(store, "lcs_ts", False, _recent_ts(1.0))   # ts=earlier → FAILURE
    _add(store, "lcs_ts", False, _recent_ts(0.0))   # ts=earliest → FAILURE

    result = get_windowed_tool_last_call_success(
        "lcs_ts", WINDOW_MS, store=store, now_ms=NOW_MS
    )

    assert result is True, (
        f"Latest ts=True regardless of insertion order; kills list[-1]=False; got {result}"
    )


def test_no_recent_calls_returns_none() -> None:
    """No calls in window -> None (not False, not 0)."""
    result = get_windowed_tool_last_call_success(
        "no_such", WINDOW_MS, store={}, now_ms=NOW_MS
    )
    assert result is None, f"Empty store -> None; got {result}"


def test_last_call_true() -> None:
    """Most-recent call succeeded -> returns True."""
    store: dict = {}
    _add(store, "lcs_ok", False, _recent_ts(0.0))  # older failure
    _add(store, "lcs_ok", True, _recent_ts(1.0))   # latest success

    result = get_windowed_tool_last_call_success(
        "lcs_ok", WINDOW_MS, store=store, now_ms=NOW_MS
    )
    assert result is True, f"Last call succeeded -> True; got {result}"


def test_old_calls_excluded_returns_none() -> None:
    """Old calls outside window excluded; no recent calls -> None."""
    store: dict = {}
    for _ in range(5):
        _add(store, "lcs_old", True, _old_ts())

    result = get_windowed_tool_last_call_success(
        "lcs_old", WINDOW_MS, store=store, now_ms=NOW_MS
    )
    assert result is None, f"Old excluded; no recent calls -> None; got {result}"


def test_returns_bool_not_float_not_int() -> None:
    """Return type must be bool (or None), not float or int."""
    store: dict = {}
    _add(store, "lcs_rt", True, _recent_ts(0.0))

    result = get_windowed_tool_last_call_success(
        "lcs_rt", WINDOW_MS, store=store, now_ms=NOW_MS
    )
    assert isinstance(result, bool), f"Must return bool; got {type(result)}"
    assert result is not None
