"""Item 914: get_tool_p50_ms(tool_name) -> float -- per-tool p50 latency.

PRIMARY DISC.: [10,20,30,40,50]ms -> p50=30.0 (kills mean=30 coincidence: use [10,20,50,100,200]
to distinguish p50=50 from mean=76); unknown tool -> 0.0; single-call -> that call.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_tool_p50_ms,
)


def _reset():
    clear_telemetry_stores()


def test_p50_not_mean_primary_discriminator() -> None:
    """FALSIFIABLE: [10,20,50,100,200] -> p50=50.0, NOT mean=76.0.
    Kills impl returning mean; the values are chosen so mean != p50."""
    _reset()
    for lat in [10.0, 20.0, 50.0, 100.0, 200.0]:
        record_tool_call("p50_tool", lat, True)
    result = get_tool_p50_ms("p50_tool")
    assert abs(result - 50.0) < 1.0  # p50 = 50.0
    assert abs(result - 76.0) > 5.0  # not mean


def test_unknown_tool_returns_zero() -> None:
    _reset()
    assert get_tool_p50_ms("unknown_p50") == 0.0
    assert isinstance(get_tool_p50_ms("unknown_p50"), float)


def test_single_call_p50_equals_that_latency() -> None:
    """Single call: p50 = the call's latency."""
    _reset()
    record_tool_call("single_p50", 42.0, True)
    assert abs(get_tool_p50_ms("single_p50") - 42.0) < 0.001


def test_returns_float() -> None:
    _reset()
    record_tool_call("type_p50", 15.0, True)
    result = get_tool_p50_ms("type_p50")
    assert isinstance(result, float)


def test_symmetric_five_values() -> None:
    """[10,20,30,40,50] -> p50=30.0 (middle value with interpolation)."""
    _reset()
    for lat in [10.0, 20.0, 30.0, 40.0, 50.0]:
        record_tool_call("sym5_p50", lat, True)
    assert abs(get_tool_p50_ms("sym5_p50") - 30.0) < 0.001
