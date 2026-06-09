"""Item 992: get_windowed_tool_p99_ms() -- per-tool p99 latency standalone shortcut.

get_windowed_tool_p99_ms(tool_name, window_ms, *, store=None, now_ms=None) -> float

Convenience shortcut for get_windowed_latency_percentile(tool, 99, ...).
0.0 for unknown tool or no recent calls.
Consistent with get_windowed_latency_percentile(tool, 99, ...).

Discriminating tests:
  1. PRIMARY DISC.: lats [10, 20, 30, 40, 50] -> p99=49.6
     (kills p95=48.0; kills max=50.0; idx=0.99*4=3.96 -> 40+0.96*(50-40)=49.6).
  2. Consistent with get_windowed_latency_percentile(tool, 99, ...).
  3. p99 > p95 for the same distribution.
  4. Unknown tool -> 0.0.
  5. Old calls excluded.
  6. Returns float.
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_latency_percentile,
    get_windowed_tool_p95_ms,
    get_windowed_tool_p99_ms,
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


def test_p99_not_p95_not_max_primary_discriminator() -> None:
    """PRIMARY DISC.: lats [10,20,30,40,50] -> p99=49.6 (not p95=48.0, not max=50.0).

    idx = 0.99 * (5-1) = 3.96
    lo=3 (40.0), hi=4 (50.0)
    p99 = 40.0 + 0.96 * (50.0 - 40.0) = 49.6

    Kills impl returning p95=48.0 (wrong percentile).
    Kills impl returning max=50.0 (off by 0.4ms).
    """
    store: dict = {}
    ts = _recent()
    for lat in [50.0, 30.0, 10.0, 40.0, 20.0]:  # unsorted insertion
        _add(store, "t", lat, ts)

    result = get_windowed_tool_p99_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, float)
    assert abs(result - 49.6) < 1e-9, (
        f"p99([10,20,30,40,50]): idx=3.96 -> 49.6; kills p95=48.0 or max=50.0; got {result}"
    )


def test_consistent_with_latency_percentile() -> None:
    """Must equal get_windowed_latency_percentile(tool, 99.0, ...)."""
    store: dict = {}
    ts = _recent()
    for lat in [5.0, 15.0, 25.0, 35.0, 45.0, 80.0, 100.0, 200.0]:
        _add(store, "t", lat, ts)

    shortcut = get_windowed_tool_p99_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    full = get_windowed_latency_percentile("t", 99.0, WINDOW_MS, store=store, now_ms=NOW_MS)

    assert abs(shortcut - full) < 1e-9, (
        f"shortcut={shortcut} must equal latency_percentile(99)={full}"
    )


def test_p99_greater_than_p95() -> None:
    """p99 > p95 for any distribution with distinct values."""
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]:
        _add(store, "t", lat, ts)

    p99 = get_windowed_tool_p99_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    p95 = get_windowed_tool_p95_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)

    assert p99 > p95, f"p99={p99} must be > p95={p95}"


def test_unknown_tool_returns_zero() -> None:
    result = get_windowed_tool_p99_ms("no_such_tool", WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0.0


def test_old_calls_excluded() -> None:
    """Huge old latencies must not pollute p99."""
    store: dict = {}
    for _ in range(10):
        _add(store, "t", 9999.0, _old())
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        _add(store, "t", lat, _recent())

    result = get_windowed_tool_p99_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert abs(result - 49.6) < 1e-9, (
        f"Old excluded; p99([10,20,30,40,50])=49.6; got {result}"
    )


def test_returns_float() -> None:
    store: dict = {}
    _add(store, "t", 42.0, _recent())
    result = get_windowed_tool_p99_ms("t", WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, float), f"Must return float; got {type(result)}"
