"""Item 959: get_windowed_fastest_tool(window_ms, *, store=None, now_ms=None) -> str | None
-- tool with the lowest windowed p50 latency.

PRIMARY DISC.: 3 tools with windowed p50s [200, 5, 50]ms -> tool with p50=5 wins.
Kills impl returning alphabetically first tool regardless of p50.
Kills impl computing cumulative p50 instead of windowed p50.
Ties broken alphabetically. None when empty. Returns str | None.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_fastest_tool,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_lowest_windowed_p50_wins_primary_discriminator() -> None:
    """FALSIFIABLE: tool a=200ms p50, tool b=5ms p50, tool c=50ms p50.
    'b' has the lowest p50 -> b wins.
    Kills impl returning alphabetically first; kills cumulative-p50 impl."""
    _reset()
    store = _make_store({
        "wft_a": [(_NOW - 10, 200.0, True)],  # p50 = 200.0
        "wft_b": [(_NOW - 10, 5.0, True)],    # p50 = 5.0  (fastest)
        "wft_c": [(_NOW - 10, 50.0, True)],   # p50 = 50.0
    })
    result = get_windowed_fastest_tool(_WIN, store=store, now_ms=_NOW)
    assert result == "wft_b"
    assert result != "wft_a"   # alphabetically first but slowest


def test_empty_store_returns_none() -> None:
    """No tools -> None."""
    _reset()
    assert get_windowed_fastest_tool(_WIN, store={}, now_ms=_NOW) is None


def test_no_recent_calls_returns_none() -> None:
    """All calls outside window -> None."""
    store = _make_store({
        "wft_old": [(_NOW - _WIN - 100, 5.0, True)],
    })
    assert get_windowed_fastest_tool(_WIN, store=store, now_ms=_NOW) is None


def test_tie_broken_alphabetically() -> None:
    """Two tools with equal windowed p50 -> alphabetically first wins."""
    store = _make_store({
        "zzz_fast": [(_NOW - 10, 1.0, True)],
        "aaa_fast": [(_NOW - 10, 1.0, True)],
    })
    result = get_windowed_fastest_tool(_WIN, store=store, now_ms=_NOW)
    assert result == "aaa_fast"


def test_single_tool_returns_that_tool() -> None:
    """Single tool with recent calls -> that tool."""
    store = _make_store({
        "only_wft": [(_NOW - 10, 42.0, True)],
    })
    assert get_windowed_fastest_tool(_WIN, store=store, now_ms=_NOW) == "only_wft"


def test_old_calls_not_considered_in_p50() -> None:
    """Tool with old fast calls and recent slow calls should use windowed p50."""
    store = _make_store({
        "wft_recently_slow": [
            (_NOW - _WIN - 10, 1.0, True),   # old fast -- ignored
            (_NOW - 10, 300.0, True),          # recent slow
        ],
        "wft_recent_fast": [(_NOW - 10, 10.0, True)],
    })
    result = get_windowed_fastest_tool(_WIN, store=store, now_ms=_NOW)
    # wft_recently_slow has windowed p50=300; wft_recent_fast has windowed p50=10
    assert result == "wft_recent_fast"
