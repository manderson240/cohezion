"""Item 915: get_tool_p95_ms(tool_name) -> float -- per-tool p95 latency.

PRIMARY DISC.: [10,20,30,40,100] -> p95 near 100 (kills p50=30 impl);
[10,10,10,10,50] -> p95 near 50 (kills mean=18 impl); unknown -> 0.0.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_tool_p95_ms,
)


def _reset():
    clear_telemetry_stores()


def test_p95_not_p50_primary_discriminator() -> None:
    """FALSIFIABLE: [10,20,30,40,100] -> p95 near 100, NOT p50=30.
    Kills impl that returns p50 or mean."""
    _reset()
    for lat in [10.0, 20.0, 30.0, 40.0, 100.0]:
        record_tool_call("p95_tool", lat, True)
    result = get_tool_p95_ms("p95_tool")
    assert result > 60.0  # near the tail value 100
    assert abs(result - 30.0) > 5.0  # not p50


def test_tail_value_dominates_p95() -> None:
    """[10,10,10,10,50] -> p95 biased towards 50 (not mean=18)."""
    _reset()
    for _ in range(4):
        record_tool_call("tail_p95", 10.0, True)
    record_tool_call("tail_p95", 50.0, True)
    result = get_tool_p95_ms("tail_p95")
    assert result > 25.0  # clearly not mean=18


def test_unknown_tool_returns_zero() -> None:
    _reset()
    assert get_tool_p95_ms("unknown_p95") == 0.0
    assert isinstance(get_tool_p95_ms("unknown_p95"), float)


def test_single_call_p95_equals_latency() -> None:
    _reset()
    record_tool_call("single_p95", 77.0, True)
    assert abs(get_tool_p95_ms("single_p95") - 77.0) < 0.001


def test_returns_float() -> None:
    _reset()
    record_tool_call("type_p95", 20.0, True)
    assert isinstance(get_tool_p95_ms("type_p95"), float)
