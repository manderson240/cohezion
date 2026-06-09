"""Item 1021: get_windowed_tool_success_count() — count of successful calls in window.

get_windowed_tool_success_count(tool_name, window_ms, *, store=None, now_ms=None) -> int

Count of calls where ok=True in window. 0 for unknown/empty.
Complementary dual of get_windowed_tool_error_count:
  success_count + error_count == total_call_count.

Discriminating tests:
  1. PRIMARY DISC.: [True, False, True, True, False] -> success_count=3
       (kills error_count=2; kills total_count=5; correct success_count=3)
  2. All failures -> 0 (not negative, not None)
  3. All successes -> n
  4. No recent calls -> 0 (unknown tool returns 0)
  5. Old calls excluded
  6. Returns int (not float, not bool)
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_success_count,
)

NOW_MS = 100_000.0
WINDOW_MS = 10_000.0
CUTOFF_MS = NOW_MS - WINDOW_MS


@pytest.fixture(autouse=True)
def _clean():
    _WINDOWED_TELEMETRY.clear()
    yield
    _WINDOWED_TELEMETRY.clear()


def _add(store: dict, tool: str, ok: bool, ts: float, lat: float = 10.0) -> None:
    store.setdefault(tool, []).append((ts, lat, ok))


def _recent(offset: float = 0.0) -> float:
    return NOW_MS - 500.0 + offset


def _old() -> float:
    return NOW_MS - WINDOW_MS - 1_000.0


def test_success_not_error_not_total_primary_discriminator() -> None:
    """PRIMARY DISC.: [True, False, True, True, False] -> success_count=3.

    Kills impl returning error_count=2 (inverted success/failure).
    Kills impl returning total_count=5 (not filtering on ok=True).
    """
    store: dict = {}
    outcomes = [True, False, True, True, False]
    for i, ok in enumerate(outcomes):
        _add(store, "sc_t", ok, _recent(float(i)))

    result = get_windowed_tool_success_count("sc_t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, int)
    assert result == 3, (
        f"success_count=3; kills error_count=2 or total_count=5; got {result}"
    )


def test_all_failures_returns_zero() -> None:
    """All calls failed -> success_count = 0 (not n, not negative)."""
    store: dict = {}
    for i in range(4):
        _add(store, "sc_all_fail", False, _recent(float(i)))

    result = get_windowed_tool_success_count(
        "sc_all_fail", WINDOW_MS, store=store, now_ms=NOW_MS
    )
    assert result == 0, f"All failures -> 0; got {result}"


def test_all_successes_returns_n() -> None:
    """All calls succeeded -> success_count = n."""
    store: dict = {}
    n = 5
    for i in range(n):
        _add(store, "sc_all_ok", True, _recent(float(i)))

    result = get_windowed_tool_success_count(
        "sc_all_ok", WINDOW_MS, store=store, now_ms=NOW_MS
    )
    assert result == n, f"All successes -> {n}; got {result}"


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0 (not KeyError, not None)."""
    result = get_windowed_tool_success_count(
        "no_such_tool", WINDOW_MS, store={}, now_ms=NOW_MS
    )
    assert result == 0, f"Unknown tool -> 0; got {result}"


def test_old_calls_excluded() -> None:
    """Old calls outside window must not count as successes."""
    store: dict = {}
    # Old successful calls — must NOT be counted
    for _ in range(10):
        _add(store, "sc_old", True, _old())
    # Recent calls: 2 successes, 1 failure
    _add(store, "sc_old", True, _recent(0.0))
    _add(store, "sc_old", True, _recent(1.0))
    _add(store, "sc_old", False, _recent(2.0))

    result = get_windowed_tool_success_count(
        "sc_old", WINDOW_MS, store=store, now_ms=NOW_MS
    )
    assert result == 2, f"Old excluded; recent successes=2; got {result}"


def test_returns_int_not_float_not_bool() -> None:
    """Return type must be int (not float, not bool)."""
    store: dict = {}
    _add(store, "sc_rt", True, _recent(0.0))

    result = get_windowed_tool_success_count(
        "sc_rt", WINDOW_MS, store=store, now_ms=NOW_MS
    )
    assert isinstance(result, int), f"Must return int; got {type(result)}"
    assert not isinstance(result, bool), "Must not be bool subtype"


def test_success_plus_error_equals_total() -> None:
    """success_count + error_count == total_call_count (complementary pair invariant)."""
    from cohezion.mcp.compound_mcp_telemetry import (
        get_windowed_tool_call_count,
        get_windowed_tool_error_count,
    )

    store: dict = {}
    outcomes = [True, False, True, False, True, False, True]
    for i, ok in enumerate(outcomes):
        _add(store, "sc_pair", ok, _recent(float(i)))

    success = get_windowed_tool_success_count(
        "sc_pair", WINDOW_MS, store=store, now_ms=NOW_MS
    )
    errors = get_windowed_tool_error_count(
        "sc_pair", WINDOW_MS, store=store, now_ms=NOW_MS
    )
    total = get_windowed_tool_call_count(
        "sc_pair", WINDOW_MS, store=store, now_ms=NOW_MS
    )

    assert success + errors == total, (
        f"success={success} + errors={errors} must equal total={total}"
    )
