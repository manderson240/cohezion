"""Item 906: mcp_windowed_health field on CompoundHealthResponse + route wiring.

PRIMARY DISC.: field must be populated from get_telemetry_health_snapshot() after
recording windowed calls — kills impl that always returns {} or missing the field.
"""

from __future__ import annotations


# ── structural: field exists and defaults to {} ──────────────────────────────


def test_compound_health_response_has_mcp_windowed_health_field() -> None:
    """CompoundHealthResponse has mcp_windowed_health field defaulting to {}."""
    from cohezion.api.routes.compound import CompoundHealthResponse

    resp = CompoundHealthResponse()
    assert hasattr(resp, "mcp_windowed_health"), (
        "CompoundHealthResponse must have mcp_windowed_health field"
    )
    assert resp.mcp_windowed_health == {}, f"Default must be {{}}; got {resp.mcp_windowed_health!r}"


def test_mcp_windowed_health_field_accepts_snapshot_data() -> None:
    """mcp_windowed_health must accept a health snapshot dict (not just empty)."""
    from cohezion.api.routes.compound import CompoundHealthResponse

    snapshot = {
        "tool_a": {
            "latency_spike": True,
            "error_spike": False,
            "recent_p95": 55.3,
            "recent_error_rate": 0.0,
        }
    }
    resp = CompoundHealthResponse(mcp_windowed_health=snapshot)
    assert resp.mcp_windowed_health == snapshot


def test_mcp_windowed_health_is_separate_from_mcp_telemetry() -> None:
    """mcp_windowed_health and mcp_telemetry are distinct fields (kills merge-impl)."""
    from cohezion.api.routes.compound import CompoundHealthResponse

    resp = CompoundHealthResponse(
        mcp_telemetry={
            "tool_x": {"call_count": 5, "error_rate": 0.0, "p50_ms": 10.0, "p95_ms": 12.0}
        },
        mcp_windowed_health={
            "tool_x": {
                "latency_spike": False,
                "error_spike": False,
                "recent_p95": 10.0,
                "recent_error_rate": 0.0,
            }
        },
    )
    assert "call_count" not in resp.mcp_windowed_health.get("tool_x", {}), (
        "mcp_windowed_health must not contain call_count (that's mcp_telemetry)"
    )
    assert "latency_spike" not in resp.mcp_telemetry.get("tool_x", {}), (
        "mcp_telemetry must not contain latency_spike (that's mcp_windowed_health)"
    )


# ── route integration: field populated from real windowed data ────────────────


def test_health_route_returns_mcp_windowed_health_key() -> None:
    """GET /compound/health JSON must include mcp_windowed_health key."""
    from fastapi.testclient import TestClient
    from cohezion.api import app

    client = TestClient(app)
    resp = client.get("/compound/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "mcp_windowed_health" in data, (
        f"mcp_windowed_health key missing from response; keys={list(data)}"
    )


def test_health_route_mcp_windowed_health_default_empty() -> None:
    """mcp_windowed_health defaults to {} when no windowed calls recorded."""
    from fastapi.testclient import TestClient
    from cohezion.api import app
    from cohezion.mcp.compound_mcp_telemetry import _WINDOWED_TELEMETRY

    _WINDOWED_TELEMETRY.clear()  # ensure no prior data
    client = TestClient(app)
    resp = client.get("/compound/health")
    data = resp.json()
    assert data["mcp_windowed_health"] == {}, (
        f"No windowed data -> {{}}; got {data['mcp_windowed_health']!r}"
    )


def test_health_route_mcp_windowed_health_populated_primary_discriminator() -> None:
    """PRIMARY DISC.: after recording windowed calls, field is non-empty dict.

    Kills impl that always returns {}.  Records calls then verifies the snapshot
    appears in the health response with at least one tool and the correct keys.
    """
    import time
    from fastapi.testclient import TestClient
    from cohezion.api import app
    from cohezion.mcp.compound_mcp_telemetry import _WINDOWED_TELEMETRY, record_tool_call_windowed

    _WINDOWED_TELEMETRY.clear()
    now_ms = time.time() * 1000.0
    # Recent calls (within 60s window)
    for _ in range(5):
        record_tool_call_windowed("probe_tool", 20.0, True, ts_ms=now_ms - 1_000)

    client = TestClient(app)
    resp = client.get("/compound/health")
    assert resp.status_code == 200
    data = resp.json()
    wh = data.get("mcp_windowed_health", {})
    assert isinstance(wh, dict), f"mcp_windowed_health must be dict; got {type(wh)}"
    assert "probe_tool" in wh, (
        f"PRIMARY DISC.: probe_tool must appear in windowed health after recording; got {list(wh)}"
    )
    tool_data = wh["probe_tool"]
    for key in ("latency_spike", "error_spike", "recent_p95", "recent_error_rate"):
        assert key in tool_data, f"Missing key '{key}' in tool snapshot; got {list(tool_data)}"


def test_health_route_snapshot_values_match_expected() -> None:
    """Snapshot values for a known-spike tool must have latency_spike=True."""
    import time
    from fastapi.testclient import TestClient
    from cohezion.api import app
    from cohezion.mcp.compound_mcp_telemetry import _WINDOWED_TELEMETRY, record_tool_call_windowed

    _WINDOWED_TELEMETRY.clear()
    now_ms = time.time() * 1000.0
    window_ms = 60_000.0
    baseline_window_ms = 300_000.0
    # Baseline: 10ms (old, in baseline window)
    baseline_ts = now_ms - window_ms - 60_000.0
    for _ in range(5):
        record_tool_call_windowed("spiking_tool", 10.0, True, ts_ms=baseline_ts)
    # Recent: 60ms (spike: ratio=6.0 > 2.0)
    recent_ts = now_ms - 1_000.0
    for _ in range(5):
        record_tool_call_windowed("spiking_tool", 60.0, True, ts_ms=recent_ts)

    client = TestClient(app)
    resp = client.get("/compound/health")
    data = resp.json()
    wh = data.get("mcp_windowed_health", {})
    if "spiking_tool" in wh:
        assert wh["spiking_tool"]["latency_spike"] is True, (
            f"ratio=6.0 -> latency_spike must be True; got {wh['spiking_tool']}"
        )
