"""Item 903: detect_latency_spike() -- MCP p95 latency spike detection.

PRIMARY DISC.: spike_ratio>2.0 -> True; ratio=1.5 -> False; {} when no data;
distinct from get_windowed_summary (new per-tool bool, not a latency summary).
"""

from __future__ import annotations

import time
from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    record_tool_call_windowed,
    detect_latency_spike,
)


def _reset():
    _WINDOWED_TELEMETRY.clear()


def _ts(seconds_ago: float = 0.0) -> float:
    return (time.time() - seconds_ago) * 1000.0


# ── primary discriminator ─────────────────────────────────────────────────────


def test_spike_ratio_above_2_returns_true_primary_discriminator() -> None:
    """FALSIFIABLE: p95_recent=60ms, p95_baseline=20ms -> ratio=3.0 -> True.
    Kills impl that always returns False, or uses ratio threshold != 2.0."""
    _reset()
    now_ms = _ts()
    baseline_ms = _ts(seconds_ago=60)
    # Baseline: 5 calls at 20ms (60s ago)
    for _ in range(5):
        record_tool_call_windowed("t1", 20.0, True, ts_ms=baseline_ms)
    # Recent: 5 calls at 60ms (just now)
    for _ in range(5):
        record_tool_call_windowed("t1", 60.0, True, ts_ms=now_ms)
    result = detect_latency_spike(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    assert "t1" in result
    assert result["t1"] is True


def test_spike_ratio_below_2_returns_false() -> None:
    """FALSIFIABLE: p95_recent=25ms, p95_baseline=20ms -> ratio=1.25 -> False.
    Kills impl that returns True for any latency increase."""
    _reset()
    now_ms = _ts()
    baseline_ms = _ts(seconds_ago=60)
    for _ in range(5):
        record_tool_call_windowed("t2", 20.0, True, ts_ms=baseline_ms)
    for _ in range(5):
        record_tool_call_windowed("t2", 25.0, True, ts_ms=now_ms)
    result = detect_latency_spike(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    assert "t2" not in result or result["t2"] is False


def test_empty_store_returns_empty_dict() -> None:
    """FALSIFIABLE: no calls -> {} (kills impl returning None or raising)."""
    _reset()
    result = detect_latency_spike(
        _WINDOWED_TELEMETRY, window_ms=5_000, baseline_window_ms=60_000, now_ms=_ts()
    )
    assert result == {}


def test_no_recent_calls_tool_excluded() -> None:
    """When recent window has no calls (all calls are old), tool is excluded."""
    _reset()
    old_ms = _ts(seconds_ago=300)
    for _ in range(5):
        record_tool_call_windowed("t3", 10.0, True, ts_ms=old_ms)
    result = detect_latency_spike(
        _WINDOWED_TELEMETRY, window_ms=5_000, baseline_window_ms=60_000, now_ms=_ts()
    )
    assert "t3" not in result


def test_no_baseline_calls_tool_excluded() -> None:
    """When baseline window has no calls (all calls are very recent), tool is excluded."""
    _reset()
    now_ms = _ts()
    for _ in range(5):
        record_tool_call_windowed("t4", 50.0, True, ts_ms=now_ms)
    result = detect_latency_spike(
        _WINDOWED_TELEMETRY, window_ms=10_000, baseline_window_ms=20_000, now_ms=_ts()
    )
    # no baseline to compare against -> can't compute ratio -> excluded
    assert "t4" not in result


def test_multiple_tools_independently_detected() -> None:
    """Tool with spike and tool without spike are correctly classified."""
    _reset()
    now_ms = _ts()
    base_ms = _ts(seconds_ago=60)
    # t5: spike (60ms vs 10ms -> ratio=6.0)
    for _ in range(5):
        record_tool_call_windowed("t5", 10.0, True, ts_ms=base_ms)
    for _ in range(5):
        record_tool_call_windowed("t5", 60.0, True, ts_ms=now_ms)
    # t6: no spike (11ms vs 10ms -> ratio=1.1)
    for _ in range(5):
        record_tool_call_windowed("t6", 10.0, True, ts_ms=base_ms)
    for _ in range(5):
        record_tool_call_windowed("t6", 11.0, True, ts_ms=now_ms)
    result = detect_latency_spike(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    assert result.get("t5") is True
    assert result.get("t6") is not True


def test_return_type_is_dict_of_bool() -> None:
    """Result values must be bool, not float or string."""
    _reset()
    now_ms = _ts()
    base_ms = _ts(seconds_ago=60)
    for _ in range(3):
        record_tool_call_windowed("t7", 10.0, True, ts_ms=base_ms)
    for _ in range(3):
        record_tool_call_windowed("t7", 40.0, True, ts_ms=now_ms)
    result = detect_latency_spike(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    for v in result.values():
        assert isinstance(v, bool)


def test_exactly_at_ratio_2_is_not_spike() -> None:
    """Ratio exactly == 2.0 must NOT trigger spike (strict >2.0 threshold)."""
    _reset()
    now_ms = _ts()
    base_ms = _ts(seconds_ago=60)
    for _ in range(5):
        record_tool_call_windowed("t8", 10.0, True, ts_ms=base_ms)
    for _ in range(5):
        record_tool_call_windowed("t8", 20.0, True, ts_ms=now_ms)
    result = detect_latency_spike(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    # ratio = 20/10 = 2.0 -> strict > 2.0 -> False
    assert result.get("t8") is not True


def test_large_spike_ratio_5x_returns_true() -> None:
    """5x spike clearly above threshold."""
    _reset()
    now_ms = _ts()
    base_ms = _ts(seconds_ago=60)
    for _ in range(5):
        record_tool_call_windowed("t9", 10.0, True, ts_ms=base_ms)
    for _ in range(5):
        record_tool_call_windowed("t9", 50.0, True, ts_ms=now_ms)
    result = detect_latency_spike(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    assert result.get("t9") is True
