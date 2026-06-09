"""Item 913: get_tool_error_rate(tool_name) -> float -- per-tool error rate.

PRIMARY DISC.: 2 success + 2 fail -> 0.5 (kills impl returning error_count=2 not rate);
0 errors -> 0.0; unknown tool -> 0.0; all-fail -> 1.0; pure.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_tool_error_rate,
)


def _reset():
    clear_telemetry_stores()


def test_rate_not_count_primary_discriminator() -> None:
    """FALSIFIABLE: 2 success + 2 fail -> 0.5, not 2 (error_count).
    Kills impl returning int count instead of float rate."""
    _reset()
    for _ in range(2):
        record_tool_call("rate_tool", 10.0, True)
    for _ in range(2):
        record_tool_call("rate_tool", 10.0, False)
    result = get_tool_error_rate("rate_tool")
    assert abs(result - 0.5) < 0.001
    assert isinstance(result, float)


def test_unknown_tool_returns_zero_float() -> None:
    _reset()
    assert get_tool_error_rate("unknown_rate") == 0.0
    assert isinstance(get_tool_error_rate("unknown_rate"), float)


def test_all_success_returns_zero() -> None:
    _reset()
    for _ in range(5):
        record_tool_call("ok_rate", 10.0, True)
    assert get_tool_error_rate("ok_rate") == 0.0


def test_all_fail_returns_one() -> None:
    _reset()
    for _ in range(3):
        record_tool_call("full_err", 10.0, False)
    assert abs(get_tool_error_rate("full_err") - 1.0) < 0.001


def test_one_in_four_is_point_two_five() -> None:
    _reset()
    for _ in range(3):
        record_tool_call("quart", 10.0, True)
    record_tool_call("quart", 10.0, False)
    assert abs(get_tool_error_rate("quart") - 0.25) < 0.001
