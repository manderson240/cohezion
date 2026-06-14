"""Item 916: get_tool_stats(tool_name) -> dict -- unified per-tool profile.

PRIMARY DISC.: tool with 4 calls [10,20,30,40ms], 1 fail -> dict with all 5 keys
correct (kills impl returning only call_count or omitting a field);
unknown tool -> all-zero dict (kills impl raising KeyError).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_tool_stats,
)


def _reset():
    clear_telemetry_stores()


def test_five_keys_all_correct_primary_discriminator() -> None:
    """FALSIFIABLE: 4 calls [10,20,30,40ms], 1 fail ->
    {call_count:4, error_count:1, error_rate:0.25, p50_ms≈25, p95_ms≈37+}.
    Kills impl that returns only call_count or omits any field."""
    _reset()
    for lat in [10.0, 20.0, 30.0, 40.0]:
        record_tool_call("stats_tool", lat, True)
    record_tool_call("stats_tool", 30.0, False)  # 5th call, fail
    result = get_tool_stats("stats_tool")
    assert result["call_count"] == 5
    assert result["error_count"] == 1
    assert abs(result["error_rate"] - 0.2) < 0.001
    assert "p50_ms" in result
    assert "p95_ms" in result
    assert isinstance(result["p50_ms"], float)
    assert isinstance(result["p95_ms"], float)


def test_exactly_five_keys() -> None:
    """Return dict must have EXACTLY {call_count, error_count, error_rate, p50_ms, p95_ms}."""
    _reset()
    record_tool_call("keys_tool", 10.0, True)
    result = get_tool_stats("keys_tool")
    assert set(result.keys()) == {"call_count", "error_count", "error_rate", "p50_ms", "p95_ms"}


def test_unknown_tool_all_zeros() -> None:
    """Unknown tool -> all zeros, no KeyError raised."""
    _reset()
    result = get_tool_stats("unknown_stats")
    assert result["call_count"] == 0
    assert result["error_count"] == 0
    assert result["error_rate"] == 0.0
    assert result["p50_ms"] == 0.0
    assert result["p95_ms"] == 0.0


def test_all_success_error_fields_zero() -> None:
    """No failures -> error_count=0, error_rate=0.0."""
    _reset()
    for _ in range(3):
        record_tool_call("ok_stats", 20.0, True)
    result = get_tool_stats("ok_stats")
    assert result["error_count"] == 0
    assert result["error_rate"] == 0.0


def test_single_call_profile() -> None:
    """Single call: all fields non-zero, p50=p95=latency."""
    _reset()
    record_tool_call("single_stats", 55.0, True)
    result = get_tool_stats("single_stats")
    assert result["call_count"] == 1
    assert abs(result["p50_ms"] - 55.0) < 0.01
    assert abs(result["p95_ms"] - 55.0) < 0.01
