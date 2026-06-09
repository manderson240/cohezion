"""Item 940: get_most_error_prone_tool() -> str | None --
tool with the highest error rate.

PRIMARY DISC.: 3 tools with error_rates=[0.1, 0.5, 0.2] -> tool with rate=0.5
(kills impl returning slowest tool or most-called tool).
empty -> None; ties alphabetical; returns str | None; pure.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_most_error_prone_tool,
)


def _reset():
    clear_telemetry_stores()


def test_highest_error_rate_not_slowest_not_most_calls_primary_discriminator() -> None:
    """FALSIFIABLE: 3 tools. Tool A=slowest (p95=500), Tool B=most calls (10),
    Tool C=highest error rate (0.5). -> C wins.
    Kills impl returning slowest or most-called tool."""
    _reset()
    # Tool A: slow but low error rate (1 call, 1 success, p95=500ms)
    record_tool_call("tool_a_slow", 500.0, True)
    # Tool B: most calls but low error rate
    for _ in range(10):
        record_tool_call("tool_b_busy", 5.0, True)
    # Tool C: highest error rate (2 calls, 1 fail = 0.5 error rate) -- SHOULD WIN
    record_tool_call("tool_c_errors", 10.0, True)
    record_tool_call("tool_c_errors", 10.0, False)
    result = get_most_error_prone_tool()
    assert result == "tool_c_errors"


def test_empty_store_returns_none() -> None:
    """Empty store -> None."""
    _reset()
    assert get_most_error_prone_tool() is None


def test_returns_str_or_none() -> None:
    """Return type is str when store non-empty, None when empty."""
    _reset()
    assert get_most_error_prone_tool() is None
    record_tool_call("typed_err", 5.0, False)
    result = get_most_error_prone_tool()
    assert isinstance(result, str)


def test_all_success_still_returns_a_tool() -> None:
    """All tools with 0% error rate -> returns one (alphabetically first)."""
    _reset()
    record_tool_call("bravo", 5.0, True)
    record_tool_call("alpha", 5.0, True)
    result = get_most_error_prone_tool()
    assert result == "alpha"  # both 0%, alphabetically first


def test_tie_broken_alphabetically() -> None:
    """Equal error rates -> alphabetically first."""
    _reset()
    # Both 0.5 error rate
    record_tool_call("zoo", 10.0, True)
    record_tool_call("zoo", 10.0, False)
    record_tool_call("ant", 10.0, True)
    record_tool_call("ant", 10.0, False)
    result = get_most_error_prone_tool()
    assert result == "ant"  # alphabetically first
