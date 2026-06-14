"""Item 917: get_all_tool_stats() -> dict[str, dict] -- all-tools stats map.

PRIMARY DISC.: two tools recorded -> both appear with correct profiles
(kills impl returning only one tool or using wrong schema);
empty store -> {}; each value has exactly 5 keys.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_all_tool_stats,
)


def _reset():
    clear_telemetry_stores()


def test_both_tools_in_result_primary_discriminator() -> None:
    """FALSIFIABLE: two tools recorded -> both appear in result with correct profiles.
    Kills impl returning only one tool or wrong schema."""
    _reset()
    record_tool_call("tool_a", 10.0, True)
    record_tool_call("tool_a", 20.0, False)
    record_tool_call("tool_b", 50.0, True)
    result = get_all_tool_stats()
    assert "tool_a" in result
    assert "tool_b" in result
    assert result["tool_a"]["call_count"] == 2
    assert result["tool_a"]["error_count"] == 1
    assert result["tool_b"]["call_count"] == 1
    assert result["tool_b"]["error_count"] == 0


def test_empty_store_returns_empty_dict() -> None:
    """Empty store -> {} not None or missing keys."""
    _reset()
    assert get_all_tool_stats() == {}


def test_each_value_has_exactly_five_keys() -> None:
    """Each tool's value must have exactly {call_count, error_count, error_rate, p50_ms, p95_ms}."""
    _reset()
    record_tool_call("keys_check", 15.0, True)
    result = get_all_tool_stats()
    assert set(result["keys_check"].keys()) == {
        "call_count",
        "error_count",
        "error_rate",
        "p50_ms",
        "p95_ms",
    }


def test_profiles_match_individual_accessors() -> None:
    """Each tool's stats must equal what get_tool_stats returns for that tool."""
    _reset()
    from cohezion.mcp.compound_mcp_telemetry import get_tool_stats

    record_tool_call("match_tool", 30.0, True)
    record_tool_call("match_tool", 60.0, False)
    result = get_all_tool_stats()
    expected = get_tool_stats("match_tool")
    assert result["match_tool"] == expected


def test_three_tools_all_present() -> None:
    """Three distinct tools -> all three appear in result."""
    _reset()
    for i in range(3):
        record_tool_call(f"multi_{i}", float(i * 10 + 10), i % 2 == 0)
    result = get_all_tool_stats()
    assert len(result) == 3
    for i in range(3):
        assert f"multi_{i}" in result
