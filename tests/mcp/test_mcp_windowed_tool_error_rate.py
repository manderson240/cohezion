"""Item 985: get_windowed_tool_error_rate() -- windowed per-tool error rate standalone.

get_windowed_tool_error_rate(tool_name, window_ms, *, store=None, now_ms=None) -> float

Standalone accessor for the error_rate field from get_windowed_tool_telemetry_full().
error_rate = error_count / call_count.
0.0 for unknown tool or no recent calls.
Consistent with get_windowed_tool_telemetry_full()["error_rate"].

Discriminating tests:
  1. PRIMARY DISC.: 5 calls with 2 failures -> error_rate=0.4 (not error_count=2.0 or success_rate=0.6)
     (kills impl returning raw error_count=2 as float, or returning complement).
  2. Consistent with telemetry_full()["error_rate"].
  3. error_rate + success_rate == 1.0 for non-empty window.
  4. Unknown tool -> 0.0.
  5. Old calls excluded.
  6. All-success -> 0.0; all-failure -> 1.0.
  7. Returns float.
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_error_rate,
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


def test_error_rate_not_count_not_success_rate_primary_discriminator() -> None:
    """PRIMARY DISC.: 5 calls with 2 failures -> 0.4.

    Kills impl returning raw error_count=2.0.
    Kills impl returning success_rate=0.6.
    The rate is errors/total, not errors alone, not 1-errors.
    """
    store: dict = {}
    ts = _recent()
    for _ in range(3):
        _add(store, "t", 10.0, ts, ok=True)
    for _ in range(2):
        _add(store, "t", 10.0, ts, ok=False)

    result = get_windowed_tool_error_rate("t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 0.4) < 1e-9, (
        f"2 errors / 5 total = 0.4; kills error_count=2.0 or success_rate=0.6; got {result}"
    )


def test_consistent_with_telemetry_full() -> None:
    """Must equal get_windowed_tool_telemetry_full()['error_rate']."""
    store: dict = {}
    ts = _recent()
    for _ in range(7):
        _add(store, "t", 10.0, ts, ok=True)
    for _ in range(3):
        _add(store, "t", 10.0, ts, ok=False)

    direct = get_windowed_tool_error_rate("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    via_full = get_windowed_tool_telemetry_full(
        "t", WINDOW_MS, store=store, now_ms=NOW_MS
    )["error_rate"]

    assert abs(direct - via_full) < 1e-9, (
        f"direct={direct} must equal telemetry_full error_rate={via_full}"
    )


def test_error_rate_plus_success_rate_equals_one() -> None:
    """error_rate + success_rate == 1.0 for any non-empty window."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_telemetry_full

    store: dict = {}
    ts = _recent()
    for _ in range(4):
        _add(store, "t", 10.0, ts, ok=True)
    for _ in range(6):
        _add(store, "t", 10.0, ts, ok=False)

    err = get_windowed_tool_error_rate("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    full = get_windowed_tool_telemetry_full("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    suc = full["success_rate"]

    assert abs(err + suc - 1.0) < 1e-9, (
        f"error_rate={err} + success_rate={suc} must = 1.0"
    )


def test_unknown_tool_returns_zero() -> None:
    result = get_windowed_tool_error_rate("no_such_tool", WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Only calls within the window contribute to the rate."""
    store: dict = {}
    # 10 failures outside the window
    for _ in range(10):
        _add(store, "t", 10.0, _old(), ok=False)
    # 3 successes + 1 failure inside window -> rate = 0.25
    for _ in range(3):
        _add(store, "t", 10.0, _recent(), ok=True)
    _add(store, "t", 10.0, _recent(), ok=False)

    result = get_windowed_tool_error_rate("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 0.25) < 1e-9, f"Old failures excluded; 1/4=0.25; got {result}"


def test_all_successes_returns_zero() -> None:
    """Zero errors -> error_rate=0.0."""
    store: dict = {}
    for _ in range(5):
        _add(store, "t", 10.0, _recent(), ok=True)
    result = get_windowed_tool_error_rate("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 0.0, f"All-success -> 0.0; got {result}"


def test_all_failures_returns_one() -> None:
    """All errors -> error_rate=1.0."""
    store: dict = {}
    for _ in range(5):
        _add(store, "t", 10.0, _recent(), ok=False)
    result = get_windowed_tool_error_rate("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 1.0) < 1e-9, f"All-failure -> 1.0; got {result}"


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t", 10.0, _recent(), ok=False)
    _add(store, "t", 10.0, _recent(), ok=True)
    result = get_windowed_tool_error_rate("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must return float; got {type(result)}"
