"""Item 946: get_global_p95_ms() -> float -- p95 over all tools combined.

PRIMARY DISC.: tool A=[100, 200], tool B=[300, 400, 500].
Pooled [100,200,300,400,500] p95≈480 (near tail).
avg-of-per-tool-p95s = (200+500)/2 = 350 WRONG.
Kills impl averaging per-tool p95s.
empty -> 0.0; returns float.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_global_p95_ms,
)


def _reset():
    clear_telemetry_stores()


def test_pooled_not_average_of_p95s_primary_discriminator() -> None:
    """FALSIFIABLE: tool A=[100, 200], tool B=[300, 400, 500].
    avg-of-p95s = (200+500)/2 = 350 WRONG.
    pooled p95 over [100,200,300,400,500] is near 500 (tail dominates)."""
    _reset()
    record_tool_call("tool_a_global", 100.0, True)
    record_tool_call("tool_a_global", 200.0, True)
    record_tool_call("tool_b_global", 300.0, True)
    record_tool_call("tool_b_global", 400.0, True)
    record_tool_call("tool_b_global", 500.0, True)
    result = get_global_p95_ms()
    # Pooled list [100,200,300,400,500]: p95 ≈ 480 (interpolated) -- clearly > 350
    assert result > 400.0          # pooled p95 is near the tail value 500
    assert abs(result - 350.0) > 30.0  # not the naive average-of-p95s


def test_empty_store_returns_zero() -> None:
    """No calls -> 0.0."""
    _reset()
    assert get_global_p95_ms() == 0.0


def test_returns_float() -> None:
    """Return type is float."""
    _reset()
    record_tool_call("float_g95", 5.0, True)
    assert isinstance(get_global_p95_ms(), float)


def test_single_call_single_tool_p95_equals_latency() -> None:
    """Single call -> p95 == that latency."""
    _reset()
    record_tool_call("single_g95", 77.0, True)
    assert abs(get_global_p95_ms() - 77.0) < 0.001


def test_consistent_single_tool() -> None:
    """Single tool: global p95 equals that tool's p95."""
    from cohezion.mcp.compound_mcp_telemetry import get_tool_p95_ms
    _reset()
    for lat in [10.0, 20.0, 30.0, 40.0, 100.0]:
        record_tool_call("one_tool", lat, True)
    global_p95 = get_global_p95_ms()
    tool_p95 = get_tool_p95_ms("one_tool")
    assert abs(global_p95 - tool_p95) < 0.001
