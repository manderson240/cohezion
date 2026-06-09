"""Item 909: record_tool_call_all() -- unified write to both cumulative + windowed stores.

PRIMARY DISC.: after one call, BOTH _TELEMETRY[tool] AND _WINDOWED_TELEMETRY[tool]
have an entry (kills impl that writes to only one store);
idempotent: second call -> count=2 in both; injectable ts_ms tested.
"""
from __future__ import annotations

import time
from cohezion.mcp.compound_mcp_telemetry import (
    _TELEMETRY,
    _WINDOWED_TELEMETRY,
    record_tool_call_all,
)


def _reset():
    _TELEMETRY.clear()
    _WINDOWED_TELEMETRY.clear()


def _ts(seconds_ago: float = 0.0) -> float:
    return (time.time() - seconds_ago) * 1000.0


# ── primary discriminator ─────────────────────────────────────────────────────

def test_both_stores_written_primary_discriminator() -> None:
    """FALSIFIABLE: after one call, BOTH _TELEMETRY and _WINDOWED_TELEMETRY have entry.
    Kills impl that writes to only one store or ignores the windowed store."""
    _reset()
    record_tool_call_all("all_tool", 25.0, True)
    assert "all_tool" in _TELEMETRY, "cumulative store not written"
    assert "all_tool" in _WINDOWED_TELEMETRY, "windowed store not written"


def test_cumulative_call_count_incremented() -> None:
    """Cumulative store must have call_count == 1 after one call."""
    _reset()
    record_tool_call_all("cnt_tool", 30.0, True)
    assert _TELEMETRY["cnt_tool"]["call_count"] == 1


def test_windowed_store_has_one_record() -> None:
    """Windowed store list must have exactly one tuple after one call."""
    _reset()
    record_tool_call_all("win_tool", 40.0, True)
    assert len(_WINDOWED_TELEMETRY["win_tool"]) == 1


def test_idempotent_two_calls_count_two_in_both() -> None:
    """Two calls -> call_count=2 cumulative + 2 windowed records."""
    _reset()
    record_tool_call_all("idem_tool", 10.0, True)
    record_tool_call_all("idem_tool", 20.0, False)
    assert _TELEMETRY["idem_tool"]["call_count"] == 2
    assert len(_WINDOWED_TELEMETRY["idem_tool"]) == 2


def test_injectable_ts_ms_stored_in_windowed_record() -> None:
    """ts_ms injected via parameter must appear in the windowed tuple."""
    _reset()
    fixed_ts = _ts(seconds_ago=100)
    record_tool_call_all("ts_tool", 15.0, True, ts_ms=fixed_ts)
    ts_stored, _, _ = _WINDOWED_TELEMETRY["ts_tool"][0]
    assert abs(ts_stored - fixed_ts) < 1.0  # injected ts matches


def test_error_counted_in_cumulative_store() -> None:
    """failure=True -> error_count in cumulative store incremented."""
    _reset()
    record_tool_call_all("err_tool", 10.0, True)
    record_tool_call_all("err_tool", 10.0, False)
    assert _TELEMETRY["err_tool"]["error_count"] == 1


def test_success_flag_stored_in_windowed_record() -> None:
    """success flag must appear in the windowed tuple (3rd element)."""
    _reset()
    record_tool_call_all("flag_tool", 10.0, False)
    _, _, ok = _WINDOWED_TELEMETRY["flag_tool"][0]
    assert ok is False


def test_latency_stored_in_windowed_record() -> None:
    """latency_ms must appear as the 2nd element of the windowed tuple."""
    _reset()
    record_tool_call_all("lat_tool", 77.0, True)
    _, lat, _ = _WINDOWED_TELEMETRY["lat_tool"][0]
    assert abs(lat - 77.0) < 0.01
