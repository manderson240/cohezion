"""Item 941: get_fastest_tool() -> str | None --
tool with the lowest p50 latency.

PRIMARY DISC.: 3 tools with p50=[50, 10, 30] -> tool with p50=10
(kills impl returning lowest p95, most-called, or slowest).
empty -> None; ties alphabetical; returns str | None; pure.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_fastest_tool,
)


def _reset():
    clear_telemetry_stores()


def test_lowest_p50_not_slowest_not_most_calls_primary_discriminator() -> None:
    """FALSIFIABLE: 3 tools. Tool A has most calls (5) and tool C is slow.
    Tool B is fastest (p50=10). -> B wins."""
    _reset()
    # Tool A: many calls, p50=50 (busy but not fastest)
    for _ in range(5):
        record_tool_call("tool_a_busy", 50.0, True)
    # Tool B: single call, p50=10 (SHOULD WIN — fastest)
    record_tool_call("tool_b_fast", 10.0, True)
    # Tool C: single call, p50=30
    record_tool_call("tool_c_slow", 30.0, True)
    result = get_fastest_tool()
    assert result == "tool_b_fast"


def test_empty_store_returns_none() -> None:
    """Empty store -> None."""
    _reset()
    assert get_fastest_tool() is None


def test_returns_str_not_none_when_nonempty() -> None:
    """Non-empty store -> returns str."""
    _reset()
    record_tool_call("typed_fast", 5.0, True)
    result = get_fastest_tool()
    assert isinstance(result, str)


def test_single_tool_returns_it() -> None:
    """Single tool -> that tool."""
    _reset()
    record_tool_call("only_fast", 42.0, True)
    assert get_fastest_tool() == "only_fast"


def test_tie_broken_alphabetically() -> None:
    """Equal p50 -> alphabetically first."""
    _reset()
    # Both have single call at same latency -> same p50
    record_tool_call("zebra_fast", 10.0, True)
    record_tool_call("alpha_fast", 10.0, True)
    result = get_fastest_tool()
    assert result == "alpha_fast"  # alphabetically first
