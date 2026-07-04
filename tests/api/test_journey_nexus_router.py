"""Smoke tests for the journey_nexus router (FastAPI endpoints, mocked service).

Uses TestClient with no network calls. The JourneyNexus service is
replaced with a stub so we never touch FLUME/Omni/Quadrature.
"""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cohezion.api.routes.journey_nexus import router
from cohezion.api.services.journey_nexus import (
    EVOEvent,
    NarrateResult,
    OmniChatOutcome,
    QuadratureOutcome,
)


# ----- Service stub ---------------------------------------------------------


class _StubNexus:
    """A minimal stub that mimics the JourneyNexus surface the router calls."""

    def __init__(self) -> None:
        self._events: list[EVOEvent] = [
            EVOEvent(
                id="e1",
                timestamp=0.0,
                z_256=[0.5] * 256,
                state_12d=[0.5] * 12,
                kind="deliberation",
                voice="architect",
                score=0.91,
                journey_id="j1",
            ),
        ]

    async def subscribe(self, journey_id=None):
        for ev in self._events:
            if journey_id is None or ev.journey_id == journey_id:
                yield ev

    def stream_snapshot(self):
        return list(self._events)

    async def quadrature(self, journey_id, *, mode="preflight"):
        return QuadratureOutcome(
            approved=True,
            consensus_score=0.92,
            alignment_score=0.88,
            voice_responses=[
                {
                    "voice": "architect",
                    "approval_score": 0.95,
                    "concerns": [],
                    "recommendations": ["go"],
                    "score": 0.95,
                },
            ],
            rejection_reason=None,
        )

    async def narrate(self, journey_id, *, with_image=False):
        return NarrateResult(
            journey_id=journey_id,
            text="hello world",
            audio_b64="ZmFrZS1tcDM=",
            image_b64=("aW1n" if with_image else None),
            coherence=0.7,
        )

    async def omni_chat(self, journey_id, *, message):
        return OmniChatOutcome(
            text="I can help",
            tool_calls=[],
            images_b64=[],
            audio_b64="",
        )


# ----- Fixtures -------------------------------------------------------------


@pytest.fixture
def app(monkeypatch):
    """A FastAPI app with the journey-nexus router mounted + stubbed service."""
    from cohezion.api.routes import journey_nexus as router_mod

    # Reset the module-level singleton so the next _get_nexus() call builds our stub
    monkeypatch.setattr(router_mod, "_nexus_instance", None, raising=False)
    monkeypatch.setattr(router_mod, "_get_nexus", _async_stub_nexus())

    app = FastAPI()
    app.include_router(router)
    return app


def _async_stub_nexus():
    async def _get():
        return _StubNexus()

    return _get


@pytest.fixture
def client(app):
    return TestClient(app)


# ----- Tests ----------------------------------------------------------------


def test_evo_snapshot_returns_list(client):
    resp = client.get("/journey-nexus/evo/snapshot")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "e1"
    assert data[0]["voice"] == "architect"


def test_evo_snapshot_event_shape(client):
    resp = client.get("/journey-nexus/evo/snapshot")
    ev = resp.json()[0]
    assert "z_256" in ev and len(ev["z_256"]) == 256
    assert "state_12d" in ev and len(ev["state_12d"]) == 12


def test_quadrature_default_mode(client):
    resp = client.get("/journey-nexus/quadrature/j1")
    assert resp.status_code == 200
    out = resp.json()
    assert out["approved"] is True
    assert out["consensus_score"] == 0.92
    assert out["alignment_score"] == 0.88
    assert len(out["voice_responses"]) == 1


def test_quadrature_full_mode(client):
    resp = client.get("/journey-nexus/quadrature/j1?mode=full")
    assert resp.status_code == 200


def test_quadrature_bad_mode_rejected(client):
    resp = client.get("/journey-nexus/quadrature/j1?mode=invalid")
    # FastAPI's pattern matcher returns 422 for query validation
    assert resp.status_code == 422


def test_narrate_default_no_image(client):
    resp = client.get("/journey-nexus/narrate/j1")
    assert resp.status_code == 200
    out = resp.json()
    assert out["journey_id"] == "j1"
    assert out["text"] == "hello world"
    assert out["audio_b64"] == "ZmFrZS1tcDM="
    assert out["image_b64"] is None


def test_narrate_with_image(client):
    resp = client.get("/journey-nexus/narrate/j1?with_image=true")
    assert resp.status_code == 200
    assert resp.json()["image_b64"] == "aW1n"


def test_omni_chat_post(client):
    resp = client.post("/journey-nexus/omni/j1", json={"message": "render a sphere"})
    assert resp.status_code == 200
    out = resp.json()
    assert out["text"] == "I can help"
    assert out["tool_calls"] == []


def test_omni_chat_empty_message_rejected(client):
    resp = client.post("/journey-nexus/omni/j1", json={"message": ""})
    # Pydantic min_length=1 enforces non-empty
    assert resp.status_code == 422


def test_stream_evo_sse_format(client):
    """The /stream/evo endpoint must return text/event-stream with a data: line."""
    # TestClient handles SSE synchronously via .iter_lines()
    with client.stream("GET", "/journey-nexus/stream/evo") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        # Read the first data line
        for line in resp.iter_lines():
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                assert payload["id"] == "e1"
                assert payload["voice"] == "architect"
                break
        else:
            pytest.fail("No data: line in SSE stream")


# ---------------------------------------------------------------------------
# Latent Mind Theater: VizFrame discriminating tests
# ---------------------------------------------------------------------------

import math  # noqa: E402  (below existing imports for clarity)


def test_viz_frame_returns_correct_structure(client):
    """GET /frame must return a complete VizFrame with all required top-level fields."""
    resp = client.get("/journey-nexus/frame")
    assert resp.status_code == 200
    frame = resp.json()
    required_keys = {
        "frame_id", "timestamp", "points", "nexus",
        "vacuum_field", "vacuum_field_shape", "mhd_ripple_phase",
        "cache_stats", "detector_snapshot",
    }
    assert required_keys <= set(frame.keys()), f"Missing keys: {required_keys - set(frame.keys())}"


def test_viz_frame_nexus_iq_in_range(client):
    """Nexus I and Q must be in [0, 1] — they are normalized probabilities."""
    resp = client.get("/journey-nexus/frame")
    nexus = resp.json()["nexus"]
    assert 0.0 <= nexus["I"] <= 1.0, f"I={nexus['I']} out of [0,1]"
    assert 0.0 <= nexus["Q"] <= 1.0, f"Q={nexus['Q']} out of [0,1]"


def test_viz_frame_nexus_distance_formula(client):
    """nexus.distance must equal sqrt((I-0.5)^2 + (Q-0.5)^2) exactly.

    Discriminating: would fail for Manhattan distance or a constant 0.
    This is the BKT-correct formula for distance from HIHO equilibrium.
    """
    resp = client.get("/journey-nexus/frame")
    nexus = resp.json()["nexus"]
    expected = math.sqrt((nexus["I"] - 0.5) ** 2 + (nexus["Q"] - 0.5) ** 2)
    assert abs(nexus["distance"] - expected) < 1e-3, (
        f"distance={nexus['distance']}, expected={expected:.6f}"
    )


def test_viz_frame_vacuum_field_shape(client):
    """vacuum_field must be exactly 4096 floats (16^3 KDE density volume)."""
    resp = client.get("/journey-nexus/frame")
    frame = resp.json()
    assert len(frame["vacuum_field"]) == 4096, (
        f"vacuum_field len={len(frame['vacuum_field'])}, expected 4096"
    )
    assert frame["vacuum_field_shape"] == [16, 16, 16]


def test_viz_frame_has_at_least_one_point(client):
    """Each VizFrame must include at least one VizPoint (the current journey position)."""
    resp = client.get("/journey-nexus/frame")
    points = resp.json()["points"]
    assert len(points) >= 1, "VizFrame.points must be non-empty"


def test_viz_frame_point_winding_number_is_valid(client):
    """VizPoint.winding_number must be one of {-1, 0, +1} (vortex chirality).

    Discriminating: would fail if NPU→0 (correct is +1, CPU→-1, iGPU→0).
    The winding number maps directly to the Hopf fibration fiber orientation.
    """
    resp = client.get("/journey-nexus/frame")
    points = resp.json()["points"]
    valid_winding = {-1, 0, 1}
    for pt in points:
        assert pt["winding_number"] in valid_winding, (
            f"tier={pt['tier_used']} winding={pt['winding_number']}, "
            f"must be in {valid_winding}"
        )
    # NPU must map to +1 (converging, warm chirality)
    npu_pts = [p for p in points if p["tier_used"] == "npu"]
    if npu_pts:
        assert npu_pts[0]["winding_number"] == 1, "NPU tier must have winding_number=+1"


def test_viz_frame_frame_id_is_zero_on_single_call(client):
    """GET /frame always returns frame_id=0 (stateless snapshot endpoint)."""
    resp = client.get("/journey-nexus/frame")
    assert resp.json()["frame_id"] == 0


def test_stream_viz_sse_format(client):
    """GET /stream/viz must return text/event-stream with valid VizFrame JSON.

    Uses max_frames=1 to terminate the stream after one event (avoids
    the infinite-stream issue in TestClient — the generator exits cleanly).
    """
    with client.stream("GET", "/journey-nexus/stream/viz?max_frames=1") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        found = False
        for line in resp.iter_lines():
            if line.startswith("data: "):
                frame = json.loads(line[6:])
                # Must have all top-level VizFrame fields
                assert "frame_id" in frame
                assert "nexus" in frame
                assert "points" in frame
                assert "vacuum_field" in frame
                found = True
        assert found, "No data: line in /stream/viz SSE stream"


def test_stream_viz_first_frame_id_is_zero(client):
    """First frame from /stream/viz must have frame_id=0.

    Discriminating: would fail if frame_id started at 1 or was random.
    Uses max_frames=1 for clean stream termination in tests.
    """
    with client.stream("GET", "/journey-nexus/stream/viz?max_frames=1") as resp:
        for line in resp.iter_lines():
            if line.startswith("data: "):
                frame = json.loads(line[6:])
                assert frame["frame_id"] == 0, (
                    f"First frame_id={frame['frame_id']}, expected 0"
                )
