"""Item 973: get_windowed_global_error_count() -- fleet-wide windowed error count.

get_windowed_global_error_count(window_ms, *, store=None, now_ms=None) -> int

Sums ok=False calls across ALL tools within the window.
Complement of get_windowed_global_success_count (item 971).
Property: global_success_count + global_error_count == global_call_count.
Returns 0 when no recent calls or store is empty.
Always returns int.

Discriminating tests:
  1. PRIMARY DISC.: tool_a 2 errors + tool_b 3 errors = 5
     (kills impl summing total calls; kills impl returning global_error_rate).
  2. All successes -> global_error_count=0.
  3. success_count + error_count == total_call_count (conservation property).
  4. old calls excluded.
  5. empty store -> 0.
  6. returns int.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_error_count,
    get_windowed_global_success_count,
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


def test_sums_errors_across_tools_primary_discriminator() -> None:
    """PRIMARY DISC.: tool_a 2 errors + tool_b 3 errors = 5 (not total calls, not rate)."""
    store: dict = {}
    ts = _recent()
    for _ in range(2):
        _add(store, "tool_a", 10.0, ts, ok=False)
    for _ in range(3):
        _add(store, "tool_b", 10.0, ts, ok=False)
    # Add some successes to ensure errors-only are counted
    for _ in range(4):
        _add(store, "tool_a", 10.0, ts, ok=True)

    result = get_windowed_global_error_count(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result == 5, f"2+3 errors = 5; got {result}"


def test_all_successes_returns_zero() -> None:
    """No errors in fleet -> global_error_count=0."""
    store: dict = {}
    ts = _recent()
    for tool in ["a", "b", "c"]:
        for _ in range(3):
            _add(store, tool, 10.0, ts, ok=True)

    result = get_windowed_global_error_count(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 0, f"All successes -> 0; got {result}"


def test_success_plus_error_equals_total() -> None:
    """success_count + error_count == total_call_count (conservation property)."""
    store: dict = {}
    ts = _recent()
    _add(store, "tool_a", 10.0, ts, ok=True)
    _add(store, "tool_a", 10.0, ts, ok=False)
    _add(store, "tool_b", 10.0, ts, ok=True)
    _add(store, "tool_b", 10.0, ts, ok=True)
    _add(store, "tool_b", 10.0, ts, ok=False)
    # total=5, success=3, errors=2

    success = get_windowed_global_success_count(WINDOW_MS, store=store, now_ms=NOW_MS)
    errors = get_windowed_global_error_count(WINDOW_MS, store=store, now_ms=NOW_MS)
    total = sum(
        1 for records in store.values() for ts_r, _lat, _ok in records if ts_r >= NOW_MS - WINDOW_MS
    )

    assert success + errors == total, (
        f"success({success}) + errors({errors}) must equal total({total})"
    )
    assert errors == 2 and success == 3


def test_old_calls_excluded() -> None:
    """Errors outside the window must not be counted."""
    store: dict = {}
    for _ in range(8):
        _add(store, "t", 10.0, _old(), ok=False)  # outside window
    _add(store, "t", 10.0, _recent(), ok=False)  # 1 recent error

    result = get_windowed_global_error_count(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 1, f"Only 1 recent error; got {result}"


def test_empty_store_returns_zero() -> None:
    result = get_windowed_global_error_count(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0


def test_returns_int() -> None:
    store: dict = {}
    _add(store, "t", 10.0, _recent(), ok=False)
    result = get_windowed_global_error_count(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, int), f"Must return int; got {type(result)}"
