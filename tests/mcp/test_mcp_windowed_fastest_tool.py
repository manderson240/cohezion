"""Item 959: get_windowed_fastest_tool() -- tool with lowest windowed p50.

Discriminating tests:
  1. PRIMARY DISC.: 3 tools with windowed p50s [200, 5, 50]ms -> tool with p50=5 wins
     (kills impl returning alphabetically-first tool regardless of p50).
  2. Ties broken alphabetically ascending.
  3. Empty store -> None.
  4. Old calls excluded.
  5. Single tool -> that tool.
  6. Returns str (or None).
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_windowed_fastest_tool,
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


def test_lowest_p50_wins_primary_discriminator() -> None:
    """PRIMARY DISC.: 3 tools, windowed p50s [200, 5, 50] -> tool with p50=5."""
    store: dict = {}
    ts = _recent()
    # tool "a": lats=[200, 200] -> p50=200
    _add(store, "a", [200.0, 200.0], ts)
    # tool "b": lats=[5, 5] -> p50=5
    _add(store, "b", [5.0, 5.0], ts)
    # tool "c": lats=[50, 50] -> p50=50
    _add(store, "c", [50.0, 50.0], ts)

    result = get_windowed_fastest_tool(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result == "b", (
        f"Tool b has lowest p50=5; got {result!r}"
    )


def test_ties_broken_alphabetically() -> None:
    """Two tools with identical p50 -> alphabetically first returned."""
    store: dict = {}
    ts = _recent()
    _add(store, "beta", [10.0, 10.0], ts)
    _add(store, "alpha", [10.0, 10.0], ts)

    result = get_windowed_fastest_tool(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert result == "alpha", (
        f"Tied at p50=10; alphabetically first='alpha'; got {result!r}"
    )


def test_empty_store_returns_none() -> None:
    result = get_windowed_fastest_tool(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result is None


def test_old_calls_excluded() -> None:
    """Tool with only old records is invisible; only recent records count."""
    store: dict = {}
    _add(store, "slow", [1000.0], _recent())
    _add(store, "fast", [1.0], _old())  # old -> excluded

    result = get_windowed_fastest_tool(WINDOW_MS, store=store, now_ms=NOW_MS)

    # only "slow" has recent records; "fast"'s record is outside window
    assert result == "slow", (
        f"Only 'slow' has recent calls; got {result!r}"
    )


def test_single_tool_returns_itself() -> None:
    store: dict = {}
    _add(store, "only", [42.0], _recent())
    result = get_windowed_fastest_tool(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == "only"


def test_returns_str_or_none_type() -> None:
    store: dict = {}
    _add(store, "t", [10.0], _recent())
    result = get_windowed_fastest_tool(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, str)


def test_uses_windowed_telemetry_singleton() -> None:
    """Default store= uses _WINDOWED_TELEMETRY."""
    _WINDOWED_TELEMETRY["x"] = [(NOW_MS - 5_000.0, 7.0, True)]
    _WINDOWED_TELEMETRY["y"] = [(NOW_MS - 5_000.0, 100.0, True)]
    result = get_windowed_fastest_tool(WINDOW_MS, now_ms=NOW_MS)
    assert result == "x", f"x has lower p50=7; got {result!r}"
