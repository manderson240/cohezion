"""Item 948: get_global_mean_latency_ms() -> float --
mean latency across all tools combined.

PRIMARY DISC.: tool A=[10,10,10] (3 calls), tool B=[100] (1 call).
avg-of-means=(10+100)/2=55 WRONG.
correct=(10+10+10+100)/4=32.5.
Kills impl averaging per-tool means.
empty -> 0.0; returns float.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_global_mean_latency_ms,
)


def _reset():
    clear_telemetry_stores()


def test_weighted_mean_not_avg_of_means_primary_discriminator() -> None:
    """FALSIFIABLE: tool A=[10,10,10], tool B=[100].
    avg-of-means = (10+100)/2 = 55 WRONG.
    correct = (10+10+10+100)/4 = 32.5."""
    _reset()
    for _ in range(3):
        record_tool_call("gm_a", 10.0, True)
    record_tool_call("gm_b", 100.0, True)
    result = get_global_mean_latency_ms()
    assert abs(result - 32.5) < 0.001
    assert abs(result - 55.0) > 1.0   # not naive avg-of-means


def test_empty_store_returns_zero() -> None:
    """No calls -> 0.0."""
    _reset()
    assert get_global_mean_latency_ms() == 0.0


def test_returns_float() -> None:
    """Return type is float."""
    _reset()
    record_tool_call("float_gm", 5.0, True)
    assert isinstance(get_global_mean_latency_ms(), float)


def test_single_call_mean_equals_latency() -> None:
    """Single call -> mean == that latency."""
    _reset()
    record_tool_call("single_gm", 77.0, True)
    assert abs(get_global_mean_latency_ms() - 77.0) < 0.001


def test_consistent_with_total_latency_and_count() -> None:
    """global_mean == total_latency / total_calls."""
    from cohezion.mcp.compound_mcp_telemetry import (
        get_total_call_count,
        get_tool_total_latency_ms,
        get_all_tool_names,
    )
    _reset()
    for lat in [10.0, 20.0, 30.0]:
        record_tool_call("gm_c1", lat, True)
    for lat in [40.0, 50.0]:
        record_tool_call("gm_c2", lat, True)
    result = get_global_mean_latency_ms()
    total_lat = sum(get_tool_total_latency_ms(t) for t in get_all_tool_names())
    total_calls = get_total_call_count()
    expected = total_lat / total_calls
    assert abs(result - expected) < 0.001
