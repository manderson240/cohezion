"""Item 937: get_tool_success_count(tool_name) -> int -- successful call count.

PRIMARY DISC.: 5 calls, 2 errors -> 3
(kills impl returning call_count=5, error_count=2, or 0).
unknown -> 0; returns int; pure.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_tool_success_count,
)


def _reset():
    clear_telemetry_stores()


def test_success_not_calls_not_errors_primary_discriminator() -> None:
    """FALSIFIABLE: 5 calls, 2 errors -> success_count=3.
    Kills impl returning call_count=5 or error_count=2."""
    _reset()
    for _ in range(3):
        record_tool_call("sc_tool", 10.0, True)
    for _ in range(2):
        record_tool_call("sc_tool", 20.0, False)
    result = get_tool_success_count("sc_tool")
    assert result == 3
    assert result != 5  # not call_count
    assert result != 2  # not error_count


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0."""
    _reset()
    assert get_tool_success_count("never_seen") == 0


def test_returns_int() -> None:
    """Return type is int."""
    _reset()
    record_tool_call("int_sc", 5.0, True)
    assert isinstance(get_tool_success_count("int_sc"), int)


def test_all_success_equals_call_count() -> None:
    """No errors -> success_count == call_count."""
    _reset()
    for _ in range(4):
        record_tool_call("all_ok", 10.0, True)
    assert get_tool_success_count("all_ok") == 4


def test_all_errors_returns_zero() -> None:
    """All errors -> success_count == 0."""
    _reset()
    for _ in range(3):
        record_tool_call("all_err", 10.0, False)
    assert get_tool_success_count("all_err") == 0
