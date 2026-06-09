"""Item 942: get_busiest_tool() -> str | None --
tool with the most calls.

PRIMARY DISC.: 3 tools with call_counts=[3, 10, 5] -> tool with count=10
(kills impl returning slowest or most error-prone).
empty -> None; ties alphabetical; returns str | None; pure.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_busiest_tool,
)


def _reset():
    clear_telemetry_stores()


def test_most_calls_not_slowest_not_error_prone_primary_discriminator() -> None:
    """FALSIFIABLE: 3 tools. Tool A=slowest (p95=500), Tool B=most errors (100%),
    Tool C=most calls (10). -> C wins.
    Kills impl returning slowest or most error-prone tool."""
    _reset()
    # Tool A: slow (p95=500) but few calls
    for _ in range(3):
        record_tool_call("tool_a_slow", 500.0, True)
    # Tool B: all errors but few calls
    for _ in range(5):
        record_tool_call("tool_b_errors", 10.0, False)
    # Tool C: most calls (10), low latency, few errors -- SHOULD WIN
    for _ in range(10):
        record_tool_call("tool_c_busy", 5.0, True)
    result = get_busiest_tool()
    assert result == "tool_c_busy"


def test_empty_store_returns_none() -> None:
    """Empty store -> None."""
    _reset()
    assert get_busiest_tool() is None


def test_returns_str_when_nonempty() -> None:
    """Non-empty -> str."""
    _reset()
    record_tool_call("one", 5.0, True)
    assert isinstance(get_busiest_tool(), str)


def test_single_tool_returns_it() -> None:
    """Single tool -> that tool."""
    _reset()
    record_tool_call("sole_busy", 10.0, True)
    assert get_busiest_tool() == "sole_busy"


def test_tie_broken_alphabetically() -> None:
    """Equal call counts -> alphabetically first."""
    _reset()
    for _ in range(3):
        record_tool_call("zebra_busy", 5.0, True)
    for _ in range(3):
        record_tool_call("ant_busy", 5.0, True)
    result = get_busiest_tool()
    assert result == "ant_busy"  # alphabetically first
