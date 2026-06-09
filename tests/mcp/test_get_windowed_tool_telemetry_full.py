"""Item 961: get_windowed_tool_telemetry_full(tool_name, window_ms, *, store=None, now_ms=None) -> dict
-- full 6-key windowed profile for a single tool.

PRIMARY DISC.: 5 recent calls with 2 failures -> dict with exactly 6 keys with
correct values. Kills impl returning 4-key get_tool_windowed_stats dict (missing
success_rate and error_count). Unknown tool -> all-zero with success_rate=1.0.
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_windowed_tool_telemetry_full,
)

_EXPECTED_KEYS = frozenset({
    "call_count", "error_count", "error_rate", "success_rate", "p50_ms", "p95_ms",
})
_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_six_keys_all_correct_primary_discriminator() -> None:
    """FALSIFIABLE: 5 recent calls with 2 failures -> exactly 6 keys, correct values.
    Kills impl returning 4-key windowed stats dict (missing success_rate, error_count)."""
    _reset()
    store = _make_store({
        "wttf": [
            *[(_NOW - 10, 10.0, True)] * 3,
            *[(_NOW - 10, 20.0, False)] * 2,
        ]
    })
    result = get_windowed_tool_telemetry_full("wttf", _WIN, store=store, now_ms=_NOW)
    assert set(result.keys()) == _EXPECTED_KEYS
    assert result["call_count"] == 5
    assert result["error_count"] == 2
    assert abs(result["error_rate"] - 0.4) < 0.001
    assert abs(result["success_rate"] - 0.6) < 0.001
    assert isinstance(result["p50_ms"], float)
    assert isinstance(result["p95_ms"], float)


def test_exactly_six_keys() -> None:
    """Return dict must have EXACTLY 6 keys — no more, no less."""
    _reset()
    store = _make_store({"six_wttf": [(_NOW - 10, 5.0, True)]})
    result = get_windowed_tool_telemetry_full("six_wttf", _WIN, store=store, now_ms=_NOW)
    assert len(result) == 6
    assert set(result.keys()) == _EXPECTED_KEYS


def test_unknown_tool_all_zero_with_success_rate_one() -> None:
    """Unknown tool -> all-zero with success_rate=1.0 (not 0.0)."""
    _reset()
    result = get_windowed_tool_telemetry_full("no_such_wttf", _WIN, store={}, now_ms=_NOW)
    assert result["call_count"] == 0
    assert result["error_count"] == 0
    assert result["error_rate"] == 0.0
    assert abs(result["success_rate"] - 1.0) < 0.001  # NOT 0.0!
    assert result["p50_ms"] == 0.0
    assert result["p95_ms"] == 0.0


def test_no_recent_calls_returns_zero_dict() -> None:
    """Tool with only old calls -> all-zero dict with success_rate=1.0."""
    store = _make_store({
        "wttf_old": [(_NOW - _WIN - 100, 50.0, False)],
    })
    result = get_windowed_tool_telemetry_full("wttf_old", _WIN, store=store, now_ms=_NOW)
    assert result["call_count"] == 0
    assert abs(result["success_rate"] - 1.0) < 0.001


def test_all_successful_calls() -> None:
    """All successful -> error_count=0, success_rate=1.0."""
    store = _make_store({"success_wttf": [(_NOW - 10, 5.0, True)] * 4})
    result = get_windowed_tool_telemetry_full("success_wttf", _WIN, store=store, now_ms=_NOW)
    assert result["error_count"] == 0
    assert result["error_rate"] == 0.0
    assert abs(result["success_rate"] - 1.0) < 0.001


def test_consistent_with_windowed_stats() -> None:
    """call_count, error_rate, p50_ms, p95_ms consistent with get_tool_windowed_stats."""
    from cohezion.mcp.compound_mcp_telemetry import get_tool_windowed_stats
    _reset()
    store = _make_store({
        "consist_wttf": [
            (_NOW - 10, 10.0, True),
            (_NOW - 10, 30.0, False),
            (_NOW - 10, 20.0, True),
        ]
    })
    full = get_windowed_tool_telemetry_full("consist_wttf", _WIN, store=store, now_ms=_NOW)
    stats = get_tool_windowed_stats("consist_wttf", _WIN, store=store, now_ms=_NOW)
    assert full["call_count"] == stats["call_count"]
    assert abs(full["error_rate"] - stats["error_rate"]) < 0.001
    assert abs(full["p50_ms"] - stats["p50_ms"]) < 0.001
    assert abs(full["p95_ms"] - stats["p95_ms"]) < 0.001
    # Additional keys not in windowed_stats:
    assert full["error_count"] == 1
    assert abs(full["success_rate"] - (1.0 - stats["error_rate"])) < 0.001
