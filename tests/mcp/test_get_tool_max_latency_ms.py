"""Item 935: get_tool_max_latency_ms(tool_name) -> float -- maximum latency.

PRIMARY DISC.: [30, 10, 50, 20] -> 50.0
(kills impl returning min=10, mean=27.5, or last=20).
unknown -> 0.0; returns float; pure.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_tool_max_latency_ms,
)


def _reset():
    clear_telemetry_stores()


def test_max_not_min_not_last_primary_discriminator() -> None:
    """FALSIFIABLE: [30, 10, 50, 20] -> max=50.0.
    Kills impl returning min=10, mean=27.5, or last=20."""
    _reset()
    for lat in [30.0, 10.0, 50.0, 20.0]:
        record_tool_call("max_tool", lat, True)
    result = get_tool_max_latency_ms("max_tool")
    assert abs(result - 50.0) < 0.001
    assert abs(result - 10.0) > 1.0   # not min
    assert abs(result - 20.0) > 1.0   # not last
    assert abs(result - 27.5) > 1.0   # not mean


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_tool_max_latency_ms("never_seen") == 0.0


def test_returns_float() -> None:
    """Return type is float."""
    _reset()
    record_tool_call("float_max", 5.0, True)
    assert isinstance(get_tool_max_latency_ms("float_max"), float)


def test_single_call_max_equals_latency() -> None:
    """Single call: max == that latency."""
    _reset()
    record_tool_call("single_max", 88.0, True)
    assert abs(get_tool_max_latency_ms("single_max") - 88.0) < 0.001


def test_max_updates_on_new_high() -> None:
    """Max updates when a new high value is recorded."""
    _reset()
    record_tool_call("updating_max", 10.0, True)
    assert abs(get_tool_max_latency_ms("updating_max") - 10.0) < 0.001
    record_tool_call("updating_max", 200.0, True)
    assert abs(get_tool_max_latency_ms("updating_max") - 200.0) < 0.001
    record_tool_call("updating_max", 5.0, True)  # lower — max unchanged
    assert abs(get_tool_max_latency_ms("updating_max") - 200.0) < 0.001
