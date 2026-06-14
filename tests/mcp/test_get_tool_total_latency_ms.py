"""Item 932: get_tool_total_latency_ms(tool_name) -> float --
sum of all recorded latencies for a tool.

PRIMARY DISC.: [10, 20, 30] -> 60.0
(kills impl returning mean=20, max=30, or count=3).
unknown -> 0.0; returns float; pure.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_tool_total_latency_ms,
)


def _reset():
    clear_telemetry_stores()


def test_sum_not_mean_not_max_primary_discriminator() -> None:
    """FALSIFIABLE: [10, 20, 30] -> 60.0 (NOT mean=20, NOT max=30, NOT count=3).
    Kills impl returning mean, max, or count."""
    _reset()
    for lat in [10.0, 20.0, 30.0]:
        record_tool_call("sum_tool", lat, True)
    result = get_tool_total_latency_ms("sum_tool")
    assert abs(result - 60.0) < 0.001
    assert abs(result - 20.0) > 1.0  # not mean
    assert abs(result - 30.0) > 1.0  # not max
    assert abs(result - 3.0) > 1.0  # not count


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    result = get_tool_total_latency_ms("never_seen")
    assert result == 0.0


def test_returns_float() -> None:
    """Return type is float."""
    _reset()
    record_tool_call("float_tool", 5.0, True)
    result = get_tool_total_latency_ms("float_tool")
    assert isinstance(result, float)


def test_single_call_total_equals_latency() -> None:
    """Single call: total == that latency."""
    _reset()
    record_tool_call("single_latency", 42.5, True)
    result = get_tool_total_latency_ms("single_latency")
    assert abs(result - 42.5) < 0.001


def test_accumulates_across_calls() -> None:
    """Total grows with each call."""
    _reset()
    record_tool_call("accum", 10.0, True)
    assert abs(get_tool_total_latency_ms("accum") - 10.0) < 0.001
    record_tool_call("accum", 20.0, True)
    assert abs(get_tool_total_latency_ms("accum") - 30.0) < 0.001
    record_tool_call("accum", 30.0, True)
    assert abs(get_tool_total_latency_ms("accum") - 60.0) < 0.001


def test_failed_calls_included_in_sum() -> None:
    """Failed calls' latencies are included in the sum."""
    _reset()
    record_tool_call("mixed", 10.0, True)
    record_tool_call("mixed", 50.0, False)  # error — latency still counted
    result = get_tool_total_latency_ms("mixed")
    assert abs(result - 60.0) < 0.001
