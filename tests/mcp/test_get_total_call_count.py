"""Item 943: get_total_call_count() -> int -- total calls across all tools.

PRIMARY DISC.: 3 tools with [5, 3, 2] calls -> 10
(kills impl returning tool count=3 or max=5).
empty -> 0; returns int; pure.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_total_call_count,
    get_tool_count,
)


def _reset():
    clear_telemetry_stores()


def test_sum_not_tool_count_not_max_primary_discriminator() -> None:
    """FALSIFIABLE: 3 tools with [5, 3, 2] calls -> total=10.
    Kills impl returning tool_count=3 or max_calls=5."""
    _reset()
    for _ in range(5):
        record_tool_call("alpha_calls", 10.0, True)
    for _ in range(3):
        record_tool_call("beta_calls", 10.0, True)
    for _ in range(2):
        record_tool_call("gamma_calls", 10.0, True)
    result = get_total_call_count()
    assert result == 10
    assert result != get_tool_count()   # 10 ≠ 3 (tool count)
    assert result != 5                  # not max


def test_empty_store_returns_zero() -> None:
    """No calls -> 0."""
    _reset()
    assert get_total_call_count() == 0


def test_returns_int() -> None:
    """Return type is int."""
    _reset()
    record_tool_call("int_total", 5.0, True)
    assert isinstance(get_total_call_count(), int)


def test_single_tool_many_calls() -> None:
    """100 calls to 1 tool -> 100."""
    _reset()
    for _ in range(100):
        record_tool_call("flood", 5.0, True)
    assert get_total_call_count() == 100


def test_increments_on_each_call() -> None:
    """Counter grows by 1 per call regardless of tool."""
    _reset()
    assert get_total_call_count() == 0
    record_tool_call("t1", 5.0, True)
    assert get_total_call_count() == 1
    record_tool_call("t2", 5.0, True)  # different tool
    assert get_total_call_count() == 2
    record_tool_call("t1", 5.0, True)  # same tool again
    assert get_total_call_count() == 3
