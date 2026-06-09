"""Item 882/885: get_windowed_summary() -- time-windowed telemetry filtering."""
from __future__ import annotations
import time
from cohezion.mcp.compound_mcp_telemetry import (
    record_tool_call_windowed,
    get_windowed_summary,
    _WINDOWED_TELEMETRY,
)


def _reset():
    _WINDOWED_TELEMETRY.clear()


def test_windowed_excludes_old_calls_primary_discriminator() -> None:
    """FALSIFIABLE: 3 old + 2 new calls; window sees only 2 (not 5)."""
    _reset()
    old_ts = (time.time() - 100) * 1000  # 100s ago
    now_ts = time.time() * 1000
    for _ in range(3):
        record_tool_call_windowed("t1", 10.0, True, ts_ms=old_ts)
    for _ in range(2):
        record_tool_call_windowed("t1", 15.0, True, ts_ms=now_ts)
    summary = get_windowed_summary(_WINDOWED_TELEMETRY, window_ms=5000)
    assert "t1" in summary
    assert summary["t1"]["call_count"] == 2   # only recent 2, not all 5


def test_empty_window_gives_empty_dict() -> None:
    _reset()
    old_ts = (time.time() - 100) * 1000
    record_tool_call_windowed("t2", 5.0, True, ts_ms=old_ts)
    summary = get_windowed_summary(_WINDOWED_TELEMETRY, window_ms=1000)
    assert summary == {}


def test_all_calls_in_window_included() -> None:
    _reset()
    now_ts = time.time() * 1000
    for i in range(4):
        record_tool_call_windowed("t3", float(i + 1), True, ts_ms=now_ts)
    summary = get_windowed_summary(_WINDOWED_TELEMETRY, window_ms=60_000)
    assert summary["t3"]["call_count"] == 4


def test_windowed_error_rate_only_recent() -> None:
    _reset()
    old_ts = (time.time() - 200) * 1000
    now_ts = time.time() * 1000
    record_tool_call_windowed("t4", 10.0, False, ts_ms=old_ts)  # old error
    record_tool_call_windowed("t4", 10.0, True, ts_ms=now_ts)   # recent success
    summary = get_windowed_summary(_WINDOWED_TELEMETRY, window_ms=5000)
    # only recent call -> 0 errors -> error_rate = 0.0
    assert summary["t4"]["error_rate"] == 0.0


def test_empty_store_returns_empty_dict() -> None:
    _reset()
    assert get_windowed_summary(_WINDOWED_TELEMETRY, window_ms=10_000) == {}


def test_multiple_tools_windowed_independently() -> None:
    _reset()
    now_ts = time.time() * 1000
    old_ts = (time.time() - 200) * 1000
    record_tool_call_windowed("ta", 5.0, True, ts_ms=now_ts)
    record_tool_call_windowed("tb", 5.0, True, ts_ms=old_ts)  # old; excluded
    summary = get_windowed_summary(_WINDOWED_TELEMETRY, window_ms=5000)
    assert "ta" in summary
    assert "tb" not in summary


def test_windowed_call_count_is_int() -> None:
    _reset()
    now_ts = time.time() * 1000
    record_tool_call_windowed("t5", 5.0, True, ts_ms=now_ts)
    summary = get_windowed_summary(_WINDOWED_TELEMETRY, window_ms=10_000)
    assert isinstance(summary["t5"]["call_count"], int)


def test_windowed_error_rate_is_float() -> None:
    _reset()
    now_ts = time.time() * 1000
    record_tool_call_windowed("t6", 5.0, False, ts_ms=now_ts)
    summary = get_windowed_summary(_WINDOWED_TELEMETRY, window_ms=10_000)
    assert isinstance(summary["t6"]["error_rate"], float)


def test_windowed_keys_match_cumulative_for_recent() -> None:
    _reset()
    now_ts = time.time() * 1000
    record_tool_call_windowed("t7", 10.0, True, ts_ms=now_ts)
    summary = get_windowed_summary(_WINDOWED_TELEMETRY, window_ms=60_000)
    assert "call_count" in summary["t7"] and "error_rate" in summary["t7"]


def test_half_calls_in_window() -> None:
    _reset()
    old_ts = (time.time() - 1000) * 1000
    now_ts = time.time() * 1000
    for _ in range(6):
        record_tool_call_windowed("t8", 5.0, True, ts_ms=old_ts)
    for _ in range(4):
        record_tool_call_windowed("t8", 5.0, True, ts_ms=now_ts)
    summary = get_windowed_summary(_WINDOWED_TELEMETRY, window_ms=5000)
    assert summary["t8"]["call_count"] == 4
