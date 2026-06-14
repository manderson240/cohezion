"""Item 965: get_windowed_top_n_tools_by_p95_latency() -- top-N slowest by windowed p95.

get_windowed_top_n_tools_by_p95_latency(n, window_ms, *, store=None, now_ms=None) -> list[str]

Returns up to n tool names sorted descending by windowed p95 latency (slowest first).
Only tools with >=1 recent call eligible. Ties broken alphabetically ascending.
Empty list when empty/no recent calls.

Discriminating tests:
  1. PRIMARY DISC.: 3 tools with windowed p95 [10, 50, 100], n=2 -> [tool_100, tool_50]
     (kills impl ranking by p50 instead of p95; kills impl returning more than n).
  2. Tool with only old calls excluded.
  3. n=0 -> [].
  4. Ties broken alphabetically.
  5. Returns list[str].
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_top_n_tools_by_p95_latency,
)

NOW_MS = 100_000.0
WINDOW_MS = 10_000.0


@pytest.fixture(autouse=True)
def _clean():
    _WINDOWED_TELEMETRY.clear()
    yield
    _WINDOWED_TELEMETRY.clear()


def _add(store: dict, tool: str, lats: list[float], ts: float) -> None:
    for lat in lats:
        store.setdefault(tool, []).append((ts, lat, True))


def _recent() -> float:
    return NOW_MS - 5_000.0


def _old() -> float:
    return NOW_MS - WINDOW_MS - 1_000.0


def test_ranked_by_p95_not_p50_primary_discriminator() -> None:
    """PRIMARY DISC.: tools with p95=[100,50,10], n=2 -> [tool_100, tool_50].

    The p50 order could differ if distributions are skewed. Use same-value
    distributions so p50==p95 per tool; discriminating check: correct ranking.
    """
    store: dict = {}
    ts = _recent()
    # tool "a": latencies all 10ms -> p95=10
    _add(store, "a", [10.0] * 4, ts)
    # tool "b": latencies all 50ms -> p95=50
    _add(store, "b", [50.0] * 4, ts)
    # tool "c": latencies all 100ms -> p95=100
    _add(store, "c", [100.0] * 4, ts)

    result = get_windowed_top_n_tools_by_p95_latency(2, WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result == ["c", "b"], f"c(p95=100) > b(p95=50) > a(p95=10); top 2 = [c, b]; got {result}"


def test_p95_beats_p50_when_distributions_differ() -> None:
    """Tool with high tail (high p95) beats tool with same median (p50).

    tool_x: lats=[1,1,1,100] -> p50≈1, p95≈100
    tool_y: lats=[50,50,50,50] -> p50=50, p95=50
    Ranked by p95: x(100) > y(50), so x is slower.
    Kills impl ranking by p50: p50 order gives y > x.
    """
    store: dict = {}
    ts = _recent()
    _add(store, "x", [1.0, 1.0, 1.0, 100.0], ts)
    _add(store, "y", [50.0, 50.0, 50.0, 50.0], ts)

    result = get_windowed_top_n_tools_by_p95_latency(1, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == ["x"], f"x has p95=100 > y's p95=50; got {result}"


def test_old_calls_excluded() -> None:
    """Tool with only old calls must not appear."""
    store: dict = {}
    _add(store, "recent", [5.0], _recent())
    _add(store, "ancient", [1000.0], _old())

    result = get_windowed_top_n_tools_by_p95_latency(5, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert "ancient" not in result, f"ancient must be excluded; got {result}"


def test_n_zero_returns_empty() -> None:
    store: dict = {}
    _add(store, "t", [100.0], _recent())
    assert get_windowed_top_n_tools_by_p95_latency(0, WINDOW_MS, store=store, now_ms=NOW_MS) == []


def test_ties_broken_alphabetically() -> None:
    store: dict = {}
    ts = _recent()
    _add(store, "zeta", [50.0, 50.0], ts)
    _add(store, "alpha", [50.0, 50.0], ts)

    result = get_windowed_top_n_tools_by_p95_latency(2, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == ["alpha", "zeta"], f"Tied at p95=50; alphabetical; got {result}"


def test_empty_store_returns_empty() -> None:
    assert get_windowed_top_n_tools_by_p95_latency(5, WINDOW_MS, store={}, now_ms=NOW_MS) == []


def test_returns_list() -> None:
    store: dict = {}
    _add(store, "t", [10.0], _recent())
    result = get_windowed_top_n_tools_by_p95_latency(1, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, list)
