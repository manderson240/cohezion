"""Item 1005: get_windowed_global_slow_call_count() — fleet-wide SLO slow-call count.

get_windowed_global_slow_call_count(window_ms, threshold_ms, *, store=None, now_ms=None) -> int

Pools ALL tools. Counts calls with latency STRICTLY > threshold_ms in window.
Dual of get_windowed_tool_slow_call_count (item 1003).

Discriminating tests:
  1. PRIMARY DISC.: tool_a [10, 200] + tool_b [300, 50] threshold=100 -> 2
       (kills per-tool max=1: each tool has only 1 slow call; fleet total=2 pools them)
  2. MULTI-TOOL POOL: 3 tools with counts [3, 1, 0] -> 4 (kills max-per-tool=3)
  3. Strictly >: lat=100 not counted (kills >= implementations)
  4. Old calls excluded.
  5. Empty store -> 0.
  6. Returns int.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_slow_call_count,
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


def test_primary_discriminator_kills_per_tool_max() -> None:
    """PRIMARY DISC.: tool_a[10,200] + tool_b[300,50] threshold=100 -> 2.

    Each tool contributes exactly 1 slow call.
    A wrong impl returning max-per-tool would return 1 (since each tool=1).
    The correct pooled count is 2.
    """
    store: dict = {}
    ts = _recent()
    for lat in [10.0, 200.0]:
        _add(store, "gsc_a", lat, ts)
    for lat in [300.0, 50.0]:
        _add(store, "gsc_b", lat, ts)

    result = get_windowed_global_slow_call_count(WINDOW_MS, 100.0, store=store, now_ms=NOW_MS)

    assert isinstance(result, int)
    assert result == 2, f"tool_a.200 + tool_b.300 = 2 slow; kills per-tool-max=1; got {result}"


def test_multi_tool_pool_discriminator() -> None:
    """MULTI-TOOL POOL: 3 tools contributing [3, 1, 0] slow calls -> 4.

    Kills any impl using max-per-tool=3 or count-of-contributing-tools=2.
    """
    store: dict = {}
    ts = _recent()
    # tool_c_a: 3 slow (200, 300, 500 > 100)
    for lat in [200.0, 300.0, 500.0]:
        _add(store, "gsc_c_a", lat, ts)
    # tool_c_b: 1 slow (150 > 100) + 1 fast (50)
    for lat in [150.0, 50.0]:
        _add(store, "gsc_c_b", lat, ts)
    # tool_c_c: 0 slow (10, 20 <= 100)
    for lat in [10.0, 20.0]:
        _add(store, "gsc_c_c", lat, ts)

    result = get_windowed_global_slow_call_count(WINDOW_MS, 100.0, store=store, now_ms=NOW_MS)

    assert result == 4, (
        f"pool: tool_a=3 + tool_b=1 + tool_c=0 = 4; kills max-per-tool=3; got {result}"
    )


def test_strictly_greater_than_threshold() -> None:
    """Lat=100 exactly at threshold=100 is NOT slow (strictly >).

    Kills >= implementations (would count 100.0 as slow).
    """
    store: dict = {}
    ts = _recent()
    for _ in range(5):
        _add(store, "gsc_exact", 100.0, ts)
    _add(store, "gsc_exact", 100.01, ts)

    result = get_windowed_global_slow_call_count(WINDOW_MS, 100.0, store=store, now_ms=NOW_MS)

    assert result == 1, f"5 calls at exactly 100ms (not slow) + 1 at 100.01ms -> 1; got {result}"


def test_old_calls_excluded() -> None:
    """Old slow calls outside the window must not be counted."""
    store: dict = {}
    for _ in range(10):
        _add(store, "gsc_old", 9999.0, _old())
    for lat in [10.0, 20.0, 30.0]:
        _add(store, "gsc_old", lat, _recent())

    result = get_windowed_global_slow_call_count(WINDOW_MS, 100.0, store=store, now_ms=NOW_MS)

    assert result == 0, f"Old excluded; all recent < 100ms -> 0; got {result}"


def test_empty_store_returns_zero() -> None:
    assert get_windowed_global_slow_call_count(WINDOW_MS, 100.0, store={}, now_ms=NOW_MS) == 0


def test_returns_int() -> None:
    store: dict = {}
    _add(store, "gsc_rt", 200.0, _recent())
    result = get_windowed_global_slow_call_count(WINDOW_MS, 100.0, store=store, now_ms=NOW_MS)
    assert isinstance(result, int), f"Must return int; got {type(result)}"
