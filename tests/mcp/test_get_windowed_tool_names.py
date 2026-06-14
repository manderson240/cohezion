"""Item 928: get_windowed_tool_names(window_ms, *, now_ms=None) -> list[str].

PRIMARY DISC.: 2 active + 1 stale -> sorted list of 2 active tool names
  (kills impl returning all tool names or unsorted);
empty store -> []; returns sorted list.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_names,
)

NOW = 80_000.0


def _reset():
    clear_telemetry_stores()


def test_stale_tool_excluded_sorted_result_primary_discriminator() -> None:
    """FALSIFIABLE: 2 active + 1 stale -> sorted list of 2 active.
    Kills impl including all tools or returning unsorted."""
    _reset()
    store: dict = {
        "beta_tool": [(NOW - 500, 10.0, True)],  # active
        "alpha_tool": [(NOW - 300, 20.0, True)],  # active
        "stale_tool": [(NOW - 9000, 5.0, True)],  # outside 5000ms window
    }
    result = get_windowed_tool_names(window_ms=5000.0, store=store, now_ms=NOW)
    assert result == ["alpha_tool", "beta_tool"]  # sorted, stale excluded


def test_empty_store_returns_empty_list() -> None:
    _reset()
    store: dict = {}
    assert get_windowed_tool_names(window_ms=5000.0, store=store, now_ms=NOW) == []


def test_all_tools_stale_returns_empty() -> None:
    _reset()
    store: dict = {
        "old1": [(NOW - 99000, 5.0, True)],
        "old2": [(NOW - 50000, 5.0, True)],
    }
    result = get_windowed_tool_names(window_ms=1000.0, store=store, now_ms=NOW)
    assert result == []


def test_single_active_tool() -> None:
    _reset()
    store: dict = {"my_tool": [(NOW - 100, 15.0, True)]}
    result = get_windowed_tool_names(window_ms=5000.0, store=store, now_ms=NOW)
    assert result == ["my_tool"]


def test_returns_sorted_list() -> None:
    """All active tools must be sorted alphabetically."""
    _reset()
    store: dict = {
        "z_tool": [(NOW - 100, 5.0, True)],
        "a_tool": [(NOW - 200, 5.0, True)],
        "m_tool": [(NOW - 300, 5.0, True)],
    }
    result = get_windowed_tool_names(window_ms=5000.0, store=store, now_ms=NOW)
    assert result == sorted(result)
    assert len(result) == 3
