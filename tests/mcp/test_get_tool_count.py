"""Item 930: get_tool_count() -> int -- total number of distinct tools recorded.

PRIMARY DISC.: 5 calls across 3 tools -> 3 (kills impl counting total calls).
empty -> 0; returns int; pure.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_tool_count,
)


def _reset():
    clear_telemetry_stores()


def test_calls_vs_distinct_primary_discriminator() -> None:
    """FALSIFIABLE: 5 calls across 3 distinct tools -> 3 (NOT 5).
    Kills impl that counts total calls instead of distinct tools."""
    _reset()
    record_tool_call("alpha", 10.0, True)
    record_tool_call("alpha", 20.0, True)  # 2nd call to same tool
    record_tool_call("beta", 15.0, True)
    record_tool_call("gamma", 30.0, True)
    record_tool_call("gamma", 5.0, False)  # 5th call, 3rd distinct tool
    result = get_tool_count()
    assert result == 3  # 3 distinct, NOT 5 total calls


def test_empty_store_returns_zero() -> None:
    """No calls recorded -> 0."""
    _reset()
    assert get_tool_count() == 0


def test_returns_int() -> None:
    """Return type is int."""
    _reset()
    record_tool_call("typecheck_tool", 5.0, True)
    result = get_tool_count()
    assert isinstance(result, int)


def test_single_tool_many_calls() -> None:
    """100 calls to 1 tool -> count=1."""
    _reset()
    for _ in range(100):
        record_tool_call("single_flood", 10.0, True)
    assert get_tool_count() == 1


def test_increments_on_new_tool() -> None:
    """Each new distinct tool increments the count."""
    _reset()
    assert get_tool_count() == 0
    record_tool_call("t1", 5.0, True)
    assert get_tool_count() == 1
    record_tool_call("t1", 5.0, True)  # repeat — count unchanged
    assert get_tool_count() == 1
    record_tool_call("t2", 5.0, True)  # new tool
    assert get_tool_count() == 2
