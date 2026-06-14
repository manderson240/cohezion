"""Item 957: get_windowed_busiest_tool(window_ms, *, store=None, now_ms=None) -> str | None
-- tool with the most calls in the recent window.

PRIMARY DISC.: 3 tools with [1, 5, 3] windowed calls -> tool with 5 calls wins.
Kills impl returning alphabetically first tool regardless of count.
Ties broken alphabetically. None when empty. Returns str | None.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_busiest_tool,
)

_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_highest_windowed_count_wins_primary_discriminator() -> None:
    """FALSIFIABLE: tool a=1 call, tool b=5 calls, tool c=3 calls.
    'b' has 5 calls -> b wins.
    Kills impl returning alphabetically first tool regardless of count."""
    _reset()
    store = _make_store(
        {
            "wbt_a": [(_NOW - 10, 5.0, True)] * 1,
            "wbt_b": [(_NOW - 10, 5.0, True)] * 5,
            "wbt_c": [(_NOW - 10, 5.0, True)] * 3,
        }
    )
    result = get_windowed_busiest_tool(_WIN, store=store, now_ms=_NOW)
    assert result == "wbt_b"  # 5 calls wins
    assert result != "wbt_a"  # alphabetically first but only 1 call


def test_empty_store_returns_none() -> None:
    """No tools -> None."""
    _reset()
    assert get_windowed_busiest_tool(_WIN, store={}, now_ms=_NOW) is None


def test_no_recent_calls_returns_none() -> None:
    """All calls outside window -> None."""
    store = _make_store(
        {
            "wbt_old": [(_NOW - _WIN - 100, 5.0, True)],
        }
    )
    assert get_windowed_busiest_tool(_WIN, store=store, now_ms=_NOW) is None


def test_tie_broken_alphabetically() -> None:
    """Two tools with equal windowed counts -> alphabetically first wins."""
    store = _make_store(
        {
            "zzz": [(_NOW - 10, 5.0, True)] * 3,
            "aaa": [(_NOW - 10, 5.0, True)] * 3,
        }
    )
    result = get_windowed_busiest_tool(_WIN, store=store, now_ms=_NOW)
    assert result == "aaa"  # alphabetically first among tied tools


def test_single_tool_returns_that_tool() -> None:
    """Single tool with recent calls -> that tool."""
    store = _make_store(
        {
            "solo_wbt": [(_NOW - 10, 5.0, True)] * 2,
        }
    )
    assert get_windowed_busiest_tool(_WIN, store=store, now_ms=_NOW) == "solo_wbt"


def test_out_of_window_calls_not_counted() -> None:
    """Old calls don't count toward windowed busiest calculation."""
    store = _make_store(
        {
            "wbt_old_heavy": [
                (_NOW - _WIN - 10, 5.0, True),  # outside window
                (_NOW - _WIN - 10, 5.0, True),  # outside window
                (_NOW - _WIN - 10, 5.0, True),  # outside window
                (_NOW - 10, 5.0, True),  # inside window: 1 recent
            ],
            "wbt_new": [(_NOW - 10, 5.0, True)] * 2,  # inside window: 2 recent
        }
    )
    result = get_windowed_busiest_tool(_WIN, store=store, now_ms=_NOW)
    assert result == "wbt_new"  # only 2 recent calls vs 1 recent call
