"""Item 1014: get_windowed_tool_consecutive_error_count() — per-tool error streak.

get_windowed_tool_consecutive_error_count(tool_name, window_ms, *, store=None, now_ms=None) -> int

Number of consecutive errors at the END of the window (most-recent calls).
0 when no errors in window, last call succeeded, or unknown tool.
Detects active error storms — distinct from total_error_count.

Discriminating tests:
  1. PRIMARY DISC.: [True, False, True, False, False] -> consecutive_at_end=2
       (total_errors=3 is a WRONG answer; correct=2 consecutive at end)
  2. TAIL DISC.: [False, False, True, False] -> consecutive=1 (not 3)
       (kills "count all False in window" = 3; correct tail = 1)
  3. Last call success -> 0 (streak broken)
  4. No recent calls -> 0
  5. All errors -> n
  6. Returns int
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_consecutive_error_count,
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
    """Return a recent timestamp with an offset for ordering."""
    return NOW_MS - 5_000.0 + offset


def _old_ts() -> float:
    return NOW_MS - WINDOW_MS - 1_000.0


def test_consecutive_at_end_not_total_primary_discriminator() -> None:
    """PRIMARY DISC.: [True, False, True, False, False] (oldest→newest) -> 2.

    total_errors = 3 (False at positions 1, 3, 4).
    consecutive at END = 2 (positions 3 and 4 are both False, position 2 broke streak).

    Kills impl returning total_error_count=3.
    """
    store: dict = {}
    # Insert in chronological order: oldest first, newest last
    outcomes = [True, False, True, False, False]
    for i, ok in enumerate(outcomes):
        _add(store, "ce_t", ok, _recent_ts(float(i)))

    result = get_windowed_tool_consecutive_error_count("ce_t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, int)
    assert result == 2, (
        f"[T,F,T,F,F] -> 2 consecutive at end; kills total_errors=3; got {result}"
    )


def test_tail_not_all_in_window_discriminator() -> None:
    """TAIL DISC.: [False, False, True, False] (oldest→newest) -> 1.

    total False in window = 3.
    The True at position 2 breaks the streak; only 1 at the end.

    Kills impl counting all False in window (would return 3).
    """
    store: dict = {}
    outcomes = [False, False, True, False]
    for i, ok in enumerate(outcomes):
        _add(store, "ce_tail", ok, _recent_ts(float(i)))

    result = get_windowed_tool_consecutive_error_count(
        "ce_tail", WINDOW_MS, store=store, now_ms=NOW_MS
    )

    assert result == 1, (
        f"[F,F,T,F] -> 1 consecutive at end; kills count-all-False=3; got {result}"
    )


def test_last_call_success_returns_zero() -> None:
    """Streak broken by final success -> 0."""
    store: dict = {}
    # 3 errors then a success
    for i in range(3):
        _add(store, "ce_suc", False, _recent_ts(float(i)))
    _add(store, "ce_suc", True, _recent_ts(3.0))

    result = get_windowed_tool_consecutive_error_count(
        "ce_suc", WINDOW_MS, store=store, now_ms=NOW_MS
    )
    assert result == 0, f"Last call success -> 0; got {result}"


def test_all_errors_returns_count() -> None:
    """All calls failed -> count = n."""
    store: dict = {}
    n = 4
    for i in range(n):
        _add(store, "ce_all", False, _recent_ts(float(i)))

    result = get_windowed_tool_consecutive_error_count(
        "ce_all", WINDOW_MS, store=store, now_ms=NOW_MS
    )
    assert result == n, f"All errors -> {n}; got {result}"


def test_unknown_tool_returns_zero() -> None:
    result = get_windowed_tool_consecutive_error_count(
        "no_such", WINDOW_MS, store={}, now_ms=NOW_MS
    )
    assert result == 0


def test_old_errors_excluded() -> None:
    """Old error calls outside the window must not extend the streak."""
    store: dict = {}
    for _ in range(5):
        _add(store, "ce_old", False, _old_ts())
    # Recent: success only
    _add(store, "ce_old", True, _recent_ts(0.0))

    result = get_windowed_tool_consecutive_error_count(
        "ce_old", WINDOW_MS, store=store, now_ms=NOW_MS
    )
    assert result == 0, f"Old excluded; last recent = success -> 0; got {result}"


def test_returns_int() -> None:
    store: dict = {}
    for i in range(3):
        _add(store, "ce_rt", False, _recent_ts(float(i)))
    result = get_windowed_tool_consecutive_error_count(
        "ce_rt", WINDOW_MS, store=store, now_ms=NOW_MS
    )
    assert isinstance(result, int), f"Must return int; got {type(result)}"
