"""Item 944: get_total_error_count() -> int -- total errors across all tools.

PRIMARY DISC.: 3 tools with [2, 0, 1] errors -> 3
(kills impl returning total_call_count or tool_count).
empty -> 0; returns int; pure.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_total_error_count,
    get_total_call_count,
    get_tool_count,
)


def _reset():
    clear_telemetry_stores()


def test_sum_errors_not_calls_not_tools_primary_discriminator() -> None:
    """FALSIFIABLE: 2 tools, 8 total calls, 3 total errors -> error_count=3.
    Kills impl returning total_calls=8 or tool_count=2."""
    _reset()
    # Tool A: 5 calls, 2 errors
    for _ in range(2):
        record_tool_call("err_a", 10.0, False)
    for _ in range(3):
        record_tool_call("err_a", 5.0, True)
    # Tool B: 3 calls, 1 error
    record_tool_call("err_b", 10.0, True)
    record_tool_call("err_b", 10.0, True)
    record_tool_call("err_b", 10.0, False)
    result = get_total_error_count()
    assert result == 3
    assert result != get_total_call_count()  # 3 ≠ 8 (total calls)
    assert result != get_tool_count()  # 3 ≠ 2 (tool count)


def test_empty_store_returns_zero() -> None:
    """No calls -> 0."""
    _reset()
    assert get_total_error_count() == 0


def test_returns_int() -> None:
    """Return type is int."""
    _reset()
    record_tool_call("int_err", 5.0, True)
    assert isinstance(get_total_error_count(), int)


def test_all_success_returns_zero() -> None:
    """No failures -> 0."""
    _reset()
    for _ in range(5):
        record_tool_call("clean", 5.0, True)
    assert get_total_error_count() == 0


def test_all_failures_equals_total_calls() -> None:
    """All calls failing -> error_count == total_call_count."""
    _reset()
    for _ in range(4):
        record_tool_call("bad", 5.0, False)
    assert get_total_error_count() == get_total_call_count() == 4
