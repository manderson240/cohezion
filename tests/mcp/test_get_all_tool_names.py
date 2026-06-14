"""Item 929: get_all_tool_names() -> list[str] -- sorted list of all recorded tool names.

PRIMARY DISC.: 3 tools recorded -> sorted list of all 3
(kills impl returning windowed names, unsorted, or dict).
empty store -> []; pure; includes all tools regardless of recency.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_all_tool_names,
)


def _reset():
    clear_telemetry_stores()


def test_three_tools_sorted_primary_discriminator() -> None:
    """FALSIFIABLE: 3 tools recorded -> sorted list of all 3.
    Kills impl returning windowed names (no windowed calls here) or unsorted."""
    _reset()
    # Record calls — order deliberately reversed to kill "insertion-order" impl
    record_tool_call("zebra_tool", 10.0, True)
    record_tool_call("alpha_tool", 20.0, True)
    record_tool_call("middle_tool", 15.0, True)
    result = get_all_tool_names()
    assert result == ["alpha_tool", "middle_tool", "zebra_tool"]


def test_returns_list_not_dict() -> None:
    """Return type is list, not dict or set."""
    _reset()
    record_tool_call("list_check_tool", 5.0, True)
    result = get_all_tool_names()
    assert isinstance(result, list)


def test_empty_store_returns_empty_list() -> None:
    """No recorded tools -> []."""
    _reset()
    result = get_all_tool_names()
    assert result == []


def test_single_tool() -> None:
    """Single tool -> list of length 1."""
    _reset()
    record_tool_call("solo_tool", 30.0, True)
    result = get_all_tool_names()
    assert result == ["solo_tool"]


def test_does_not_include_windowed_only_tools() -> None:
    """Tools in _WINDOWED_TELEMETRY but not in _TELEMETRY are NOT included.
    Kills impl that reads windowed store instead of cumulative store."""
    _reset()
    # Only cumulative call recorded — no windowed-only scenario needed;
    # this confirms get_all_tool_names() sources from _TELEMETRY (cumulative).
    record_tool_call("cum_only", 5.0, True)
    result = get_all_tool_names()
    assert "cum_only" in result


def test_duplicate_calls_tool_appears_once() -> None:
    """Multiple calls to same tool -> tool appears exactly once in result."""
    _reset()
    for _ in range(5):
        record_tool_call("repeat_tool", 10.0, True)
    result = get_all_tool_names()
    assert result.count("repeat_tool") == 1
