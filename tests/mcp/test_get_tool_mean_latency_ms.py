"""Item 933: get_tool_mean_latency_ms(tool_name) -> float -- mean latency.

PRIMARY DISC.: [10, 20, 60] -> 30.0 but p50=20.0
(kills p50-impl; p50 and mean coincide for symmetric sets like [10,20,30],
so we use an ASYMMETRIC set where they diverge).
unknown -> 0.0; returns float; pure.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_tool_mean_latency_ms,
    get_tool_p50_ms,
)


def _reset():
    clear_telemetry_stores()


def test_mean_not_p50_primary_discriminator() -> None:
    """FALSIFIABLE: [10, 20, 60] -> mean=30.0, p50=20.0.
    Kills impl returning p50 (20) instead of mean (30)."""
    _reset()
    for lat in [10.0, 20.0, 60.0]:
        record_tool_call("mean_tool", lat, True)
    result = get_tool_mean_latency_ms("mean_tool")
    p50 = get_tool_p50_ms("mean_tool")
    # Confirm they differ (validates the discriminating property of this set)
    assert abs(p50 - 20.0) < 0.1
    assert abs(result - 30.0) < 0.001   # mean = (10+20+60)/3 = 30
    assert abs(result - p50) > 5.0      # mean ≠ p50 for this asymmetric set


def test_unknown_tool_returns_zero() -> None:
    """Unknown tool -> 0.0."""
    _reset()
    assert get_tool_mean_latency_ms("never_seen") == 0.0


def test_returns_float() -> None:
    """Return type is float."""
    _reset()
    record_tool_call("float_mean", 5.0, True)
    assert isinstance(get_tool_mean_latency_ms("float_mean"), float)


def test_single_call_mean_equals_latency() -> None:
    """Single call: mean == that latency."""
    _reset()
    record_tool_call("single_mean", 77.0, True)
    assert abs(get_tool_mean_latency_ms("single_mean") - 77.0) < 0.001


def test_equal_latencies() -> None:
    """All latencies equal -> mean equals that value."""
    _reset()
    for _ in range(4):
        record_tool_call("equal_lat", 25.0, True)
    assert abs(get_tool_mean_latency_ms("equal_lat") - 25.0) < 0.001


def test_failed_calls_included() -> None:
    """Failed calls' latencies are included in the mean."""
    _reset()
    record_tool_call("mixed_mean", 10.0, True)
    record_tool_call("mixed_mean", 30.0, False)  # error — still counted
    # mean = (10+30)/2 = 20
    assert abs(get_tool_mean_latency_ms("mixed_mean") - 20.0) < 0.001
