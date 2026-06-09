"""Item 921: get_tool_windowed_stats(tool_name, window_ms, *, now_ms=None) -> dict.

PRIMARY DISC.: 3 recent + 1 old call -> call_count=3 (kills impl counting old calls);
all-3-fail -> error_rate=1.0 (kills count-not-rate impl);
unknown tool -> zeros (kills KeyError impl).
Returns {call_count, error_rate, p50_ms, p95_ms} — NO error_count (windowed schema).
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call_windowed,
    clear_telemetry_stores,
    _WINDOWED_TELEMETRY,
    get_tool_windowed_stats,
)

NOW = 10_000.0  # fixed reference point for tests


def _reset():
    clear_telemetry_stores()


def test_window_excludes_old_calls_primary_discriminator() -> None:
    """FALSIFIABLE: 3 recent + 1 old -> call_count=3.
    Kills impl that counts all calls (ignoring window)."""
    _reset()
    store: dict = {}
    # 3 calls within window [10000 - 5000, 10000] = [5000, 10000]
    for ts in [6000.0, 7000.0, 9000.0]:
        store.setdefault("wind_tool", []).append((ts, 20.0, True))
    # 1 old call at ts=1000 (outside window)
    store["wind_tool"].append((1000.0, 100.0, False))
    result = get_tool_windowed_stats("wind_tool", window_ms=5000.0, store=store, now_ms=NOW)
    assert result["call_count"] == 3


def test_all_failures_in_window_error_rate_one() -> None:
    """3 failures in window -> error_rate=1.0."""
    _reset()
    store: dict = {"fail_tool": [(NOW - 1000, 10.0, False) for _ in range(3)]}
    result = get_tool_windowed_stats("fail_tool", window_ms=5000.0, store=store, now_ms=NOW)
    assert abs(result["error_rate"] - 1.0) < 0.001


def test_unknown_tool_returns_all_zeros() -> None:
    _reset()
    store: dict = {}
    result = get_tool_windowed_stats("no_such", window_ms=5000.0, store=store, now_ms=NOW)
    assert result == {"call_count": 0, "error_rate": 0.0, "p50_ms": 0.0, "p95_ms": 0.0}


def test_exactly_four_keys_no_error_count() -> None:
    """Windowed schema: {call_count, error_rate, p50_ms, p95_ms} — no error_count."""
    _reset()
    store: dict = {"k_tool": [(NOW - 100, 30.0, True)]}
    result = get_tool_windowed_stats("k_tool", window_ms=5000.0, store=store, now_ms=NOW)
    assert set(result.keys()) == {"call_count", "error_rate", "p50_ms", "p95_ms"}
    assert "error_count" not in result


def test_latencies_within_window_only() -> None:
    """p50/p95 are computed from window calls only — not all-time calls."""
    _reset()
    store: dict = {
        "lat_tool": [
            (NOW - 500, 10.0, True),   # in window
            (NOW - 200, 90.0, True),   # in window
            (NOW - 9000, 1000.0, True),  # outside window (old)
        ]
    }
    result = get_tool_windowed_stats("lat_tool", window_ms=1000.0, store=store, now_ms=NOW)
    assert result["call_count"] == 2
    # p50 of [10, 90]: idx=0.5 -> 10 + 0.5*(90-10) = 50
    assert abs(result["p50_ms"] - 50.0) < 1.0
    # Huge old latency 1000ms must NOT influence results
    assert result["p95_ms"] < 200.0
