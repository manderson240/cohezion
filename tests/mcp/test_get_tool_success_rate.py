"""Item 938: get_tool_success_rate(tool_name) -> float -- success rate (1 - error_rate).

PRIMARY DISC.: 5 calls, 1 error -> 0.8
(kills impl returning error_rate=0.2); unknown -> 1.0
(kills impl returning 0.0 for unknown).
Returns float in [0.0, 1.0]; pure.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_tool_success_rate,
    get_tool_error_rate,
)


def _reset():
    clear_telemetry_stores()


def test_one_minus_error_rate_primary_discriminator() -> None:
    """FALSIFIABLE: 5 calls, 1 error -> success_rate=0.8, error_rate=0.2.
    Kills impl returning error_rate=0.2 instead of 1-error_rate=0.8."""
    _reset()
    for _ in range(4):
        record_tool_call("sr_tool", 10.0, True)
    record_tool_call("sr_tool", 20.0, False)
    result = get_tool_success_rate("sr_tool")
    err_rate = get_tool_error_rate("sr_tool")
    # Confirm error_rate=0.2 so the discriminating property is meaningful
    assert abs(err_rate - 0.2) < 0.001
    # success_rate must be complement, NOT the same as error_rate
    assert abs(result - 0.8) < 0.001
    assert abs(result - err_rate) > 0.1  # they differ: 0.8 ≠ 0.2


def test_unknown_tool_returns_one() -> None:
    """Unknown tool -> 1.0 (no failures seen, so 100% success).
    Kills impl returning 0.0 for unknown."""
    _reset()
    result = get_tool_success_rate("never_seen")
    assert abs(result - 1.0) < 0.001


def test_returns_float() -> None:
    """Return type is float."""
    _reset()
    record_tool_call("float_sr", 5.0, True)
    assert isinstance(get_tool_success_rate("float_sr"), float)


def test_all_success_returns_one() -> None:
    """No errors -> 1.0."""
    _reset()
    for _ in range(3):
        record_tool_call("all_ok_sr", 10.0, True)
    assert abs(get_tool_success_rate("all_ok_sr") - 1.0) < 0.001


def test_all_errors_returns_zero() -> None:
    """All errors -> 0.0."""
    _reset()
    for _ in range(3):
        record_tool_call("all_err_sr", 10.0, False)
    assert abs(get_tool_success_rate("all_err_sr") - 0.0) < 0.001


def test_complements_error_rate() -> None:
    """success_rate + error_rate == 1.0 for known tools."""
    _reset()
    record_tool_call("comp_tool", 10.0, True)
    record_tool_call("comp_tool", 10.0, False)
    record_tool_call("comp_tool", 10.0, True)
    sr = get_tool_success_rate("comp_tool")
    er = get_tool_error_rate("comp_tool")
    assert abs(sr + er - 1.0) < 0.001
