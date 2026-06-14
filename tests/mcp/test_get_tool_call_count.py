"""Item 911: get_tool_call_count(tool_name) -> int -- per-tool cumulative count.

PRIMARY DISC.: tool with 3 calls -> 3 (kills impl returning total across tools);
unknown tool -> 0 (kills impl raising KeyError); cumulative not windowed.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    _TELEMETRY,
    record_tool_call,
    clear_telemetry_stores,
    get_tool_call_count,
)


def _reset():
    clear_telemetry_stores()


# ── primary discriminator ─────────────────────────────────────────────────────


def test_three_calls_returns_three_primary_discriminator() -> None:
    """FALSIFIABLE: tool with 3 calls -> count=3.
    Kills impl that returns total across all tools or always returns 1."""
    _reset()
    for _ in range(3):
        record_tool_call("cnt3_tool", 10.0, True)
    assert get_tool_call_count("cnt3_tool") == 3


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool must return 0, not raise KeyError."""
    _reset()
    assert get_tool_call_count("nonexistent_tool") == 0


def test_returns_integer() -> None:
    """Return type must be int."""
    _reset()
    record_tool_call("type_tool", 5.0, True)
    result = get_tool_call_count("type_tool")
    assert isinstance(result, int)


def test_counts_only_the_named_tool_not_others() -> None:
    """Count is per-tool, not a global total across all tools."""
    _reset()
    for _ in range(5):
        record_tool_call("big_tool", 10.0, True)
    for _ in range(2):
        record_tool_call("small_tool", 10.0, True)
    assert get_tool_call_count("small_tool") == 2  # not 7 total


def test_count_increments_with_each_call() -> None:
    """Count grows by 1 for each record_tool_call."""
    _reset()
    record_tool_call("incr_tool", 10.0, True)
    assert get_tool_call_count("incr_tool") == 1
    record_tool_call("incr_tool", 20.0, False)
    assert get_tool_call_count("incr_tool") == 2


def test_does_not_mutate_store() -> None:
    """Calling get_tool_call_count must not modify _TELEMETRY."""
    _reset()
    record_tool_call("pure_tool", 10.0, True)
    before = dict(_TELEMETRY)
    get_tool_call_count("pure_tool")
    assert dict(_TELEMETRY) == before


def test_error_calls_still_counted() -> None:
    """Failed calls count toward the total just as successful calls do."""
    _reset()
    record_tool_call("err_cnt_tool", 10.0, True)
    record_tool_call("err_cnt_tool", 10.0, False)
    record_tool_call("err_cnt_tool", 10.0, False)
    assert get_tool_call_count("err_cnt_tool") == 3
