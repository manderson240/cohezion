"""Item 950: get_all_tool_telemetry_full() -> dict[str, dict] --
full 8-key profile for every recorded tool.

PRIMARY DISC.: 2 tools recorded -> dict with exactly 2 keys, each value
having exactly 8 keys (kills impl returning 5-key stats or missing
success_rate/min/max).
empty -> {}; returns dict[str,dict].
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call,
    clear_telemetry_stores,
    get_all_tool_telemetry_full,
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


def test_two_tools_two_keys_eight_each_primary_discriminator() -> None:
    """FALSIFIABLE: 2 tools -> dict with exactly 2 keys, each value exactly 8 keys.
    Kills impl returning 5-key stats dict or missing success_rate/min/max."""
    _reset()
    record_tool_call("all_a", 10.0, True)
    record_tool_call("all_a", 20.0, False)
    record_tool_call("all_b", 50.0, True)
    result = get_all_tool_telemetry_full()
    assert isinstance(result, dict)
    assert set(result.keys()) == {"all_a", "all_b"}
    for tool_name, profile in result.items():
        assert set(profile.keys()) == _EXPECTED_KEYS, (
            f"Tool {tool_name!r} has wrong keys: {set(profile.keys())}"
        )


def test_empty_store_returns_empty_dict() -> None:
    """No calls -> {}."""
    _reset()
    result = get_all_tool_telemetry_full()
    assert result == {}


def test_returns_dict_type() -> None:
    """Return type is dict."""
    _reset()
    record_tool_call("rtype_all", 5.0, True)
    assert isinstance(get_all_tool_telemetry_full(), dict)


def test_single_tool_one_key() -> None:
    """One tool -> dict with exactly one key."""
    _reset()
    record_tool_call("single_all", 7.0, True)
    result = get_all_tool_telemetry_full()
    assert len(result) == 1
    assert "single_all" in result
    assert set(result["single_all"].keys()) == _EXPECTED_KEYS


def test_consistent_with_get_tool_telemetry_full() -> None:
    """Values for each tool match get_tool_telemetry_full(tool_name)."""
    from cohezion.mcp.compound_mcp_telemetry import get_tool_telemetry_full

    _reset()
    for lat in [5.0, 15.0, 25.0]:
        record_tool_call("cons_a", lat, True)
    record_tool_call("cons_a", 10.0, False)
    record_tool_call("cons_b", 100.0, True)
    record_tool_call("cons_b", 200.0, False)
    all_full = get_all_tool_telemetry_full()
    for tool in ("cons_a", "cons_b"):
        individual = get_tool_telemetry_full(tool)
        for key in _EXPECTED_KEYS:
            assert abs(all_full[tool][key] - individual[key]) < 0.001, (
                f"Mismatch for {tool!r} key {key!r}"
            )


def test_three_tools_three_keys() -> None:
    """Three tools -> dict with exactly 3 keys."""
    _reset()
    for name in ("t1", "t2", "t3"):
        record_tool_call(name, 1.0, True)
    result = get_all_tool_telemetry_full()
    assert len(result) == 3
    assert set(result.keys()) == {"t1", "t2", "t3"}


def test_profiles_are_independent() -> None:
    """Different tools have independent profiles."""
    _reset()
    record_tool_call("indep_x", 10.0, True)
    record_tool_call("indep_y", 500.0, False)
    result = get_all_tool_telemetry_full()
    assert result["indep_x"]["call_count"] == 1
    assert result["indep_x"]["error_count"] == 0
    assert result["indep_y"]["call_count"] == 1
    assert result["indep_y"]["error_count"] == 1
    assert result["indep_x"]["max_ms"] < result["indep_y"]["max_ms"]
