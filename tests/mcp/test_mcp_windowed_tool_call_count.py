"""Item 982: get_windowed_tool_call_count() -- windowed per-tool call count standalone.

get_windowed_tool_call_count(tool_name, window_ms, *, store=None, now_ms=None) -> int

Standalone accessor for the windowed call count of a single tool.
Returns both successful and failed calls combined (total call count).
0 for unknown tool or no recent calls.
Consistent with get_windowed_tool_telemetry_full()["call_count"].

Discriminating tests:
  1. PRIMARY DISC.: 3 successes + 2 failures -> call_count=5 (not 3 or 2)
     (kills impl returning success_count=3 or error_count=2).
  2. Consistent with telemetry_full()["call_count"].
  3. Unknown tool -> 0.
  4. Old calls excluded.
  5. Returns int.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_call_count,
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


def test_counts_all_calls_not_just_successes_primary_discriminator() -> None:
    """PRIMARY DISC.: 3 successes + 2 failures -> call_count=5 (kills success_count=3 or error_count=2)."""
    store: dict = {}
    ts = _recent()
    for _ in range(3):
        _add(store, "t", 10.0, ts, ok=True)
    for _ in range(2):
        _add(store, "t", 10.0, ts, ok=False)

    result = get_windowed_tool_call_count("t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result == 5, (
        f"3 successes + 2 failures = 5 total; kills success_count=3 or error_count=2; got {result}"
    )


def test_consistent_with_telemetry_full() -> None:
    """Must equal get_windowed_tool_telemetry_full()['call_count']."""
    store: dict = {}
    ts = _recent()
    for _ in range(7):
        _add(store, "t", 10.0, ts, ok=True)
    for _ in range(3):
        _add(store, "t", 10.0, ts, ok=False)

    direct = get_windowed_tool_call_count("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    via_full = get_windowed_tool_telemetry_full("t", WINDOW_MS, store=store, now_ms=NOW_MS)[
        "call_count"
    ]

    assert direct == via_full, f"direct={direct} must equal telemetry_full call_count={via_full}"


def test_unknown_tool_returns_zero() -> None:
    result = get_windowed_tool_call_count("no_such_tool", WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0


def test_old_calls_excluded() -> None:
    """Only calls in the window count."""
    store: dict = {}
    for _ in range(10):
        _add(store, "t", 10.0, _old())  # outside window
    _add(store, "t", 10.0, _recent())  # 1 recent call

    result = get_windowed_tool_call_count("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 1, f"Only 1 recent call; got {result}"


def test_returns_int() -> None:
    store: dict = {}
    _add(store, "t", 10.0, _recent())
    result = get_windowed_tool_call_count("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, int), f"Must return int; got {type(result)}"
