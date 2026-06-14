"""Item 962: get_all_windowed_tool_telemetry_full() -- fleet-wide 6-key windowed profile.

get_all_windowed_tool_telemetry_full(window_ms, *, store=None, now_ms=None) -> dict[str, dict]

Returns {tool: get_windowed_tool_telemetry_full(tool, window_ms, ...)} for ALL tools
with >=1 call in the window. Empty dict when no recent calls.

Discriminating tests:
  1. PRIMARY DISC.: 2 tools with recent calls -> dict with exactly 2 keys, each 6-key profile
     (kills impl including tools with ONLY old calls; kills impl returning 4-key profile).
  2. Tool with only old calls excluded.
  3. Empty store -> {}.
  4. Returns dict[str, dict].
  5. Uses _WINDOWED_TELEMETRY singleton by default.
"""

from __future__ import annotations

import pytest

from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    get_all_windowed_tool_telemetry_full,
)

NOW_MS = 100_000.0
WINDOW_MS = 10_000.0
_EXPECTED_KEYS = frozenset(
    {"call_count", "error_count", "error_rate", "p50_ms", "p95_ms", "success_rate"}
)


@pytest.fixture(autouse=True)
def _clean():
    _WINDOWED_TELEMETRY.clear()
    yield
    _WINDOWED_TELEMETRY.clear()


def _add(store: dict, tool: str, lat: float, ts: float, ok: bool = True) -> None:
    store.setdefault(tool, []).append((ts, lat, ok))


def _recent() -> float:
    return NOW_MS - 5_000.0


def _old() -> float:
    return NOW_MS - WINDOW_MS - 1_000.0


def test_two_tools_each_six_keys_primary_discriminator() -> None:
    """PRIMARY DISC.: 2 tools with recent calls -> 2-key dict, each value has 6 keys.

    Kills impl that:
    - Returns tools with only old calls (wrong window filtering)
    - Returns 4-key profile (missing error_count + success_rate)
    """
    store: dict = {}
    ts = _recent()
    _add(store, "alpha", 10.0, ts, ok=True)
    _add(store, "alpha", 20.0, ts, ok=False)
    _add(store, "beta", 50.0, ts, ok=True)
    # old call for "gamma" -- must be excluded
    _add(store, "gamma", 100.0, _old(), ok=True)

    result = get_all_windowed_tool_telemetry_full(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert isinstance(result, dict)
    assert set(result.keys()) == {"alpha", "beta"}, (
        f"Expected only 'alpha' and 'beta' (gamma is out of window); got {set(result.keys())}"
    )
    for tool, profile in result.items():
        assert set(profile.keys()) == _EXPECTED_KEYS, (
            f"Tool {tool}: expected 6 keys {_EXPECTED_KEYS}; got {set(profile.keys())}"
        )


def test_old_tool_excluded() -> None:
    """Tool whose only calls are outside window must not appear in result."""
    store: dict = {}
    _add(store, "recent_tool", 10.0, _recent())
    _add(store, "old_tool", 10.0, _old())

    result = get_all_windowed_tool_telemetry_full(WINDOW_MS, store=store, now_ms=NOW_MS)

    assert "old_tool" not in result, f"old_tool must be excluded; got {set(result.keys())}"
    assert "recent_tool" in result


def test_empty_store_returns_empty_dict() -> None:
    result = get_all_windowed_tool_telemetry_full(WINDOW_MS, store={}, now_ms=NOW_MS)
    assert result == {}


def test_no_recent_calls_returns_empty_dict() -> None:
    """Store has entries but all are outside window -> {}."""
    store: dict = {}
    _add(store, "t", 10.0, _old())
    result = get_all_windowed_tool_telemetry_full(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert result == {}


def test_returns_dict() -> None:
    store: dict = {}
    _add(store, "t", 5.0, _recent())
    result = get_all_windowed_tool_telemetry_full(WINDOW_MS, store=store, now_ms=NOW_MS)
    assert isinstance(result, dict)


def test_profile_values_correct() -> None:
    """Values in each per-tool profile are correct (not just structurally present)."""
    store: dict = {}
    ts = _recent()
    _add(store, "t", 10.0, ts, ok=True)
    _add(store, "t", 10.0, ts, ok=True)
    _add(store, "t", 10.0, ts, ok=False)

    result = get_all_windowed_tool_telemetry_full(WINDOW_MS, store=store, now_ms=NOW_MS)

    profile = result["t"]
    assert profile["call_count"] == 3
    assert profile["error_count"] == 1
    assert abs(profile["error_rate"] - 1.0 / 3.0) < 1e-9
    assert abs(profile["success_rate"] - 2.0 / 3.0) < 1e-9


def test_uses_windowed_telemetry_singleton() -> None:
    _WINDOWED_TELEMETRY["x"] = [(NOW_MS - 5_000.0, 10.0, True)]
    result = get_all_windowed_tool_telemetry_full(WINDOW_MS, now_ms=NOW_MS)
    assert "x" in result
    assert len(result["x"]) == 6
