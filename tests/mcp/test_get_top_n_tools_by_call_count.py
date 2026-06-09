"""Item 918: get_top_n_tools_by_call_count(n) -> list[str] -- top-N busiest tools.

PRIMARY DISC.: three tools [5,3,1] calls, n=2 -> 2 busiest in correct order
(kills impl returning all tools or wrong order);
n=0 -> []; fewer tools than n -> all returned.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_top_n_tools_by_call_count,
)


def _reset():
    clear_telemetry_stores()


def test_top_n_correct_order_primary_discriminator() -> None:
    """FALSIFIABLE: three tools with counts [5,3,1], n=2 -> the two busiest.
    Kills impl returning all tools or wrong order."""
    _reset()
    for _ in range(5):
        record_tool_call("busy_tool", 10.0, True)
    for _ in range(3):
        record_tool_call("mid_tool", 10.0, True)
    record_tool_call("quiet_tool", 10.0, True)
    result = get_top_n_tools_by_call_count(2)
    assert result == ["busy_tool", "mid_tool"]  # descending call count
    assert "quiet_tool" not in result


def test_n_zero_returns_empty_list() -> None:
    """n=0 -> [] (no items requested)."""
    _reset()
    record_tool_call("some_tool", 10.0, True)
    assert get_top_n_tools_by_call_count(0) == []


def test_fewer_tools_than_n_returns_all() -> None:
    """Fewer tools than n -> return all (no IndexError)."""
    _reset()
    record_tool_call("only_tool", 10.0, True)
    result = get_top_n_tools_by_call_count(100)
    assert result == ["only_tool"]


def test_empty_store_returns_empty_list() -> None:
    """Empty store -> []."""
    _reset()
    assert get_top_n_tools_by_call_count(5) == []


def test_tie_broken_alphabetically() -> None:
    """Ties in call_count broken by tool name ascending (deterministic)."""
    _reset()
    record_tool_call("zebra_tool", 10.0, True)
    record_tool_call("apple_tool", 10.0, True)
    record_tool_call("mango_tool", 10.0, True)
    result = get_top_n_tools_by_call_count(3)
    # All have count=1; sorted alphabetically for tie-breaking
    assert result == ["apple_tool", "mango_tool", "zebra_tool"]
