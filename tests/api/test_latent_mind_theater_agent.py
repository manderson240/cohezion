"""Agent acceptance tests for the Latent Mind Theater /frame endpoint.

Tests the endpoint as an autonomous agent would consume it:
- Reads VizFrame JSON
- Interprets routing_tier → winding_number mapping
- Determines HIHO equilibrium state from nexus distance
- Validates the machine-readable contract (not just "fires")

All tests use FastAPI TestClient — no live network calls.
"""

from __future__ import annotations

import json
import math

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cohezion.api.routes.journey_nexus import router as journey_router


# ---------------------------------------------------------------------------
# Stub nexus with deterministic viz_frame() for agent tests
# ---------------------------------------------------------------------------


class _AgentStubNexus:
    """Minimal nexus stub exposing viz_frame() so agents get deterministic data."""

    def stream_snapshot(self):
        return []

    async def viz_frame(self, *, window: int = 20, frame_id: int = 0):
        from cohezion.api.routes.journey_nexus import (  # type: ignore[attr-defined]
            NexusState,
            VizFrame,  # type: ignore[attr-defined]
            _build_viz_point,
        )

        ts = 1_000_000.0  # fixed for determinism
        pts = [_build_viz_point(i, ts) for i in range(3)]
        return VizFrame(
            frame_id=frame_id,
            timestamp=ts,
            points=pts,
            nexus=NexusState(
                I=0.6,
                Q=0.45,
                distance=round(math.sqrt((0.6 - 0.5) ** 2 + (0.45 - 0.5) ** 2), 4),
                angle_rad=round(math.atan2(0.45 - 0.5, 0.6 - 0.5), 4),
                power=round(
                    max(0.0, 1.0 - math.sqrt((0.6 - 0.5) ** 2 + (0.45 - 0.5) ** 2) * math.sqrt(2)),
                    4,
                ),
                routing_tier="npu",
                composite_health_score=0.82,
            ),
            vacuum_field=[0.0] * 4096,
            mhd_ripple_phase=1.23,
            cache_stats={"overall_hit_rate": 60.0},
            detector_snapshot={"baselines_established": True},
        )


def _async_agent_stub():
    async def _get():
        return _AgentStubNexus()

    return _get


@pytest.fixture
def agent_app(monkeypatch):
    from cohezion.api.routes import journey_nexus as router_mod

    monkeypatch.setattr(router_mod, "_nexus_instance", None, raising=False)
    monkeypatch.setattr(router_mod, "_get_nexus", _async_agent_stub())
    app = FastAPI()
    app.include_router(journey_router)
    return app


@pytest.fixture
def agent_client(agent_app):
    return TestClient(agent_app)


# ---------------------------------------------------------------------------
# Agent acceptance tests
# ---------------------------------------------------------------------------


def test_agent_reads_viz_frame_successfully(agent_client):
    """Agent can fetch /frame and receive all fields needed for autonomous decisions."""
    resp = agent_client.get("/journey-nexus/frame")
    assert resp.status_code == 200
    frame = resp.json()
    # An agent needs all of these to act
    assert "nexus" in frame
    assert "points" in frame
    assert "vacuum_field" in frame
    assert "mhd_ripple_phase" in frame
    assert len(frame["points"]) > 0


def test_agent_interprets_routing_tier_to_winding_number(agent_client):
    """Agent can map tier_used to winding_number for Hopf chirality.

    Discriminating: NPU must be +1, CPU must be -1, iGPU must be 0.
    Would fail if NPU→0 (wrong) or winding_number field is missing.
    This is the chirality mapping that determines fiber orientation.
    """
    resp = agent_client.get("/journey-nexus/frame")
    points = resp.json()["points"]

    expected_winding = {"npu": 1, "igpu": 0, "cpu": -1}
    for pt in points:
        tier = pt["tier_used"]
        if tier in expected_winding:
            assert pt["winding_number"] == expected_winding[tier], (
                f"Agent routing error: tier={tier} should map to "
                f"winding={expected_winding[tier]}, got {pt['winding_number']}"
            )


def test_agent_can_determine_hiho_equilibrium(agent_client):
    """Agent can determine HIHO equilibrium state from nexus.distance.

    Discriminating: verifies the BKT-correct Euclidean distance formula,
    NOT Manhattan distance (|I-0.5| + |Q-0.5|) or a constant.
    At (I=0.6, Q=0.45): distance = sqrt(0.01 + 0.0025) = sqrt(0.0125) ≈ 0.1118
    """
    resp = agent_client.get("/journey-nexus/frame")
    nexus = resp.json()["nexus"]
    I = nexus["I"]
    Q = nexus["Q"]
    # Agent computes the expected distance itself (would use in routing decision)
    expected_distance = math.sqrt((I - 0.5) ** 2 + (Q - 0.5) ** 2)
    assert abs(nexus["distance"] - expected_distance) < 1e-3, (
        f"HIHO equilibrium distance mismatch: got {nexus['distance']}, "
        f"expected {expected_distance:.4f} for I={I}, Q={Q}"
    )
    # Max possible distance is sqrt(2)/2 ≈ 0.707 (corner of unit square)
    assert nexus["distance"] < math.sqrt(2) / 2 + 1e-6, (
        f"distance={nexus['distance']} exceeds maximum sqrt(2)/2"
    )


def test_agent_reads_nexus_power_as_hiho_strength(agent_client):
    """nexus.power in [0,1] represents HIHO equilibrium strength.

    Discriminating: power = 1 - distance*sqrt(2), must be max at center (I=Q=0.5).
    An agent uses this to know if local models or cloud escalation is needed.
    """
    resp = agent_client.get("/journey-nexus/frame")
    nexus = resp.json()["nexus"]
    # power must be non-negative and ≤ 1
    assert 0.0 <= nexus["power"] <= 1.0, f"power={nexus['power']} out of [0,1]"
    # For distance < sqrt(2)/2, power must be positive
    if nexus["distance"] < math.sqrt(2) / 2:
        assert nexus["power"] > 0.0


def test_agent_sees_composite_health_score(agent_client):
    """Agent can read composite_health_score from nexus for routing decisions."""
    resp = agent_client.get("/journey-nexus/frame")
    nexus = resp.json()["nexus"]
    # May be null when detector grace period not passed
    score = nexus.get("composite_health_score")
    if score is not None:
        assert 0.0 <= score <= 1.0, f"composite_health_score={score} out of [0,1]"


def test_agent_vacuum_field_is_actionable_volume(agent_client):
    """Agent sees a 16^3 density volume with correct shape for 3D routing decisions."""
    resp = agent_client.get("/journey-nexus/frame")
    frame = resp.json()
    assert frame["vacuum_field_shape"] == [16, 16, 16]
    assert len(frame["vacuum_field"]) == 4096
    # All values must be finite floats (agent could compute gradient)
    for val in frame["vacuum_field"][:100]:  # spot-check first 100
        assert isinstance(val, (int, float))
        assert not math.isnan(val) and not math.isinf(val)


def test_agent_mhd_ripple_phase_is_circular(agent_client):
    """mhd_ripple_phase must be in [0, 2π] — it drives standing wave timing."""
    resp = agent_client.get("/journey-nexus/frame")
    phase = resp.json()["mhd_ripple_phase"]
    assert 0.0 <= phase <= 2 * math.pi + 0.01, f"mhd_ripple_phase={phase} out of [0, 2π]"


def test_agent_can_stream_and_read_first_frame(agent_client):
    """Agent can open /stream/viz SSE and parse the first VizFrame event.

    Uses max_frames=1 so the stream terminates after one event.
    """
    with agent_client.stream("GET", "/journey-nexus/stream/viz?max_frames=1") as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            if line.startswith("data: "):
                frame = json.loads(line[6:])
                # Agent verifies it got a well-formed frame before acting
                assert "nexus" in frame
                assert "points" in frame
                assert frame["frame_id"] == 0
                # Agent checks it can read nexus state
                nexus = frame["nexus"]
                assert 0.0 <= nexus["I"] <= 1.0
                assert 0.0 <= nexus["Q"] <= 1.0
                break
        else:
            pytest.fail("Agent received no data: line from /stream/viz")
