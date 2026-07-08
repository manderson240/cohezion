"""FastAPI router for the JourneyNexus endpoints.

Implements the Latent Mind Theater VizFrame contract defined by
tests/api/test_journey_nexus_router.py: a `/frame` snapshot endpoint,
`/stream/viz` + `/stream/evo` SSE feeds, quadrature voting, narration,
and the Omni chat tier.

Every VizFrame field is derived from live UniverseStateService simulation
state (real CA + MHD + Chaos + HIHO engines), not synthetic placeholders.
"""

from __future__ import annotations

import asyncio
import json
import math
import time
from typing import Any

import numpy as np
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from cohezion.api.services.journey_nexus import JourneyNexus
from cohezion.api.services.universe import get_universe_service
from cohezion.flume.latent_gravity import LatentGravityNavigator
from cohezion.flume.vacuum_topology import VacuumTopologyClassifier


router = APIRouter(prefix="/journey-nexus")

# Topological winding number per vacuum class (HopfManifold convention:
# +1 = warm/NPU, 0 = neutral/iGPU, -1 = cool/CPU).
_WINDING: dict[str, int] = {"instanton": 1, "trivial": 0, "soliton": -1}
_TIER_BY_WINDING: dict[int, str] = {1: "npu", 0: "igpu", -1: "cpu"}
_HUE_BY_WINDING: dict[int, float] = {1: 0.08, 0: 0.55, -1: 0.67}

_VACUUM_N = 16  # VacuumFog samples a 16^3 Data3DTexture

# Module-level singletons — replaced by monkeypatch in tests.
_nexus_instance: JourneyNexus | None = None
_frame_classifier: VacuumTopologyClassifier | None = None
_detector_instance: Any = None
_gravity_navigator: LatentGravityNavigator | None = None


def _get_gravity() -> LatentGravityNavigator:
    global _gravity_navigator
    if _gravity_navigator is None:
        _gravity_navigator = LatentGravityNavigator()
    return _gravity_navigator


async def _get_nexus() -> JourneyNexus:
    """Return (or lazily create) the JourneyNexus singleton."""
    global _nexus_instance
    if _nexus_instance is None:
        _nexus_instance = JourneyNexus()
    return _nexus_instance


def _get_classifier() -> VacuumTopologyClassifier:
    global _frame_classifier
    if _frame_classifier is None:
        _frame_classifier = VacuumTopologyClassifier()
    return _frame_classifier


def _project_12d_to_3d(vec: np.ndarray) -> tuple[float, float, float]:
    """Project a 12D FLUME latent vector to 3D.

    Same axis grouping LatentParticles uses client-side:
    x = mean(dims 0-2), y = mean(dims 3-5), z = mean(dims 6-11).
    """
    return (
        float(np.mean(vec[0:3])),
        float(np.mean(vec[3:6])),
        float(np.mean(vec[6:12])),
    )


def _hiho_glow(coherence: float) -> float:
    """HIHO proximity: peaks at coherence=0.5, falls to 0 at the extremes."""
    return max(0.0, 1.0 - abs(coherence - 0.5) * 2.0)


def _cache_stats() -> dict[str, Any]:
    """Real SemanticCache stats for this process; empty dict on failure."""
    try:
        from cohezion.cache.semantic_cache import SemanticCache

        return SemanticCache.get_instance().get_stats()
    except (ImportError, AttributeError, RuntimeError, ValueError):
        return {}


def _detector_snapshot() -> dict[str, Any]:
    """Real DegradationDetector snapshot for this process; empty on failure."""
    global _detector_instance
    try:
        from cohezion.compound.degradation_detector import DegradationDetector

        if _detector_instance is None:
            _detector_instance = DegradationDetector()
        return _detector_instance.snapshot()
    except (ImportError, AttributeError, RuntimeError, ValueError):
        return {}


def _build_viz_frame(frame_id: int) -> dict[str, Any]:
    """Assemble a VizFrame from live universe simulation state.

    - ``points``: one VizPoint per EVO. Position is the EVO's evolving 12D
      latent vector projected to 3D; ``winding_number`` comes from
      vacuum-topology classification (instanton=+1, trivial=0, soliton=-1);
      visual attributes map documented physics quantities (charge_density
      -> radius, classification confidence -> saturation/alpha,
      |magnetic_helicity| -> rotation_speed, HIHO proximity -> glow).
    - ``nexus``: the exploitation/exploration quadrature — mean EVO
      coherence (I) vs topological diversity of the latent set (Q);
      ``distance`` is the BKT distance from HIHO equilibrium
      sqrt((I-0.5)^2 + (Q-0.5)^2); ``power`` is HIHO proximity.
    - ``vacuum_field``: 16^3 density volume (x-fastest, Data3DTexture
      order) = CA fabric extruded along z with a Gaussian profile + a
      Gaussian deposit at each EVO's projected position weighted by
      charge density.
    - ``mhd_ripple_phase``: accumulated MHD twist angle — the MHD engine
      applies twist = helicity * dt per step, so phase = mean|helicity| * t.
    - ``cache_stats`` / ``detector_snapshot``: real in-process
      SemanticCache and DegradationDetector observability (fail-open {}).
    """
    svc = get_universe_service()
    clf = _get_classifier()
    # Service-internal read: the 12D latent vectors are not exposed publicly.
    evos = svc._evos
    vectors = svc._vectors
    state = svc.get_state()

    # SWIFT-analog gravity: EVO latent vectors are the N-body mass field
    # (vault: swift-carbonengine-vacuum-analog.md). Each point reports the
    # potential-well depth at its own position.
    gravity = _get_gravity()
    gravity.update_field([np.asarray(v) for v in vectors])

    points: list[dict[str, Any]] = []
    tier_votes: dict[str, int] = {"npu": 0, "igpu": 0, "cpu": 0}
    for evo, vec in zip(evos, vectors, strict=True):
        label = clf.classify(np.asarray(vec))
        winding = _WINDING[label.label]
        tier = _TIER_BY_WINDING[winding]
        tier_votes[tier] += 1
        px, py, pz = _project_12d_to_3d(np.asarray(vec))
        potential, force = gravity.potential_and_force(np.asarray(vec))
        points.append(
            {
                "pos_x": px,
                "pos_y": py,
                "pos_z": pz,
                "color_hue": _HUE_BY_WINDING[winding],
                "color_saturation": 0.5 + 0.5 * label.confidence,
                "luminosity": 0.35 + 0.4 * min(1.0, max(0.0, evo.coherence)),
                "radius": 0.03 + 0.05 * min(2.0, max(0.0, evo.charge_density)) / 2.0,
                "glow": _hiho_glow(evo.coherence),
                "alpha": 0.6 + 0.3 * label.confidence,
                "rotation_speed": abs(evo.magnetic_helicity) * 2.0,
                "coherence": evo.coherence,
                "tier_used": tier,
                "winding_number": winding,
                "potential": potential,
                "force_magnitude": float(np.linalg.norm(force)),
            }
        )

    diversity = clf.topological_diversity([np.asarray(v) for v in vectors])
    mean_coherence = state.coherence
    nexus_i = min(1.0, max(0.0, mean_coherence))
    nexus_q = min(1.0, max(0.0, float(diversity.get("diversity", 0.0))))

    # 16^3 vacuum density: CA fabric extruded along z + EVO charge deposits.
    n = _VACUUM_N
    field = np.zeros((n, n, n), dtype=np.float32)  # indexed [z, y, x]
    ca = np.asarray(state.ca_grid, dtype=np.float32).reshape(n, n)
    z_axis = np.arange(n, dtype=np.float32)
    z_profile = np.exp(-(((z_axis - n / 2.0) / 3.0) ** 2))
    field += ca[None, :, :] * z_profile[:, None, None] * 0.5
    grid_z, grid_y, grid_x = np.meshgrid(z_axis, z_axis, z_axis, indexing="ij")
    for pt, evo in zip(points, evos, strict=True):
        # Map projected position from roughly [-1, 1] into voxel space.
        cx = (max(-1.0, min(1.0, pt["pos_x"])) + 1.0) / 2.0 * (n - 1)
        cy = (max(-1.0, min(1.0, pt["pos_y"])) + 1.0) / 2.0 * (n - 1)
        cz = (max(-1.0, min(1.0, pt["pos_z"])) + 1.0) / 2.0 * (n - 1)
        r2 = (grid_x - cx) ** 2 + (grid_y - cy) ** 2 + (grid_z - cz) ** 2
        amplitude = min(2.0, max(0.0, evo.charge_density)) / 2.0
        field += amplitude * np.exp(-r2 / (2.0 * 2.5**2))
    peak = float(field.max())
    if peak > 1e-6:
        field /= peak

    mean_helicity = float(np.mean([abs(e.magnetic_helicity) for e in evos]))
    mhd_phase = math.fmod(mean_helicity * state.time, 2.0 * math.pi)

    return {
        "frame_id": frame_id,
        "timestamp": time.time(),
        "tick": state.tick,
        "time": state.time,
        "coherence": mean_coherence,
        "tier_used": max(tier_votes, key=lambda k: tier_votes[k]),
        "nexus": {
            "I": nexus_i,
            "Q": nexus_q,
            "distance": math.sqrt((nexus_i - 0.5) ** 2 + (nexus_q - 0.5) ** 2),
            "power": _hiho_glow(mean_coherence),
        },
        "mhd_ripple_phase": mhd_phase,
        "vacuum_field": [float(v) for v in field.ravel()],
        "vacuum_field_shape": [n, n, n],
        "topology_fractions": {
            "instanton": float(diversity.get("instanton", 0.0)),
            "soliton": float(diversity.get("soliton", 0.0)),
            "trivial": float(diversity.get("trivial", 0.0)),
        },
        "gravity": {
            "n_particles": gravity.n_particles,
            "deepest_potential": min((p["potential"] for p in points), default=0.0),
            "mean_potential": (float(np.mean([p["potential"] for p in points])) if points else 0.0),
        },
        "cache_stats": _cache_stats(),
        "detector_snapshot": _detector_snapshot(),
        "points": points,
    }


@router.get("/frame")
async def viz_frame() -> dict[str, Any]:
    """Return a stateless VizFrame snapshot (frame_id is always 0)."""
    return _build_viz_frame(0)


@router.get("/stream/viz")
async def stream_viz(
    max_frames: int | None = Query(default=None, ge=1),
    interval_s: float = Query(default=0.5, ge=0.05, le=10.0),
) -> StreamingResponse:
    """SSE stream of VizFrames; advances the universe one tick per frame."""

    async def _gen():
        frame_id = 0
        svc = get_universe_service()
        while max_frames is None or frame_id < max_frames:
            svc.tick()
            frame = _build_viz_frame(frame_id)
            yield f"data: {json.dumps(frame)}\n\n"
            frame_id += 1
            if max_frames is not None and frame_id >= max_frames:
                break
            await asyncio.sleep(interval_s)

    return StreamingResponse(_gen(), media_type="text/event-stream")


@router.get("/evo/snapshot")
async def evo_snapshot() -> list[dict[str, Any]]:
    """Return the current EVO event stream snapshot."""
    nexus = await _get_nexus()
    events = nexus.stream_snapshot() if hasattr(nexus, "stream_snapshot") else []
    return [e.__dict__ if hasattr(e, "__dict__") else e for e in events]


@router.get("/stream/evo")
async def stream_evo() -> StreamingResponse:
    """SSE stream of EVO events (current snapshot, then the stream closes).

    EventSource clients auto-reconnect, giving poll-like delivery without
    holding a connection open against an empty event queue.
    """
    nexus = await _get_nexus()

    async def _gen():
        events = nexus.stream_snapshot() if hasattr(nexus, "stream_snapshot") else []
        for e in events:
            payload = e.__dict__ if hasattr(e, "__dict__") else e
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream")


@router.get("/quadrature/{journey_id}")
async def quadrature_vote(
    journey_id: str,
    mode: str = Query(default="preflight", pattern="^(preflight|full)$"),
) -> Any:
    """Run a Quadrature Nexus vote on *journey_id*."""
    nexus = await _get_nexus()
    result = await nexus.quadrature(journey_id, mode=mode)  # type: ignore[attr-defined]
    return result


@router.get("/narrate/{journey_id}")
async def narrate(journey_id: str, with_image: bool = False) -> Any:
    """Narrate *journey_id*."""
    nexus = await _get_nexus()
    result = await nexus.narrate(journey_id, with_image=with_image)  # type: ignore[call-arg]
    return result


class OmniChatRequest(BaseModel):
    """Body for the Omni chat endpoint."""

    message: str = Field(min_length=1)


@router.post("/omni/{journey_id}")
async def omni_chat(journey_id: str, body: OmniChatRequest) -> Any:
    """Route a message through the Omni Tier."""
    nexus = await _get_nexus()
    result = await nexus.omni_chat(  # type: ignore[attr-defined]
        journey_id, message=body.message
    )
    return result
