"""Item 925: get_all_tool_windowed_stats(window_ms, *, now_ms=None) -> dict[str, dict].

PRIMARY DISC.: two tools, one has recent calls, one only has old calls ->
  only the active tool appears (kills impl that includes all tools);
empty store -> {}; each value has exactly 4 keys (no error_count).
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_all_tool_windowed_stats,
)

NOW = 50_000.0


def _reset():
    clear_telemetry_stores()


def test_stale_tool_excluded_primary_discriminator() -> None:
    """FALSIFIABLE: active tool appears, stale-only tool absent.
    Kills impl that includes all tools regardless of window."""
    _reset()
    store: dict = {
        "active": [(NOW - 500, 10.0, True), (NOW - 300, 20.0, True)],  # in window
        "stale": [(NOW - 9000, 50.0, False)],  # outside 5000ms window
    }
    result = get_all_tool_windowed_stats(window_ms=5000.0, store=store, now_ms=NOW)
    assert "active" in result
    assert "stale" not in result


def test_values_have_exactly_four_keys() -> None:
    """Each per-tool dict: {call_count, error_rate, p50_ms, p95_ms} — no error_count."""
    _reset()
    store: dict = {"tool": [(NOW - 100, 15.0, True)]}
    result = get_all_tool_windowed_stats(window_ms=5000.0, store=store, now_ms=NOW)
    assert set(result["tool"].keys()) == {"call_count", "error_rate", "p50_ms", "p95_ms"}
    assert "error_count" not in result["tool"]


def test_empty_store_returns_empty_dict() -> None:
    _reset()
    store: dict = {}
    assert get_all_tool_windowed_stats(window_ms=5000.0, store=store, now_ms=NOW) == {}


def test_two_active_tools_both_appear() -> None:
    _reset()
    store: dict = {
        "tool_a": [(NOW - 100, 10.0, True)],
        "tool_b": [(NOW - 200, 20.0, False)],
    }
    result = get_all_tool_windowed_stats(window_ms=5000.0, store=store, now_ms=NOW)
    assert set(result.keys()) == {"tool_a", "tool_b"}


def test_stats_values_correct() -> None:
    """Verify the per-tool values are computed correctly for a known input."""
    _reset()
    store: dict = {
        "check": [
            (NOW - 400, 10.0, True),
            (NOW - 300, 20.0, True),
            (NOW - 200, 30.0, False),
        ]
    }
    result = get_all_tool_windowed_stats(window_ms=5000.0, store=store, now_ms=NOW)
    assert result["check"]["call_count"] == 3
    assert abs(result["check"]["error_rate"] - 1 / 3) < 0.001
