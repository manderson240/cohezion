"""Item 971: get_windowed_global_success_count() -- fleet-wide windowed success count.

get_windowed_global_success_count(window_ms, *, store=None, now_ms=None) -> int

Sums ok=True calls across ALL tools within the window.
Returns 0 when no recent calls or store is empty.
Always returns int.

Discriminating tests:
  1. PRIMARY DISC.: tool_a 3 successes + tool_b 2 successes = 5
     (kills impl summing total calls instead of successes; kills impl returning rate).
  2. tool with errors does not inflate success count.
  3. old calls excluded.
  4. empty store -> 0.
  5. single-tool result equals get_windowed_tool_success_count().
  6. returns int.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_success_count,
    get_windowed_tool_telemetry_full,
)

NOW_MS = 100_000.0
WINDOW_MS = 10_000.0


@pytest.fixture(autouse=True)
def _clean():
    _WINDOWED_TELEMETRY.clear()
    yield
    _WINDOWED_TELEMETRY.clear()


def _add(store: dict, tool: str, lat: float, ts: float, ok: bool = True) -> None:
    store.setdefault(tool, []).append((ts, lat, ok))


def _recent() -> float:
    return NOW_MS - 5_000.0


def _old() -> float:
    return NOW_MS - WINDOW_MS - 1_000.0


def test_sums_successes_across_tools_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a 3 ok + tool_b 2 ok = 5 (not total calls, not rate)."""
    store: dict = {}
    ts = _recent()
    for _ in range(3):
        _add(store, "tool_a", 10.0, ts, ok=True)
    for _ in range(2):
        _add(store, "tool_b", 10.0, ts, ok=True)

    result = get_windowed_global_success_count(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result == 5, f"3+2 successes = 5; got {result}"


def test_errors_do_not_inflate_success_count() -> None:
    """Errors (ok=False) must not be counted as successes."""
    store: dict = {}
    ts = _recent()
    for _ in range(4):
        _add(store, "t", 10.0, ts, ok=True)
    for _ in range(3):
        _add(store, "t", 10.0, ts, ok=False)
    # 4 successes, 3 errors, 7 total -- must return 4 not 7

    result = get_windowed_global_success_count(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 4, f"4 successes, 3 errors -> 4; got {result}"


def test_old_calls_excluded() -> None:
    """Successful calls outside the window must not count."""
    store: dict = {}
    for _ in range(10):
        _add(store, "t", 10.0, _old(), ok=True)  # outside window
    _add(store, "t", 10.0, _recent(), ok=True)  # only this recent success

    result = get_windowed_global_success_count(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 1, f"Only 1 recent success; got {result}"


def test_empty_store_returns_zero() -> None:
    result = get_windowed_global_success_count(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0


def test_single_tool_consistent_with_full_telemetry() -> None:
    """For a single tool, result == call_count - error_count from telemetry_full."""
    store: dict = {}
    ts = _recent()
    for _ in range(6):
        _add(store, "t", 10.0, ts, ok=True)
    _add(store, "t", 10.0, ts, ok=False)

    global_ok = get_windowed_global_success_count(WINDOW_MS, store=store, now_ms=NOW_MS)
    full = get_windowed_tool_telemetry_full("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    per_tool_ok = full["call_count"] - full["error_count"]

    assert global_ok == per_tool_ok, (
        f"single-tool global={global_ok} must equal call_count-error_count={per_tool_ok}"
    )


def test_returns_int() -> None:
    store: dict = {}
    _add(store, "t", 10.0, _recent(), ok=True)
    result = get_windowed_global_success_count(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, int), f"Must return int; got {type(result)}"
