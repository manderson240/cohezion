"""Item 963: get_windowed_top_n_tools_by_call_count() -- top-N by windowed call count.

get_windowed_top_n_tools_by_call_count(n, window_ms, *, store=None, now_ms=None) -> list[str]

Returns up to n tool names sorted descending by windowed call count.
Ties broken alphabetically ascending. Empty list when empty or no recent calls.

Discriminating tests:
  1. PRIMARY DISC.: 4 tools with windowed counts [5, 1, 3, 2], n=2 -> [tool_with_5, tool_with_3]
     (kills cumulative-count impl; kills impl ignoring window).
  2. Tool with only old calls excluded.
  3. n=0 -> [].
  4. n > active tools -> all active tools (no padding).
  5. Ties broken alphabetically ascending.
  6. Returns list[str].
  7. Uses _WINDOWED_TELEMETRY singleton by default.
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_top_n_tools_by_call_count,
)

NOW_MS = 100_000.0
WINDOW_MS = 10_000.0


@pytest.fixture(autouse=True)
def _clean():
    _WINDOWED_TELEMETRY.clear()
    yield
    _WINDOWED_TELEMETRY.clear()


def _add(store: dict, tool: str, count: int, ts: float) -> None:
    for _ in range(count):
        store.setdefault(tool, []).append((ts, 10.0, True))


def _recent() -> float:
    return NOW_MS - 5_000.0


def _old() -> float:
    return NOW_MS - WINDOW_MS - 1_000.0


def test_top_n_by_windowed_count_primary_discriminator() -> None:
    """PRIMARY DISC.: 4 tools with windowed counts [5,1,3,2], n=2 -> top 2 correct."""
    store: dict = {}
    ts = _recent()
    _add(store, "d", 5, ts)  # most calls
    _add(store, "a", 1, ts)
    _add(store, "c", 3, ts)  # second
    _add(store, "b", 2, ts)

    result = get_windowed_top_n_tools_by_call_count(2, WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result == ["d", "c"], (
        f"Top 2 by windowed count: d(5), c(3); got {result}"
    )


def test_old_calls_tool_excluded() -> None:
    """Tool with only old calls must NOT appear even if it has huge cumulative count."""
    store: dict = {}
    _add(store, "recent", 3, _recent())
    _add(store, "ancient", 100, _old())  # huge count but outside window

    result = get_windowed_top_n_tools_by_call_count(5, WINDOW_MS, store=store, now_ms=NOW_MS)

    assert "ancient" not in result, f"ancient must be excluded (only old calls); got {result}"
    assert "recent" in result


def test_n_zero_returns_empty() -> None:
    store: dict = {}
    _add(store, "t", 5, _recent())
    result = get_windowed_top_n_tools_by_call_count(0, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == []


def test_n_greater_than_active_tools_returns_all() -> None:
    """n > active tool count -> return all active tools (no padding)."""
    store: dict = {}
    _add(store, "a", 3, _recent())
    _add(store, "b", 1, _recent())
    result = get_windowed_top_n_tools_by_call_count(10, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert len(result) == 2
    assert result[0] == "a"  # higher count first


def test_ties_broken_alphabetically() -> None:
    """Two tools with same windowed count -> alphabetically first comes first."""
    store: dict = {}
    ts = _recent()
    _add(store, "beta", 3, ts)
    _add(store, "alpha", 3, ts)

    result = get_windowed_top_n_tools_by_call_count(2, WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result == ["alpha", "beta"], (
        f"Tied at 3 calls; alphabetical order; got {result}"
    )


def test_empty_store_returns_empty_list() -> None:
    result = get_windowed_top_n_tools_by_call_count(5, WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == []


def test_returns_list() -> None:
    store: dict = {}
    _add(store, "t", 1, _recent())
    result = get_windowed_top_n_tools_by_call_count(1, WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, list)


def test_uses_windowed_telemetry_singleton() -> None:
    _WINDOWED_TELEMETRY["x"] = [(NOW_MS - 5_000.0, 10.0, True)] * 5
    _WINDOWED_TELEMETRY["y"] = [(NOW_MS - 5_000.0, 10.0, True)] * 2
    result = get_windowed_top_n_tools_by_call_count(1, WINDOW_MS, now_ms=NOW_MS)
    assert result == ["x"], f"x has 5 calls vs y's 2; got {result}"
