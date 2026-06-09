"""Item 934: get_tool_min_latency_ms(tool_name) -> float -- minimum latency.

PRIMARY DISC.: [30, 10, 20] -> 10.0
(kills impl returning max=30, mean=20, or first=30).
unknown -> 0.0; returns float; pure.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_tool_min_latency_ms,
)


def _reset():
    clear_telemetry_stores()


def test_min_not_max_not_first_primary_discriminator() -> None:
    """FALSIFIABLE: recorded in order [30, 10, 20] -> min=10.0.
    Kills impl returning max=30 or first-inserted=30 or mean=20."""
    _reset()
    # Deliberately record in non-ascending order so first≠min, max≠min
    for lat in [30.0, 10.0, 20.0]:
        record_tool_call("min_tool", lat, True)
    result = get_tool_min_latency_ms("min_tool")
    assert abs(result - 10.0) < 0.001
    assert abs(result - 30.0) > 1.0  # not max
    assert abs(result - 20.0) > 1.0  # not mean


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_tool_min_latency_ms("never_seen") == 0.0


def test_returns_float() -> None:
    """Return type is float."""
    _reset()
    record_tool_call("float_min", 5.0, True)
    assert isinstance(get_tool_min_latency_ms("float_min"), float)


def test_single_call_min_equals_latency() -> None:
    """Single call: min == that latency."""
    _reset()
    record_tool_call("single_min", 42.5, True)
    assert abs(get_tool_min_latency_ms("single_min") - 42.5) < 0.001


def test_min_stays_min_after_larger_calls() -> None:
    """After additional larger calls, min is unchanged."""
    _reset()
    record_tool_call("growing", 5.0, True)
    record_tool_call("growing", 100.0, True)
    record_tool_call("growing", 50.0, True)
    assert abs(get_tool_min_latency_ms("growing") - 5.0) < 0.001
