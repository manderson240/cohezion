"""Item 972: get_windowed_tool_error_count() -- windowed error count for one tool.

get_windowed_tool_error_count(tool_name, window_ms, *, store=None, now_ms=None) -> int

Dual of get_windowed_tool_success_count (item 970).
Returns exact count of failed calls (ok=False) in the window for one tool.
Returns 0 for unknown tool or no recent calls.
Always returns int.

Discriminating tests:
  1. PRIMARY DISC.: 5 calls with 2 failures -> error_count=2
     (kills impl returning call_count=5 or success_count=3; kills impl returning rate=0.4).
  2. All successes -> error_count=0.
  3. Consistent with get_windowed_tool_telemetry_full()["error_count"].
  4. Unknown tool -> 0.
  5. Old calls excluded.
  6. Returns int not float.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_error_count,
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


def test_counts_only_failures_primary_discriminator() -> None:
    """PRIMARY DISC.: 5 calls, 2 failures -> error_count=2 (not 5, not 3, not 0.4)."""
    store: dict = {}
    ts = _recent()
    for _ in range(3):
        _add(store, "t", 10.0, ts, ok=True)
    for _ in range(2):
        _add(store, "t", 10.0, ts, ok=False)

    result = get_windowed_tool_error_count("t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result == 2, (
        f"5 calls, 2 failures -> error_count=2; kills call_count=5 or success_count=3; got {result}"
    )


def test_all_successes_returns_zero() -> None:
    """Zero errors when all calls succeed."""
    store: dict = {}
    for _ in range(5):
        _add(store, "t", 10.0, _recent(), ok=True)

    result = get_windowed_tool_error_count("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 0, f"All successes -> error_count=0; got {result}"


def test_consistent_with_telemetry_full() -> None:
    """Must equal get_windowed_tool_telemetry_full()['error_count']."""
    store: dict = {}
    ts = _recent()
    for _ in range(8):
        _add(store, "t", 10.0, ts, ok=True)
    for _ in range(2):
        _add(store, "t", 10.0, ts, ok=False)

    direct = get_windowed_tool_error_count("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    via_full = get_windowed_tool_telemetry_full("t", WINDOW_MS, store=store, now_ms=NOW_MS)[
        "error_count"
    ]

    assert direct == via_full, f"direct={direct} must equal telemetry_full error_count={via_full}"


def test_unknown_tool_returns_zero() -> None:
    result = get_windowed_tool_error_count("no_such_tool", WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0


def test_old_calls_excluded() -> None:
    """Only errors in the window count."""
    store: dict = {}
    for _ in range(5):
        _add(store, "t", 10.0, _old(), ok=False)  # outside window
    _add(store, "t", 10.0, _recent(), ok=True)  # only this recent (success)

    result = get_windowed_tool_error_count("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 0, f"Old errors excluded; recent call is success -> 0; got {result}"


def test_returns_int() -> None:
    store: dict = {}
    _add(store, "t", 10.0, _recent(), ok=False)
    result = get_windowed_tool_error_count("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, int), f"Must return int; got {type(result)}"
