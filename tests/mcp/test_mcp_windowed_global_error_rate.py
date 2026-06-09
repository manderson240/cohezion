"""Item 953: get_windowed_global_error_rate() -- overall error rate in recent window.

get_windowed_global_error_rate(window_ms, *, store=None, now_ms=None) -> float

Computes total_windowed_errors / total_windowed_calls across all tools in
_WINDOWED_TELEMETRY; 0.0 when no recent calls; injectable store.

Discriminating tests:
  1. PRIMARY DISC.: 2 tools A(3 calls/2 errors) + B(1 call/0 errors) ->
     2/4=0.5; kills avg-per-tool-rates impl (2/3+0)/2=0.333 WRONG.
  2. Empty store -> 0.0.
  3. No recent calls -> 0.0.
  4. All successful -> 0.0.
  5. All errors -> 1.0.
  6. Returns float not int.
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_error_rate,
)

NOW_MS = 100_000.0
WINDOW_MS = 10_000.0


@pytest.fixture(autouse=True)
def _clean():
    _WINDOWED_TELEMETRY.clear()
    yield
    _WINDOWED_TELEMETRY.clear()


def _add(store: dict, tool: str, ts: float, ok: bool, lat: float = 10.0) -> None:
    store.setdefault(tool, []).append((ts, lat, ok))


def _recent(ts_offset: float = 5_000.0) -> float:
    return NOW_MS - ts_offset


def test_weighted_rate_not_avg_per_tool_primary_discriminator() -> None:
    """PRIMARY DISC.: weighted total rate != avg-of-per-tool-rates when counts differ.

    tool_a: 3 calls, 2 errors -> error_rate=0.667
    tool_b: 1 call,  0 errors -> error_rate=0.0
    avg-per-tool = (0.667+0.0)/2 = 0.333 WRONG
    correct = 2 total errors / 4 total calls = 0.5
    """
    store: dict = {}
    ts = _recent()
    _add(store, "tool_a", ts, ok=False)
    _add(store, "tool_a", ts, ok=False)
    _add(store, "tool_a", ts, ok=True)
    _add(store, "tool_b", ts, ok=True)

    result = get_windowed_global_error_rate(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 0.5) < 1e-9, (
        f"2/4=0.5; avg-per-tool would give 0.333; got {result}"
    )


def test_empty_store_returns_zero() -> None:
    """Empty store -> 0.0."""
    result = get_windowed_global_error_rate(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0, f"Empty -> 0.0; got {result}"


def test_no_recent_calls_returns_zero() -> None:
    """All calls outside window -> 0.0."""
    store: dict = {}
    old_ts = NOW_MS - WINDOW_MS - 1_000.0
    _add(store, "tool", old_ts, ok=False)
    result = get_windowed_global_error_rate(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 0.0, f"Old calls excluded -> 0.0; got {result}"


def test_all_successful_returns_zero() -> None:
    """All successful calls -> 0.0."""
    store: dict = {}
    for _ in range(5):
        _add(store, "t", _recent(), ok=True)
    result = get_windowed_global_error_rate(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 0.0, f"All success -> 0.0; got {result}"


def test_all_errors_returns_one() -> None:
    """All failed calls -> 1.0."""
    store: dict = {}
    for _ in range(4):
        _add(store, "t", _recent(), ok=False)
    result = get_windowed_global_error_rate(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 1.0, f"All errors -> 1.0; got {result}"


def test_returns_float_not_int() -> None:
    """Return type is float."""
    store: dict = {}
    _add(store, "t", _recent(), ok=False)
    _add(store, "t", _recent(), ok=True)
    result = get_windowed_global_error_rate(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must be float; got {type(result)}"


def test_uses_windowed_telemetry_by_default() -> None:
    """Without store kwarg, reads _WINDOWED_TELEMETRY singleton."""
    _WINDOWED_TELEMETRY["x"] = [(NOW_MS - 5_000.0, 10.0, False)]  # 1 error
    result = get_windowed_global_error_rate(WINDOW_MS, now_ms=NOW_MS)
    assert result == 1.0, f"1 error / 1 call = 1.0; got {result}"
