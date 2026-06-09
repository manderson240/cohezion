"""Item 912: get_tool_error_count(tool_name) -> int -- per-tool cumulative error count.

PRIMARY DISC.: tool with 2 success + 3 fail -> error_count=3 (kills impl returning call_count);
unknown tool -> 0 (kills KeyError impl); pure (no mutation).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    _TELEMETRY,
    record_tool_call,
    clear_telemetry_stores,
    get_tool_error_count,
)


def _reset():
    clear_telemetry_stores()


# ── primary discriminator ─────────────────────────────────────────────────────

def test_error_count_not_call_count_primary_discriminator() -> None:
    """FALSIFIABLE: 2 success + 3 fail -> error_count=3, not 5 (call_count).
    Kills impl that returns call_count, or sum-errors-across-tools."""
    _reset()
    for _ in range(2):
        record_tool_call("err3_tool", 10.0, True)
    for _ in range(3):
        record_tool_call("err3_tool", 10.0, False)
    assert get_tool_error_count("err3_tool") == 3


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool returns 0, not KeyError."""
    _reset()
    assert get_tool_error_count("unknown_err_tool") == 0


def test_all_success_returns_zero() -> None:
    """Tool with only successes has error_count=0."""
    _reset()
    for _ in range(4):
        record_tool_call("ok_tool", 10.0, True)
    assert get_tool_error_count("ok_tool") == 0


def test_returns_integer() -> None:
    """Return type must be int."""
    _reset()
    record_tool_call("type_err_tool", 10.0, False)
    result = get_tool_error_count("type_err_tool")
    assert isinstance(result, int)


def test_counts_only_named_tool_errors() -> None:
    """Error count is per-tool, not total errors across all tools."""
    _reset()
    for _ in range(5):
        record_tool_call("noisy_tool", 10.0, False)
    for _ in range(2):
        record_tool_call("quiet_tool", 10.0, False)
    assert get_tool_error_count("quiet_tool") == 2  # not 7 total


def test_does_not_mutate_store() -> None:
    """Calling get_tool_error_count must not modify _TELEMETRY."""
    _reset()
    record_tool_call("pure_err_tool", 10.0, False)
    before = {k: dict(v) for k, v in _TELEMETRY.items()}
    get_tool_error_count("pure_err_tool")
    assert {k: dict(v) for k, v in _TELEMETRY.items()} == before
