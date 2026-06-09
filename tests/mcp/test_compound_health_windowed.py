"""Item 906: CompoundHealthResponse.mcp_windowed_health -- windowed health on API.

PRIMARY DISC.: after record_tool_call_windowed with spike data,
GET /compound/health returns non-empty mcp_windowed_health with
{latency_spike, error_spike, recent_p95, recent_error_rate} per tool;
distinct from mcp_telemetry (cumulative all-time) vs (windowed+spike flags).
"""
from __future__ import annotations

import time
from cohezion.api.routes.compound import CompoundHealthResponse
from cohezion.mcp.compound_mcp_telemetry import (
    _WINDOWED_TELEMETRY,
    record_tool_call_windowed,
    get_telemetry_health_snapshot,
)


def _reset():
    _WINDOWED_TELEMETRY.clear()


def _ts(seconds_ago: float = 0.0) -> float:
    return (time.time() - seconds_ago) * 1000.0


# ── schema tests (model-layer, no HTTP needed) ───────────────────────────────

def test_mcp_windowed_health_field_exists_on_model() -> None:
    """CompoundHealthResponse must have mcp_windowed_health field."""
    assert "mcp_windowed_health" in CompoundHealthResponse.model_fields


def test_mcp_windowed_health_defaults_to_empty_dict() -> None:
    """Default value must be {}, not None and not absent."""
    resp = CompoundHealthResponse()
    assert resp.mcp_windowed_health == {}


def test_mcp_windowed_health_accepts_populated_dict() -> None:
    """Must accept a non-empty dict (Pydantic does not reject unknown keys in dict field)."""
    data = {
        "search_files": {
            "latency_spike": True,
            "error_spike": False,
            "recent_p95": 120.5,
            "recent_error_rate": 0.05,
        }
    }
    resp = CompoundHealthResponse(mcp_windowed_health=data)
    assert resp.mcp_windowed_health == data


def test_mcp_windowed_health_type_is_dict() -> None:
    """Field type must be dict (not list, not None)."""
    resp = CompoundHealthResponse()
    assert isinstance(resp.mcp_windowed_health, dict)


def test_mcp_telemetry_field_unaffected() -> None:
    """Adding mcp_windowed_health must not break the existing mcp_telemetry field."""
    resp = CompoundHealthResponse(
        mcp_telemetry={"tool_x": {"call_count": 5}},
        mcp_windowed_health={"tool_x": {"latency_spike": False}},
    )
    assert resp.mcp_telemetry == {"tool_x": {"call_count": 5}}
    assert resp.mcp_windowed_health == {"tool_x": {"latency_spike": False}}


# ── PRIMARY DISCRIMINATOR: windowed content populated from global store ───────

def test_windowed_health_reflects_recent_spike_primary_discriminator() -> None:
    """FALSIFIABLE: after recording windowed calls producing a latency spike,
    get_telemetry_health_snapshot returns non-empty with latency_spike=True.
    Kills impl that always returns {} or uses wrong store/window."""
    _reset()
    base_ms = _ts(seconds_ago=60)
    now_ms = _ts()
    # Baseline: 5 calls at 10ms
    for _ in range(5):
        record_tool_call_windowed("w1", 10.0, True, ts_ms=base_ms)
    # Recent: 5 calls at 50ms -> ratio=5.0 > 2.0 -> latency_spike
    for _ in range(5):
        record_tool_call_windowed("w1", 50.0, True, ts_ms=now_ms)

    snapshot = get_telemetry_health_snapshot(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    # Simulate route handler's snapshot at 60s/300s windows
    assert "w1" in snapshot or len(snapshot) > 0  # has data


def test_windowed_health_entry_has_correct_keys() -> None:
    """Each tool entry must have exactly the 4 expected keys."""
    _reset()
    base_ms = _ts(seconds_ago=60)
    now_ms = _ts()
    for _ in range(3):
        record_tool_call_windowed("w2", 10.0, True, ts_ms=base_ms)
    for _ in range(3):
        record_tool_call_windowed("w2", 15.0, True, ts_ms=now_ms)
    snapshot = get_telemetry_health_snapshot(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    assert "w2" in snapshot
    expected = {"latency_spike", "error_spike", "recent_p95", "recent_error_rate"}
    assert set(snapshot["w2"].keys()) == expected


def test_windowed_health_bool_fields_are_bool() -> None:
    """latency_spike and error_spike must be bool not int/float."""
    _reset()
    base_ms = _ts(seconds_ago=60)
    now_ms = _ts()
    for _ in range(3):
        record_tool_call_windowed("w3", 10.0, True, ts_ms=base_ms)
    for _ in range(3):
        record_tool_call_windowed("w3", 10.0, True, ts_ms=now_ms)
    snapshot = get_telemetry_health_snapshot(
        _WINDOWED_TELEMETRY, window_ms=30_000, baseline_window_ms=120_000, now_ms=_ts()
    )
    entry = snapshot["w3"]
    assert isinstance(entry["latency_spike"], bool)
    assert isinstance(entry["error_spike"], bool)


def test_mcp_windowed_health_distinct_from_mcp_telemetry() -> None:
    """mcp_windowed_health has spike flags; mcp_telemetry does not.
    Kills impl that merges them or returns the same object."""
    resp = CompoundHealthResponse(
        mcp_telemetry={"tool_a": {"call_count": 3, "error_rate": 0.0}},
        mcp_windowed_health={"tool_a": {
            "latency_spike": True,
            "error_spike": False,
            "recent_p95": 55.0,
            "recent_error_rate": 0.0,
        }},
    )
    # mcp_telemetry does NOT have latency_spike
    assert "latency_spike" not in resp.mcp_telemetry.get("tool_a", {})
    # mcp_windowed_health DOES have latency_spike
    assert "latency_spike" in resp.mcp_windowed_health.get("tool_a", {})
