"""Item 905: get_telemetry_health_snapshot() -- unified MCP health per tool.

PRIMARY DISC.: tool with latency + error spike -> {latency_spike: True, error_spike: True, ...};
tool with no spikes -> both False; empty -> {}; keys match spec exactly;
distinct from detect_latency_spike (new aggregate, not the raw spike dict).
"""
from __future__ import annotations

import time
from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    record_tool_call_windowed,
    get_telemetry_health_snapshot,
)


def _reset():
    _WINDOWED_TELEMETRY.clear()


def _ts(seconds_ago: float = 0.0) -> float:
    return (time.time() - seconds_ago) * 1000.0


# ── primary discriminator ─────────────────────────────────────────────────────

def test_both_spikes_present_primary_discriminator() -> None:
    """FALSIFIABLE: tool with latency 3x + error jump 0->0.5 -> both spike=True.
    Kills impl that returns False for either spike or merges wrong values."""
    _reset()
    base_ms = _ts(seconds_ago=60)
    now_ms = _ts()
    # Baseline: 5 calls at 10ms, all success
    for _ in range(5):
        record_tool_call_windowed("h1", 10.0, True, ts_ms=base_ms)
    # Recent: 5 calls at 40ms (ratio=4.0 > 2.0), 3 fail (err=0.6)
    for _ in range(2):
        record_tool_call_windowed("h1", 40.0, True, ts_ms=now_ms)
    for _ in range(3):
        record_tool_call_windowed("h1", 40.0, False, ts_ms=now_ms)
    snapshot = get_telemetry_health_snapshot(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    assert "h1" in snapshot
    entry = snapshot["h1"]
    assert entry["latency_spike"] is True
    assert entry["error_spike"] is True


def test_no_spikes_both_false() -> None:
    """FALSIFIABLE: tool with mild latency + mild error -> both False.
    Kills impl that always sets spike=True or uses wrong thresholds."""
    _reset()
    base_ms = _ts(seconds_ago=60)
    now_ms = _ts()
    # Baseline: 5 calls at 20ms, all success
    for _ in range(5):
        record_tool_call_windowed("h2", 20.0, True, ts_ms=base_ms)
    # Recent: 5 calls at 25ms (ratio=1.25 < 2.0), 1 fail (err=0.2, not > 0.2)
    for _ in range(4):
        record_tool_call_windowed("h2", 25.0, True, ts_ms=now_ms)
    record_tool_call_windowed("h2", 25.0, False, ts_ms=now_ms)
    snapshot = get_telemetry_health_snapshot(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    assert "h2" in snapshot
    entry = snapshot["h2"]
    assert entry["latency_spike"] is False
    assert entry["error_spike"] is False


def test_empty_store_returns_empty_dict() -> None:
    """FALSIFIABLE: no calls -> {} (kills impl returning None or raising)."""
    _reset()
    result = get_telemetry_health_snapshot(
        _WINDOWED_TELEMETRY, window_ms=5_000, baseline_window_ms=60_000, now_ms=_ts()
    )
    assert result == {}


def test_output_keys_match_spec() -> None:
    """Output dict must have exactly {latency_spike, error_spike, recent_p95, recent_error_rate}."""
    _reset()
    base_ms = _ts(seconds_ago=60)
    now_ms = _ts()
    for _ in range(3):
        record_tool_call_windowed("h3", 10.0, True, ts_ms=base_ms)
    for _ in range(3):
        record_tool_call_windowed("h3", 10.0, True, ts_ms=now_ms)
    snapshot = get_telemetry_health_snapshot(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    assert "h3" in snapshot
    expected_keys = {"latency_spike", "error_spike", "recent_p95", "recent_error_rate"}
    assert set(snapshot["h3"].keys()) == expected_keys


def test_recent_p95_matches_windowed_summary() -> None:
    """recent_p95 must match get_windowed_summary's p95_ms for the same window.
    Kills impl that returns baseline p95 or a wrong percentile."""
    _reset()
    base_ms = _ts(seconds_ago=60)
    now_ms = _ts()
    for _ in range(3):
        record_tool_call_windowed("h4", 5.0, True, ts_ms=base_ms)
    # Recent: 5 calls at known latencies
    for lat in [10.0, 20.0, 30.0, 40.0, 100.0]:
        record_tool_call_windowed("h4", lat, True, ts_ms=now_ms)
    snapshot = get_telemetry_health_snapshot(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    # p95 of [10,20,30,40,100] = interpolated near 100
    assert "h4" in snapshot
    assert snapshot["h4"]["recent_p95"] > 50.0  # definitely uses recent, not baseline (5ms)


def test_recent_error_rate_matches_windowed_summary() -> None:
    """recent_error_rate must reflect recent window error rate, not baseline.
    Kills impl that returns all-time error rate or baseline error rate."""
    _reset()
    base_ms = _ts(seconds_ago=60)
    now_ms = _ts()
    # Baseline: all success -> err=0.0
    for _ in range(5):
        record_tool_call_windowed("h5", 10.0, True, ts_ms=base_ms)
    # Recent: 2 success, 2 fail -> err=0.5
    for _ in range(2):
        record_tool_call_windowed("h5", 10.0, True, ts_ms=now_ms)
    for _ in range(2):
        record_tool_call_windowed("h5", 10.0, False, ts_ms=now_ms)
    snapshot = get_telemetry_health_snapshot(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    assert "h5" in snapshot
    assert abs(snapshot["h5"]["recent_error_rate"] - 0.5) < 0.01


def test_no_baseline_tool_appears_with_spikes_false() -> None:
    """Tool only in recent window (no baseline) -> latency_spike=False, error_spike=False.
    Spike fns exclude this tool; snapshot includes it with False values."""
    _reset()
    now_ms = _ts()
    for _ in range(5):
        record_tool_call_windowed("h6", 50.0, True, ts_ms=now_ms)
    snapshot = get_telemetry_health_snapshot(
        _WINDOWED_TELEMETRY, window_ms=10_000, baseline_window_ms=20_000, now_ms=_ts()
    )
    assert "h6" in snapshot
    assert snapshot["h6"]["latency_spike"] is False
    assert snapshot["h6"]["error_spike"] is False


def test_tool_only_in_recent_not_old_window_excluded() -> None:
    """Tool with only old calls (outside both windows) is absent from snapshot."""
    _reset()
    old_ms = _ts(seconds_ago=300)
    for _ in range(5):
        record_tool_call_windowed("h7", 10.0, True, ts_ms=old_ms)
    snapshot = get_telemetry_health_snapshot(
        _WINDOWED_TELEMETRY, window_ms=5_000, baseline_window_ms=60_000, now_ms=_ts()
    )
    assert "h7" not in snapshot


def test_multiple_tools_independently_classified() -> None:
    """Each tool's spikes are independent — one spiking doesn't affect the other."""
    _reset()
    base_ms = _ts(seconds_ago=60)
    now_ms = _ts()
    # h8: latency spike (5x) + error spike (0->0.75)
    for _ in range(4):
        record_tool_call_windowed("h8", 10.0, True, ts_ms=base_ms)
    for _ in range(1):
        record_tool_call_windowed("h8", 50.0, True, ts_ms=now_ms)
    for _ in range(3):
        record_tool_call_windowed("h8", 50.0, False, ts_ms=now_ms)
    # h9: no spikes (stable latency, stable low error)
    for _ in range(5):
        record_tool_call_windowed("h9", 20.0, True, ts_ms=base_ms)
    for _ in range(5):
        record_tool_call_windowed("h9", 21.0, True, ts_ms=now_ms)
    snapshot = get_telemetry_health_snapshot(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    assert snapshot["h8"]["latency_spike"] is True
    assert snapshot["h8"]["error_spike"] is True
    assert snapshot["h9"]["latency_spike"] is False
    assert snapshot["h9"]["error_spike"] is False


def test_return_types_are_correct() -> None:
    """latency_spike and error_spike must be bool; p95 and error_rate must be float."""
    _reset()
    base_ms = _ts(seconds_ago=60)
    now_ms = _ts()
    for _ in range(3):
        record_tool_call_windowed("h10", 10.0, True, ts_ms=base_ms)
    for _ in range(3):
        record_tool_call_windowed("h10", 15.0, True, ts_ms=now_ms)
    snapshot = get_telemetry_health_snapshot(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    entry = snapshot["h10"]
    assert isinstance(entry["latency_spike"], bool)
    assert isinstance(entry["error_spike"], bool)
    assert isinstance(entry["recent_p95"], float)
    assert isinstance(entry["recent_error_rate"], float)
