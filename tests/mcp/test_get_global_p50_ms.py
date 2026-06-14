"""Item 947: get_global_p50_ms() -> float -- p50 latency over all tools combined.

PRIMARY DISC.: tool A=[10, 10, 10], tool B=[100].
avg-of-p50s = (10+100)/2 = 55 WRONG.
pooled [10,10,10,100] p50=10 (correct).
Kills impl averaging per-tool p50s.
empty -> 0.0; returns float.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_global_p50_ms,
)


def _reset():
    clear_telemetry_stores()


def test_pooled_not_average_of_p50s_primary_discriminator() -> None:
    """FALSIFIABLE: tool A=[10,10,10], tool B=[100].
    avg-of-p50s=(10+100)/2=55 WRONG. pooled [10,10,10,100] p50=10 (correct)."""
    _reset()
    for _ in range(3):
        record_tool_call("g50_a", 10.0, True)
    record_tool_call("g50_b", 100.0, True)
    result = get_global_p50_ms()
    # Pooled [10, 10, 10, 100]: p50 (index 1.5 interp) = 10.0
    assert abs(result - 10.0) < 0.1  # pooled median near 10
    assert abs(result - 55.0) > 5.0  # not naive avg (55)


def test_empty_store_returns_zero() -> None:
    """No calls -> 0.0."""
    _reset()
    assert get_global_p50_ms() == 0.0


def test_returns_float() -> None:
    """Return type is float."""
    _reset()
    record_tool_call("float_g50", 5.0, True)
    assert isinstance(get_global_p50_ms(), float)


def test_single_call_p50_equals_latency() -> None:
    """Single call -> p50 == that latency."""
    _reset()
    record_tool_call("single_g50", 42.0, True)
    assert abs(get_global_p50_ms() - 42.0) < 0.001


def test_consistent_single_tool() -> None:
    """Single tool: global p50 equals that tool's p50."""
    from cohezion.mcp.compound_mcp_telemetry import get_tool_p50_ms

    _reset()
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        record_tool_call("one_g50", lat, True)
    global_p50 = get_global_p50_ms()
    tool_p50 = get_tool_p50_ms("one_g50")
    assert abs(global_p50 - tool_p50) < 0.001
