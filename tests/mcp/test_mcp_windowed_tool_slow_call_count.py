"""Item 1003: get_windowed_tool_slow_call_count() — SLO slow-call counter.

get_windowed_tool_slow_call_count(tool_name, window_ms, threshold_ms, *, store=None, now_ms=None) -> int

Counts calls with latency STRICTLY > threshold_ms in the window.
Useful for SLO compliance: "how many calls breached the 200ms SLA?"

Discriminating tests:
  1. PRIMARY DISC.: lats [10, 50, 200, 300] with threshold=100 -> 2
       (kills count-all=4; kills count->50 with threshold=100 would give 2, but:)
       (more subtle disc: threshold=50, lats [10, 50, 200] -> 1 not 2 -- strictly >)
  2. STRICT GT DISC.: threshold=50 with lats [10, 50, 200] -> 1 (50 is NOT > 50)
       (kills >= implementations that would give 2)
  3. Returns int (not float).
  4. Unknown tool -> 0.
  5. Old calls excluded.
  6. threshold=0 -> all calls.
  7. All below threshold -> 0.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_tool_slow_call_count,
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


def test_slow_count_threshold_100_primary_discriminator() -> None:
    """PRIMARY DISC.: lats [10, 50, 200, 300] with threshold=100 -> 2.

    10 < 100 → not slow
    50 < 100 → not slow
    200 > 100 → slow
    300 > 100 → slow

    Kills "count all calls" = 4.
    Kills "count > 50" (wrong threshold) = 3.
    """
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 50.0, 200.0, 300.0]:
        _add(store, "t", lat, ts)

    result = get_windowed_tool_slow_call_count("t", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS)

    assert isinstance(result, int), f"Must return int; got {type(result)}"
    assert result == 2, (
        f"threshold=100; [10,50,200,300] -> 2 slow; kills all=4, >50=3; got {result}"
    )


def test_strictly_greater_than_not_gte() -> None:
    """STRICT GT DISC.: threshold=50, lats [10, 50, 200] -> 1 (50 is NOT > 50).

    50 == threshold → NOT counted (strictly greater than, not >=)
    200 > 50 → counted

    Kills >= implementation (would give 2).
    """
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 50.0, 200.0]:
        _add(store, "t_gt", lat, ts)

    result = get_windowed_tool_slow_call_count("t_gt", WINDOW_MS, 50.0, store=store, now_ms=NOW_MS)

    assert result == 1, (
        f"strict >: 50 == threshold not counted; only 200 > 50 -> 1; kills >=impl=2; got {result}"
    )


def test_returns_int_type() -> None:
    store: dict = {}
    _add(store, "t_int", 300.0, _recent())
    result = get_windowed_tool_slow_call_count(
        "t_int", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert isinstance(result, int), f"Must be int not float; got {type(result)}"


def test_unknown_tool_returns_zero() -> None:
    result = get_windowed_tool_slow_call_count("no_such", WINDOW_MS, 100.0, store={}, now_ms=NOW_MS)
    assert result == 0


def test_old_calls_excluded() -> None:
    """Old slow calls must not count."""
    store: dict = {}
    for _ in range(10):
        _add(store, "t_old", 9999.0, _old())  # old, would be slow
    for lat in [10.0, 20.0, 30.0]:  # recent, all below threshold
        _add(store, "t_old", lat, _recent())

    result = get_windowed_tool_slow_call_count(
        "t_old", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert result == 0, f"Old excluded; all recent < 100ms; got {result}"


def test_all_below_threshold_returns_zero() -> None:
    store: dict = {}
    for lat in [10.0, 20.0, 30.0]:
        _add(store, "t_below", lat, _recent())
    result = get_windowed_tool_slow_call_count(
        "t_below", WINDOW_MS, 100.0, store=store, now_ms=NOW_MS
    )
    assert result == 0, f"All < 100ms threshold -> 0; got {result}"


def test_threshold_zero_counts_all_nonzero_latencies() -> None:
    """With threshold=0, all positive latencies are slow."""
    store: dict = {}
    for lat in [1.0, 5.0, 100.0, 1000.0]:
        _add(store, "t_zero", lat, _recent())
    result = get_windowed_tool_slow_call_count("t_zero", WINDOW_MS, 0.0, store=store, now_ms=NOW_MS)
    assert result == 4, f"threshold=0; all 4 calls > 0 -> 4; got {result}"
