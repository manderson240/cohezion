"""Item 920: get_top_n_tools_by_p95_ms(n) -> list[str] -- top-N highest-p95 tools.

PRIMARY DISC.: three tools with p95 [100ms, 50ms, 10ms], n=2 ->
  ["slow_100", "slow_050"] (kills impl using call_count or error_rate sort);
n=0 -> []; fewer tools than n -> all returned.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_top_n_tools_by_p95_ms,
)


def _reset():
    clear_telemetry_stores()


def test_top2_by_p95_primary_discriminator() -> None:
    """FALSIFIABLE: p95s [100, 50, 10], n=2 -> two slowest.
    Kills impl using call_count or error_rate as sort key."""
    _reset()
    record_tool_call("slow_100", 100.0, True)
    record_tool_call("slow_050", 50.0, True)
    record_tool_call("slow_010", 10.0, True)
    result = get_top_n_tools_by_p95_ms(2)
    assert len(result) == 2
    assert result[0] == "slow_100"
    assert result[1] == "slow_050"


def test_zero_n_returns_empty() -> None:
    _reset()
    record_tool_call("some_tool", 99.0, True)
    assert get_top_n_tools_by_p95_ms(0) == []
    assert get_top_n_tools_by_p95_ms(-5) == []


def test_fewer_tools_than_n_returns_all() -> None:
    _reset()
    record_tool_call("a_tool", 30.0, True)
    record_tool_call("b_tool", 20.0, True)
    result = get_top_n_tools_by_p95_ms(100)
    assert len(result) == 2
    assert set(result) == {"a_tool", "b_tool"}


def test_empty_store_returns_empty() -> None:
    _reset()
    assert get_top_n_tools_by_p95_ms(5) == []


def test_tie_broken_by_name() -> None:
    """Same p95 -> alphabetical order."""
    _reset()
    # Both get exactly one call at same latency -> p95 = that latency
    record_tool_call("z_slow", 77.0, True)
    record_tool_call("a_slow", 77.0, True)
    result = get_top_n_tools_by_p95_ms(2)
    assert result == ["a_slow", "z_slow"]
