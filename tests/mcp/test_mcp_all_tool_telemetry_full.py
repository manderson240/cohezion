"""Item 950: get_all_tool_telemetry_full() -- fleet-wide 8-key profile map.

get_all_tool_telemetry_full() -> dict[str, dict]

Returns {tool_name: get_tool_telemetry_full(tool_name)} for all tools in
_TELEMETRY; empty dict when store empty; pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: 2 tools recorded -> dict with exactly 2 keys, each value
     having exactly 8 keys (kills impl using 5-key get_tool_stats).
  2. Empty store -> {}.
  3. Each value has the correct 8 key names.
  4. Values are numerically correct (not just structurally).
  5. unknown-tool default not injected (only recorded tools appear).
  6. Returns dict[str,dict] -- not a list.
"""
from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _TELEMETRY,
    get_all_tool_telemetry_full,
    record_tool_call,
)

_EXPECTED_KEYS = frozenset(
    {"call_count", "error_count", "error_rate", "success_rate",
     "p50_ms", "p95_ms", "min_ms", "max_ms"}
)


@pytest.fixture(autouse=True)
def _clean_store():
    _TELEMETRY.clear()
    yield
    _TELEMETRY.clear()


def test_two_tools_primary_discriminator() -> None:
    """PRIMARY DISC.: 2 tools -> dict with 2 keys; each value has exactly 8 keys.

    Kills impl delegating to 5-key get_tool_stats (missing min_ms, max_ms,
    success_rate) and kills impl with wrong number of outer keys.
    """
    record_tool_call("alpha", 10.0, True)
    record_tool_call("beta", 20.0, False)
    result = get_all_tool_telemetry_full()
    assert isinstance(result, dict), "Must return dict"
    assert set(result.keys()) == {"alpha", "beta"}, f"Expected 2 tools; got {list(result)}"
    for tool, profile in result.items():
        assert len(profile) == 8, f"Tool {tool!r}: expected 8 keys, got {len(profile)}: {list(profile)}"
        assert set(profile.keys()) == _EXPECTED_KEYS, (
            f"Tool {tool!r}: key mismatch. Expected {_EXPECTED_KEYS}, got {set(profile.keys())}"
        )


def test_empty_store_returns_empty_dict() -> None:
    """Empty store -> {}."""
    result = get_all_tool_telemetry_full()
    assert result == {}, f"Empty store -> {{}}; got {result}"


def test_values_numerically_correct() -> None:
    """Values must be numerically accurate, not just structurally correct."""
    record_tool_call("tool_x", 10.0, True)
    record_tool_call("tool_x", 20.0, True)
    record_tool_call("tool_x", 30.0, False)  # 1 error, 3 calls
    result = get_all_tool_telemetry_full()
    assert "tool_x" in result
    profile = result["tool_x"]
    assert profile["call_count"] == 3
    assert profile["error_count"] == 1
    assert abs(profile["error_rate"] - 1 / 3) < 1e-9
    assert abs(profile["success_rate"] - 2 / 3) < 1e-9
    assert profile["min_ms"] == 10.0
    assert profile["max_ms"] == 30.0


def test_only_recorded_tools_appear() -> None:
    """Only tools that have been recorded appear; no phantom entries."""
    record_tool_call("real_tool", 50.0, True)
    result = get_all_tool_telemetry_full()
    assert list(result.keys()) == ["real_tool"], f"Got unexpected tools: {list(result)}"


def test_return_is_dict_not_list() -> None:
    """Return type is dict[str, dict], not a list."""
    record_tool_call("a_tool", 5.0, True)
    result = get_all_tool_telemetry_full()
    assert isinstance(result, dict), f"Expected dict; got {type(result)}"


def test_single_tool_profile_matches_individual_call() -> None:
    """Single tool: result matches what get_tool_telemetry_full returns directly."""
    from cohezion.mcp.compound_mcp_telemetry import get_tool_telemetry_full

    record_tool_call("solo", 42.0, True)
    all_full = get_all_tool_telemetry_full()
    individual = get_tool_telemetry_full("solo")
    assert all_full["solo"] == individual, (
        "get_all_tool_telemetry_full['solo'] must equal get_tool_telemetry_full('solo')"
    )
