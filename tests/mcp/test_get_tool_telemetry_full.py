"""Item 949: get_tool_telemetry_full(tool_name) -> dict --
complete per-tool profile with exactly 8 keys.

PRIMARY DISC.: 4 calls [10,20,30,40], 1 fail: all 8 keys present and correct
(kills impl missing min/max/success_rate; kills impl with wrong key count;
kills impl returning 0 for success_rate on unknown tool).
unknown -> {call_count:0,...,success_rate:1.0}; returns dict with exactly 8 keys.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_tool_telemetry_full,
)

_EXPECTED_KEYS = frozenset(
    {
        "call_count",
        "error_count",
        "error_rate",
        "success_rate",
        "p50_ms",
        "p95_ms",
        "min_ms",
        "max_ms",
    }
)


def _reset():
    clear_telemetry_stores()


def test_eight_keys_all_correct_primary_discriminator() -> None:
    """FALSIFIABLE: 4 calls [10,20,30,40] (all success) + 1 fail@30ms.
    Must return exactly 8 keys with correct values.
    Kills impl missing min/max/success_rate or returning wrong key count."""
    _reset()
    for lat in [10.0, 20.0, 30.0, 40.0]:
        record_tool_call("full_tool", lat, True)
    record_tool_call("full_tool", 30.0, False)  # 5th call, 1 fail
    result = get_tool_telemetry_full("full_tool")
    assert set(result.keys()) == _EXPECTED_KEYS
    assert result["call_count"] == 5
    assert result["error_count"] == 1
    assert abs(result["error_rate"] - 0.2) < 0.001
    assert abs(result["success_rate"] - 0.8) < 0.001
    assert abs(result["min_ms"] - 10.0) < 0.001
    assert abs(result["max_ms"] - 40.0) < 0.001
    assert isinstance(result["p50_ms"], float)
    assert isinstance(result["p95_ms"], float)


def test_exactly_eight_keys() -> None:
    """Return dict must have EXACTLY 8 keys — no more, no less."""
    _reset()
    record_tool_call("eight_keys", 5.0, True)
    result = get_tool_telemetry_full("eight_keys")
    assert len(result) == 8
    assert set(result.keys()) == _EXPECTED_KEYS


def test_unknown_tool_correct_zero_and_one() -> None:
    """Unknown tool -> all-zero dict EXCEPT success_rate=1.0."""
    _reset()
    result = get_tool_telemetry_full("unknown_full")
    assert result["call_count"] == 0
    assert result["error_count"] == 0
    assert result["error_rate"] == 0.0
    assert abs(result["success_rate"] - 1.0) < 0.001  # not 0.0!
    assert result["p50_ms"] == 0.0
    assert result["p95_ms"] == 0.0
    assert result["min_ms"] == 0.0
    assert result["max_ms"] == 0.0


def test_consistent_with_individual_accessors() -> None:
    """Full dict values consistent with individual accessor functions."""
    from cohezion.mcp.compound_mcp_telemetry import (
        get_tool_stats,
        get_tool_min_latency_ms,
        get_tool_max_latency_ms,
        get_tool_success_rate,
    )

    _reset()
    for lat in [5.0, 15.0, 25.0]:
        record_tool_call("consist_full", lat, True)
    record_tool_call("consist_full", 10.0, False)
    result = get_tool_telemetry_full("consist_full")
    stats = get_tool_stats("consist_full")
    assert result["call_count"] == stats["call_count"]
    assert result["error_count"] == stats["error_count"]
    assert abs(result["error_rate"] - stats["error_rate"]) < 0.001
    assert abs(result["p50_ms"] - stats["p50_ms"]) < 0.001
    assert abs(result["p95_ms"] - stats["p95_ms"]) < 0.001
    assert abs(result["min_ms"] - get_tool_min_latency_ms("consist_full")) < 0.001
    assert abs(result["max_ms"] - get_tool_max_latency_ms("consist_full")) < 0.001
    assert abs(result["success_rate"] - get_tool_success_rate("consist_full")) < 0.001
