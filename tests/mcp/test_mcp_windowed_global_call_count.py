"""Item 954: get_windowed_global_call_count() -- total calls across all tools in window.

get_windowed_global_call_count(window_ms, *, store=None, now_ms=None) -> int

Counts all records in _WINDOWED_TELEMETRY within the last window_ms ms
across ALL tools. 0 when no recent calls. Returns int.

Discriminating tests:
  1. PRIMARY DISC.: 3 tools with [2,3,1] recent calls -> 6
     (kills impl returning tool_count=3 or max_per_tool=3).
  2. Empty store -> 0.
  3. Old calls outside window excluded.
  4. Returns int not float.
  5. Single tool matches per-tool windowed call count.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_global_call_count,
)

NOW_MS = 100_000.0
WINDOW_MS = 10_000.0


@pytest.fixture(autouse=True)
def _clean():
    _WINDOWED_TELEMETRY.clear()
    yield
    _WINDOWED_TELEMETRY.clear()


def _add(store: dict, tool: str, ts: float) -> None:
    store.setdefault(tool, []).append((ts, 10.0, True))


def _recent() -> float:
    return NOW_MS - 5_000.0


def _old() -> float:
    return NOW_MS - WINDOW_MS - 1_000.0


def test_sums_across_tools_primary_discriminator() -> None:
    """PRIMARY DISC.: 3 tools, [2,3,1] recent calls -> total=6.

    Kills impl returning tool_count=3 or max_tool_count=3.
    """
    store: dict = {}
    for _ in range(2):
        _add(store, "a", _recent())
    for _ in range(3):
        _add(store, "b", _recent())
    _add(store, "c", _recent())

    result = get_windowed_global_call_count(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 6, f"2+3+1=6; got {result}"


def test_empty_store_returns_zero() -> None:
    result = get_windowed_global_call_count(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == 0, f"Empty -> 0; got {result}"


def test_old_calls_excluded() -> None:
    store: dict = {}
    _add(store, "t", _old())
    result = get_windowed_global_call_count(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == 0, f"Old calls excluded -> 0; got {result}"


def test_returns_int_not_float() -> None:
    store: dict = {}
    _add(store, "t", _recent())
    result = get_windowed_global_call_count(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, int), f"Must be int; got {type(result)}"


def test_uses_windowed_telemetry_by_default() -> None:
    _WINDOWED_TELEMETRY["x"] = [(NOW_MS - 5_000.0, 10.0, True)] * 4
    result = get_windowed_global_call_count(WINDOW_MS, now_ms=NOW_MS)
    assert result == 4, f"4 calls in singleton -> 4; got {result}"
