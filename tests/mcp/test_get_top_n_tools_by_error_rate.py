"""Item 919: get_top_n_tools_by_error_rate(n) -> list[str] -- top-N error-prone tools.

PRIMARY DISC.: three tools [0.9, 0.5, 0.1] error rates, n=2 -> two most error-prone
  (kills impl using call_count sort; kills wrong-order impl).
Tools with 0 calls EXCLUDED (kills impl including them at rate=0.0).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_top_n_tools_by_error_rate,
)


def _reset():
    clear_telemetry_stores()


def test_top2_by_error_rate_primary_discriminator() -> None:
    """FALSIFIABLE: rates [0.9, 0.5, 0.1], n=2 -> top-2 most error-prone.
    Kills impl using call_count or wrong order."""
    _reset()
    # high_err: 9 fail / 10 calls = 0.9
    for _ in range(1):
        record_tool_call("high_err", 10.0, True)
    for _ in range(9):
        record_tool_call("high_err", 10.0, False)
    # mid_err: 5 fail / 10 calls = 0.5
    for _ in range(5):
        record_tool_call("mid_err", 10.0, True)
    for _ in range(5):
        record_tool_call("mid_err", 10.0, False)
    # low_err: 1 fail / 10 calls = 0.1
    for _ in range(9):
        record_tool_call("low_err", 10.0, True)
    for _ in range(1):
        record_tool_call("low_err", 10.0, False)
    result = get_top_n_tools_by_error_rate(2)
    assert len(result) == 2
    assert result[0] == "high_err"
    assert result[1] == "mid_err"


def test_zero_n_returns_empty() -> None:
    _reset()
    record_tool_call("some_tool", 10.0, False)
    assert get_top_n_tools_by_error_rate(0) == []
    assert get_top_n_tools_by_error_rate(-1) == []


def test_tools_with_zero_calls_excluded() -> None:
    """Tools never recorded must NOT appear even at the tail of the list."""
    _reset()
    record_tool_call("real_tool", 10.0, False)  # error_rate = 1.0
    # "phantom_tool" is never recorded — 0 calls, must be excluded
    result = get_top_n_tools_by_error_rate(10)
    assert "phantom_tool" not in result
    assert result == ["real_tool"]


def test_fewer_tools_than_n_returns_all() -> None:
    _reset()
    for tool in ["a_tool", "b_tool"]:
        record_tool_call(tool, 10.0, False)
    result = get_top_n_tools_by_error_rate(100)
    assert len(result) == 2
    assert set(result) == {"a_tool", "b_tool"}


def test_tie_broken_by_name() -> None:
    """Same error rate -> alphabetical order."""
    _reset()
    for tool in ["z_err", "a_err"]:
        record_tool_call(tool, 10.0, False)  # both 1.0 error rate
    result = get_top_n_tools_by_error_rate(2)
    assert result == ["a_err", "z_err"]
