"""Disconnected Modules API — wires 14 codebase modules into the Genesis Engine.

Exposes: Hamiltonian dynamics, manifold utils, spatial phonons, triune manifold,
emergent detector, FLUME morphospace/LCSP, rewards bridge, coherence tracker,
and data endpoints for TensorBeamVisualizer, HIHOBridge, PersistenceDiagram.
"""

from __future__ import annotations

import logging

import numpy as np
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

modules_router = APIRouter(prefix="/modules", tags=["modules"])


# ─── Response Models ───────────────────────────────────────────────


class HamiltonianResponse(BaseModel):
    """Hamiltonian dynamics simulation result."""

    initial_energy: float
    final_energy: float
    final_state: list[float]
    trajectory_length: int
    potential_type: str


class ManifoldLagrangeResponse(BaseModel):
    """Semantic Lagrange point computation result."""

    stable: bool
    mu: float = 0.0
    distance: float = 0.0
    l4_point: list[float] = Field(default_factory=list)
    l5_point: list[float] = Field(default_factory=list)
    barycenter: list[float] = Field(default_factory=list)
    reason: str = ""


class PhononResponse(BaseModel):
    """Spatial phonon evolution result."""

    initial_coherence: float
    final_coherence: float
    steps_evolved: int


class TriuneResponse(BaseModel):
    """Triune manifold HIHO coherence computation."""

    coherence: float
    restoring_force: float
    doer_dim: int
    thinker_dim: int
    knower_dim: int


class EmergenceResponse(BaseModel):
    """Emergent behavior detection summary."""

    run_id: str
    total_cycles: int
    event_count: int
    complexity_score: float
    events: list[dict]


class MorphospaceResponse(BaseModel):
    """Morphospace stability analysis."""

    stability: float
    nearest_well: str
    well_distance: float
    known_wells: list[str]


class LCSPResponse(BaseModel):
    """LCSP prediction result."""

    next_state: list[float]
    confidence: float
    hiho_stability: float


class RewardsResponse(BaseModel):
    """Rewards bridge computation."""

    base_reward: float
    ratchet_penalty: float
    combined_reward: float
    coherence: float
    tokens_used: int


class TensorBeamData(BaseModel):
    """Data for the TensorBeamVisualizer component."""

    axes: list[str]
    values: list[float]
    hiho_target: list[float]
    deviations: list[float]


class HIHOBridgeData(BaseModel):
    """Data for the HIHOBridge component."""

    coherence: float
    stability_score: float
    restoring_force: float
    is_stable: bool
    reward: float


class PersistenceData(BaseModel):
    """Data for the PersistenceDiagram component."""

    h0_pairs: list[list[float]]
    h1_pairs: list[list[float]]
    persistence_entropy: float
    total_features: int


# ─── Request Models ────────────────────────────────────────────────


class LagrangeRequest(BaseModel):
    """Request for Lagrange point computation."""

    topic_a: list[float] = Field(default_factory=lambda: [0.5] * 12)
    topic_b: list[float] = Field(default_factory=lambda: [0.8] * 12)
    weight_a: float = 1.0
    weight_b: float = 0.5


class StateRequest(BaseModel):
    """Request with a 12D state vector."""

    state: list[float] = Field(default_factory=lambda: [0.5] * 12)


# ─── Endpoints ─────────────────────────────────────────────────────


@modules_router.post("/hamiltonian/simulate", response_model=HamiltonianResponse)
async def simulate_hamiltonian(
    potential: str = Query(
        "double_well", description="Potential type: double_well, harmonic, hiho_well"
    ),
    epochs: int = Query(50, ge=1, le=500),
    temperature: float = Query(0.01, ge=0.0, le=1.0),
    n_agents: int = Query(4, ge=1, le=32),
    z_dim: int = Query(12, ge=2, le=256),
) -> HamiltonianResponse:
    """Simulate Hamiltonian dynamics on a potential energy surface.

    Runs overdamped Langevin dynamics on the specified potential,
    returning initial/final energies and the final state.
    """
    from cohezion.physics.hamiltonian import HamiltonianDynamics, PotentialType

    pot_map = {
        "double_well": PotentialType.DOUBLE_WELL,
        "harmonic": PotentialType.HARMONIC,
        "hiho_well": PotentialType.HIHO_WELL,
    }
    pot_type = pot_map.get(potential, PotentialType.DOUBLE_WELL)

    dynamics = HamiltonianDynamics(potential=pot_type, temperature=temperature)
    z0 = np.full((n_agents, z_dim), 0.5, dtype=np.float32)
    z0 += np.random.default_rng(42).normal(0, 0.1, z0.shape).astype(np.float32)

    initial_energy = float(np.mean(dynamics.energy(z0)))
    z_final = dynamics.simulate(z0, epochs=epochs, seed=42)
    final_energy = float(np.mean(dynamics.energy(z_final)))

    return HamiltonianResponse(
        initial_energy=initial_energy,
        final_energy=final_energy,
        final_state=z_final[0].tolist(),
        trajectory_length=epochs,
        potential_type=potential,
    )


@modules_router.post("/manifold/lagrange-points", response_model=ManifoldLagrangeResponse)
async def compute_lagrange_points(req: LagrangeRequest) -> ManifoldLagrangeResponse:
    """Find Semantic Lagrange Points (L4/L5) between two 12D topics.

    Uses the Restricted Three-Body Problem analogy to find stable
    equilibrium points in the semantic manifold.
    """
    from cohezion.physics.manifold_utils import SemanticLagrangeFinder

    finder = SemanticLagrangeFinder()
    a = np.array(req.topic_a[:12], dtype=float)
    b = np.array(req.topic_b[:12], dtype=float)
    result = finder.find_triangular_points(a, b, req.weight_a, req.weight_b)

    return ManifoldLagrangeResponse(**result)


@modules_router.post("/phonons/evolve", response_model=PhononResponse)
async def evolve_phonons(
    steps: int = Query(10, ge=1, le=100),
    viscosity: float = Query(0.05, ge=0.0, le=1.0),
    phonon_coupling: float = Query(0.12, ge=0.0, le=1.0),
) -> PhononResponse:
    """Evolve spatial phonon dynamics on the 12D manifold.

    Simulates viscous dark energy expansion using the phonon model
    from [2512.00056], starting from the current cosmogony state.
    """
    from cohezion.universe.engine import AxiomaticState
    from cohezion.universe.spatial_phonons import PhononParameters, SpatialPhononsEngine

    params = PhononParameters(viscosity_alpha=viscosity, phonon_coupling=phonon_coupling)
    engine = SpatialPhononsEngine(params=params)

    state = AxiomaticState()
    initial_coh = state.spin_coherence

    for _ in range(steps):
        state = engine.evolve_state(state, delta_t=0.1)

    return PhononResponse(
        initial_coherence=initial_coh,
        final_coherence=state.spin_coherence,
        steps_evolved=steps,
    )


@modules_router.get("/triune/coherence", response_model=TriuneResponse)
async def get_triune_coherence() -> TriuneResponse:
    """Compute Triune manifold HIHO coherence.

    Uses the Doer(12D)/Thinker(512D)/Knower(2048D) manifold structure
    from Percival's Triune Self model. Returns coherence between
    doer intent and a reference environment vector.
    """
    import torch

    from cohezion.universe.triune_manifold import (
        calculate_hiho_coherence,
        compute_restoring_force,
    )

    doer = torch.randn(12) * 0.5
    thinker = torch.randn(512) * 0.3
    knower = torch.randn(2048) * 0.1
    environment = torch.randn(12) * 0.5

    coherence = calculate_hiho_coherence(doer, environment)
    restoring = compute_restoring_force(coherence)

    return TriuneResponse(
        coherence=coherence,
        restoring_force=restoring,
        doer_dim=12,
        thinker_dim=512,
        knower_dim=2048,
    )


@modules_router.post("/emergence/detect", response_model=EmergenceResponse)
async def detect_emergence(
    n_agents: int = Query(10, ge=2, le=50),
    n_cycles: int = Query(50, ge=20, le=200),
    seed: int = Query(42),
) -> EmergenceResponse:
    """Run emergent behavior detection on synthetic agent data.

    Generates simulated coherence histories and z-vectors, then runs
    the full EmergentDetector pipeline: phase transitions, swarm
    coherence, novelty exploration, and complexity scoring.
    """
    from cohezion.simulation.emergent_detector import EmergentDetector

    rng = np.random.default_rng(seed)
    z_dim = 16

    coherence_history = 0.5 + 0.1 * rng.standard_normal((n_cycles, n_agents))
    coherence_history = np.clip(coherence_history, 0.0, 1.0)

    z_vectors = rng.standard_normal((n_cycles, n_agents, z_dim)).astype(np.float32)
    # Inject a phase transition at cycle n_cycles//2
    mid = n_cycles // 2
    z_vectors[mid:] += 0.5
    coherence_history[mid:] += 0.2
    coherence_history = np.clip(coherence_history, 0.0, 1.0)

    detector = EmergentDetector()
    agent_ids = [f"evo_{i}" for i in range(n_agents)]
    report = detector.analyze(
        coherence_history=coherence_history,
        z_vectors=z_vectors,
        agent_ids=agent_ids,
        run_id=f"genesis_sim_{seed}",
    )

    events = [
        {
            "type": e.event_type,
            "cycle": e.cycle,
            "magnitude": e.magnitude,
            "description": e.description,
        }
        for e in report.events[:20]
    ]

    return EmergenceResponse(
        run_id=report.run_id,
        total_cycles=report.total_cycles,
        event_count=report.event_count,
        complexity_score=report.complexity_score,
        events=events,
    )


@modules_router.post("/morphospace/analyze", response_model=MorphospaceResponse)
async def analyze_morphospace(req: StateRequest) -> MorphospaceResponse:
    """Analyze a 12D state in the FLUME morphospace.

    Returns stability score, nearest stability well, and distance.
    Uses LCSP predictor under the hood for HIHO stability calculations.
    """
    from cohezion.flume.morphospace import MorphospaceMapper

    mapper = MorphospaceMapper()
    s = np.array(req.state[:12], dtype=float)
    stability = mapper.compute_stability(s)
    nearest = mapper.find_nearest_well(s)

    well_name = nearest.name if nearest else "none"
    well_dist = float(np.linalg.norm(s - nearest.center)) if nearest else 0.0

    return MorphospaceResponse(
        stability=stability,
        nearest_well=well_name,
        well_distance=well_dist,
        known_wells=[w.name for w in mapper.known_wells],
    )


@modules_router.post("/lcsp/predict", response_model=LCSPResponse)
async def predict_lcsp(req: StateRequest) -> LCSPResponse:
    """Predict next 12D state using LCSP (Lattice-Coupled State Projection).

    Encodes the current state into 256D latent space, predicts the next
    latent state with HIHO stability constraints, and decodes back to 12D.
    """
    from cohezion.flume.lcsp import LCSPPredictor

    predictor = LCSPPredictor()
    s = np.array(req.state[:12], dtype=float)
    prediction = predictor.predict(s)

    return LCSPResponse(
        next_state=prediction.next_state.tolist(),
        confidence=prediction.confidence,
        hiho_stability=prediction.hiho_stability,
    )


@modules_router.get("/rewards/compute", response_model=RewardsResponse)
async def compute_rewards(
    coherence: float = Query(0.5, ge=0.0, le=1.0),
    tokens_used: int = Query(0, ge=0),
) -> RewardsResponse:
    """Compute reward signal using the RewardsBridge.

    Combines the Gaussian HIHO reward (peaked at coherence=0.5) with
    a coherence ratchet that penalizes backsliding.
    """
    from cohezion.physics.rewards_bridge import RewardsBridge

    bridge = RewardsBridge()
    base = bridge.calculator.calculate_score(coherence, tokens_used)
    ratchet_pen = bridge.ratchet.check(coherence)
    combined = bridge.compute(coherence, tokens_used)

    return RewardsResponse(
        base_reward=base,
        ratchet_penalty=ratchet_pen,
        combined_reward=combined,
        coherence=coherence,
        tokens_used=tokens_used,
    )


# ─── Genesis Tab Data Endpoints ────────────────────────────────────


@modules_router.get("/tensor-beam", response_model=TensorBeamData)
async def get_tensor_beam_data() -> TensorBeamData:
    """Data for the TensorBeamVisualizer — 12D axiomatic state as tensor beams.

    Returns the current cosmogony 12D state with per-axis deviations
    from the HIHO target (0.5).
    """
    from cohezion.physics.cosmogony import get_cosmogony

    cosmo = get_cosmogony()
    state = cosmo.generate_12d_state()

    axes = [
        "Awareness",
        "Logic",
        "Ontology",
        "Perception",
        "Emotion",
        "Novelty",
        "Physics",
        "Chemistry",
        "Biology",
        "Temporal",
        "Precipitation",
        "SpinCoherence",
    ]
    values = state.tolist()
    hiho = [0.5] * 12
    deviations = [abs(v - 0.5) for v in values]

    return TensorBeamData(
        axes=axes,
        values=values,
        hiho_target=hiho,
        deviations=deviations,
    )


@modules_router.get("/hiho-bridge", response_model=HIHOBridgeData)
async def get_hiho_bridge_data(
    coherence: float = Query(0.5, ge=0.0, le=1.0),
) -> HIHOBridgeData:
    """Data for the HIHOBridge component — coherence stability dashboard.

    Computes restoring force, stability score, and reward at the
    given coherence level.
    """
    from cohezion.physics.rewards_bridge import RewardsBridge
    from cohezion.universe.triune_manifold import compute_restoring_force

    restoring = compute_restoring_force(coherence)
    stability = max(0.0, 1.0 - abs(coherence - 0.5) * 2.0)
    is_stable = 0.4 <= coherence <= 0.6

    bridge = RewardsBridge()
    reward = bridge.compute(coherence)

    return HIHOBridgeData(
        coherence=coherence,
        stability_score=stability,
        restoring_force=restoring,
        is_stable=is_stable,
        reward=reward,
    )


@modules_router.get("/persistence-diagram", response_model=PersistenceData)
async def get_persistence_diagram(
    n_points: int = Query(30, ge=10, le=100),
    seed: int = Query(42),
) -> PersistenceData:
    """Data for the PersistenceDiagram component — topological features of trajectories.

    Generates a synthetic agent trajectory and computes persistent homology
    (H0 connected components, H1 loops) using the Vietoris-Rips filtration.
    """
    from cohezion.compound.topological_persistence import TopologicalPersistence

    rng = np.random.default_rng(seed)
    trajectory = np.cumsum(rng.standard_normal((n_points, 8)) * 0.1, axis=0)

    analyzer = TopologicalPersistence()
    diagram = analyzer.compute_persistence(trajectory)

    h0_pairs = [
        [p.birth, p.death if not np.isinf(p.death) else -1.0]
        for p in diagram.pairs
        if p.dimension == 0
    ]
    h1_pairs = [
        [p.birth, p.death if not np.isinf(p.death) else -1.0]
        for p in diagram.pairs
        if p.dimension == 1
    ]

    return PersistenceData(
        h0_pairs=h0_pairs,
        h1_pairs=h1_pairs,
        persistence_entropy=diagram.persistence_entropy(),
        total_features=len(diagram.pairs),
    )


__all__ = ["modules_router"]
