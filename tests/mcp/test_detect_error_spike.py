"""Item 904: detect_error_spike() -- MCP error-rate delta spike detection.

PRIMARY DISC.: baseline_err=0.0 + recent_err=0.5 -> True (delta=0.5>0.2);
baseline_err=0.3 + recent_err=0.4 -> False (delta=0.1<=0.2); empty -> {};
distinct from detect_latency_spike (uses error-rate delta, not p95 ratio).
"""

from __future__ import annotations

import time
from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    record_tool_call_windowed,
    detect_error_spike,
)


def _reset():
    _WINDOWED_TELEMETRY.clear()


def _ts(seconds_ago: float = 0.0) -> float:
    return (time.time() - seconds_ago) * 1000.0


# ── primary discriminator ─────────────────────────────────────────────────────


def test_error_rate_delta_above_0_2_returns_true_primary_discriminator() -> None:
    """FALSIFIABLE: baseline err=0.0, recent err=0.5 -> delta=0.5 > 0.2 -> True.
    Kills impl using latency ratio or always returning False."""
    _reset()
    base_ms = _ts(seconds_ago=60)
    now_ms = _ts()
    # Baseline: 5 successes (err=0.0)
    for _ in range(5):
        record_tool_call_windowed("e1", 10.0, True, ts_ms=base_ms)
    # Recent: 2 success, 2 fail (err=0.5)
    for _ in range(2):
        record_tool_call_windowed("e1", 10.0, True, ts_ms=now_ms)
    for _ in range(2):
        record_tool_call_windowed("e1", 10.0, False, ts_ms=now_ms)
    result = detect_error_spike(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    assert "e1" in result
    assert result["e1"] is True


def test_error_rate_delta_below_threshold_returns_false() -> None:
    """FALSIFIABLE: baseline err=0.3, recent err=0.4 -> delta=0.1 <= 0.2 -> False.
    Kills impl that triggers on any error rate increase."""
    _reset()
    base_ms = _ts(seconds_ago=60)
    now_ms = _ts()
    # Baseline: 3 success, 1 fail -> err=0.25 (close to 0.3)
    for _ in range(3):
        record_tool_call_windowed("e2", 10.0, True, ts_ms=base_ms)
    record_tool_call_windowed("e2", 10.0, False, ts_ms=base_ms)
    # Recent: 3 success, 2 fail -> err=0.4
    for _ in range(3):
        record_tool_call_windowed("e2", 10.0, True, ts_ms=now_ms)
    for _ in range(2):
        record_tool_call_windowed("e2", 10.0, False, ts_ms=now_ms)
    result = detect_error_spike(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    # delta = 0.4 - 0.25 = 0.15 < 0.2 -> False
    assert result.get("e2") is not True


def test_empty_store_returns_empty_dict() -> None:
    _reset()
    assert (
        detect_error_spike(
            _WINDOWED_TELEMETRY, window_ms=5_000, baseline_window_ms=60_000, now_ms=_ts()
        )
        == {}
    )


def test_no_recent_calls_tool_excluded() -> None:
    _reset()
    old_ms = _ts(seconds_ago=300)
    for _ in range(5):
        record_tool_call_windowed("e3", 10.0, True, ts_ms=old_ms)
    result = detect_error_spike(
        _WINDOWED_TELEMETRY, window_ms=5_000, baseline_window_ms=60_000, now_ms=_ts()
    )
    assert "e3" not in result


def test_no_baseline_calls_tool_excluded() -> None:
    """When all calls are recent (no baseline), tool is excluded (can't compute delta)."""
    _reset()
    now_ms = _ts()
    for _ in range(5):
        record_tool_call_windowed("e4", 10.0, True, ts_ms=now_ms)
    result = detect_error_spike(
        _WINDOWED_TELEMETRY, window_ms=10_000, baseline_window_ms=20_000, now_ms=_ts()
    )
    assert "e4" not in result


def test_exactly_at_threshold_not_spike() -> None:
    """delta == 0.2 (exactly) must NOT be a spike (strict > 0.2)."""
    _reset()
    base_ms = _ts(seconds_ago=60)
    now_ms = _ts()
    # Baseline: 5 success -> err=0.0
    for _ in range(5):
        record_tool_call_windowed("e5", 10.0, True, ts_ms=base_ms)
    # Recent: 4 success, 1 fail -> err=0.2 -> delta=0.2 exactly
    for _ in range(4):
        record_tool_call_windowed("e5", 10.0, True, ts_ms=now_ms)
    record_tool_call_windowed("e5", 10.0, False, ts_ms=now_ms)
    result = detect_error_spike(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    # delta = 0.2 - 0.0 = 0.2; strict > 0.2 -> False
    assert result.get("e5") is not True


def test_multiple_tools_independently_classified() -> None:
    """Tool with spike and tool without spike classified independently."""
    _reset()
    base_ms = _ts(seconds_ago=60)
    now_ms = _ts()
    # e6: spike (err jumps 0.0 -> 0.8)
    for _ in range(5):
        record_tool_call_windowed("e6", 10.0, True, ts_ms=base_ms)
    for _ in range(2):
        record_tool_call_windowed("e6", 10.0, True, ts_ms=now_ms)
    for _ in range(8):
        record_tool_call_windowed("e6", 10.0, False, ts_ms=now_ms)
    # e7: no spike (err stays at 0.0)
    for _ in range(5):
        record_tool_call_windowed("e7", 10.0, True, ts_ms=base_ms)
    for _ in range(5):
        record_tool_call_windowed("e7", 10.0, True, ts_ms=now_ms)
    result = detect_error_spike(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    assert result.get("e6") is True
    assert result.get("e7") is not True


def test_return_values_are_bool() -> None:
    _reset()
    base_ms = _ts(seconds_ago=60)
    now_ms = _ts()
    for _ in range(5):
        record_tool_call_windowed("e8", 10.0, True, ts_ms=base_ms)
    for _ in range(3):
        record_tool_call_windowed("e8", 10.0, False, ts_ms=now_ms)
    result = detect_error_spike(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    for v in result.values():
        assert isinstance(v, bool)
