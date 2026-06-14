"""Item 939: get_slowest_tool() -> str | None -- tool with highest p95 latency.

PRIMARY DISC.: 3 tools with p95=[100, 500, 200] -> the tool with p95=500
(kills impl returning tool with most calls or highest error rate).
empty store -> None; returns str | None; pure.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_slowest_tool,
)


def _reset():
    clear_telemetry_stores()


def test_highest_p95_not_calls_not_errors_primary_discriminator() -> None:
    """FALSIFIABLE: 3 tools with distinct p95s -> the one with p95~500 wins.
    Tool C has the most calls (5) and highest error rate, but lower p95 than B.
    Kills impl returning tool with most calls or highest error rate."""
    _reset()
    # Tool A: 1 call, p95=100ms
    record_tool_call("tool_a", 100.0, True)
    # Tool B: 1 call, p95=500ms (SHOULD WIN)
    record_tool_call("tool_b", 500.0, True)
    # Tool C: 5 calls with errors, p95=200ms (most calls, highest error rate)
    for _ in range(4):
        record_tool_call("tool_c", 200.0, False)  # error
    record_tool_call("tool_c", 180.0, True)
    result = get_slowest_tool()
    assert result == "tool_b"


def test_empty_store_returns_none() -> None:
    """Empty store -> None."""
    _reset()
    assert get_slowest_tool() is None


def test_returns_str_or_none() -> None:
    """Return type is str when store non-empty, None when empty."""
    _reset()
    assert get_slowest_tool() is None
    record_tool_call("typed_tool", 10.0, True)
    result = get_slowest_tool()
    assert isinstance(result, str)


def test_single_tool_returns_it() -> None:
    """Single tool -> that tool's name."""
    _reset()
    record_tool_call("only_tool", 42.0, True)
    assert get_slowest_tool() == "only_tool"


def test_tie_broken_alphabetically() -> None:
    """Equal p95 -> alphabetically first (deterministic)."""
    _reset()
    # Two tools with same single call latency -> same p95
    record_tool_call("zebra", 100.0, True)
    record_tool_call("alpha", 100.0, True)
    result = get_slowest_tool()
    # Both have p95=100; alphabetically "alpha" comes first
    assert result == "alpha"
