"""Item 936: get_tool_latency_range_ms(tool_name) -> tuple[float, float] --
(min, max) latency range.

PRIMARY DISC.: [30, 10, 50, 20] -> (10.0, 50.0) as a tuple
(kills impl returning reversed (50, 10), a dict, or a list).
unknown -> (0.0, 0.0); returns tuple[float, float]; pure.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_tool_latency_range_ms,
)


def _reset():
    clear_telemetry_stores()


def test_min_max_tuple_not_reversed_primary_discriminator() -> None:
    """FALSIFIABLE: [30, 10, 50, 20] -> (10.0, 50.0) as tuple[float, float].
    Kills impl returning (max, min)=(50, 10) or a dict or a list."""
    _reset()
    for lat in [30.0, 10.0, 50.0, 20.0]:
        record_tool_call("range_tool", lat, True)
    result = get_tool_latency_range_ms("range_tool")
    assert isinstance(result, tuple)
    assert len(result) == 2
    lo, hi = result
    assert abs(lo - 10.0) < 0.001   # min first
    assert abs(hi - 50.0) < 0.001   # max second
    # discriminate reversed (max, min) impl:
    assert lo < hi


def test_unknown_tool_returns_zero_zero() -> None:
    """Unknown tool -> (0.0, 0.0)."""
    _reset()
    result = get_tool_latency_range_ms("never_seen")
    assert result == (0.0, 0.0)


def test_returns_tuple_of_floats() -> None:
    """Return type is tuple containing floats."""
    _reset()
    record_tool_call("type_range", 5.0, True)
    lo, hi = get_tool_latency_range_ms("type_range")
    assert isinstance(lo, float)
    assert isinstance(hi, float)


def test_single_call_range_is_equal() -> None:
    """Single call: min == max."""
    _reset()
    record_tool_call("single_range", 42.5, True)
    lo, hi = get_tool_latency_range_ms("single_range")
    assert abs(lo - 42.5) < 0.001
    assert abs(hi - 42.5) < 0.001


def test_consistent_with_min_max_accessors() -> None:
    """Range consistent with individual min/max accessors."""
    from cohezion.mcp.compound_mcp_telemetry import (
        get_tool_min_latency_ms,
        get_tool_max_latency_ms,
    )
    _reset()
    for lat in [15.0, 5.0, 25.0, 10.0]:
        record_tool_call("conscheck", lat, True)
    lo, hi = get_tool_latency_range_ms("conscheck")
    assert abs(lo - get_tool_min_latency_ms("conscheck")) < 0.001
    assert abs(hi - get_tool_max_latency_ms("conscheck")) < 0.001
