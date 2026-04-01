"""Extended Physics API — exposes bioelectric, natural-capital, and cosmogony chain.

Wires disconnected physics modules into the Genesis Engine API layer.
Follows the router pattern established in genesis.py.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)

physics_ext_router = APIRouter(prefix="/physics", tags=["physics-extended"])


# ─── Response Models ───────────────────────────────────────────────


class BioelectricResponse(BaseModel):
    """State snapshot of the BioelectricNetwork."""

    n_cells: int
    v_mem: list[float]
    coherence: float
    hiho_deviation: float
    information_capacity_bits: float
    cognitive_light_cone: dict
    percolation: dict


class NaturalCapitalResponse(BaseModel):
    """Ecosystem service metrics for the current manifold state."""

    habitat_quality: float
    carbon_storage: float
    water_yield: float
    pollination: float
    sediment_retention: float
    total_natural_capital: float
    seventh_generation: dict


class CosmogonyChainResponse(BaseModel):
    """Full 10-step cosmogony chain status."""

    temperature: float
    symmetry: str
    stage: int
    total_steps: int = Field(default=10)
    transitions_completed: int
    transitions: list[dict]
    order_parameters: dict[str, float]
    fisher_eigenvalue_max: float
    landau_free_energy: float


class HamiltonianSimulateResponse(BaseModel):
    """Result of a Hamiltonian dynamics trajectory."""

    potential: str
    epochs: int
    dt: float
    temperature: float
    initial_energy: float
    final_energy: float
    final_state_mean: float
    final_state_std: float
    trajectory_checkpoints: int


class TriuneStateResponse(BaseModel):
    """Current Triune manifold state (Doer/Thinker/Knower)."""

    doer: list[float] = Field(description="12D observable state")
    thinker: list[float] = Field(description="512D reasoning space")
    knower: list[float] = Field(description="2048D semantic intent")
    hiho_coherence: float
    restoring_force: float


class PhononStateResponse(BaseModel):
    """Spatial phonon dynamics snapshot."""

    expansion_rate: float
    viscous_drag: float
    coherence_gain: float
    state_before: dict[str, float]
    state_after: dict[str, float]


class StabilityWellResponse(BaseModel):
    """A stability well in the 12D morphospace."""

    name: str
    center: list[float]
    radius: float
    depth: float


class MorphospaceWellsResponse(BaseModel):
    """All known stability wells in the morphospace."""

    wells: list[StabilityWellResponse]
    count: int


class LCSPPredictResponse(BaseModel):
    """Result of an LCSP state prediction."""

    input_state: list[float]
    next_state: list[float]
    actions: list[float]
    confidence: float
    hiho_stability: float


class EmergenceDetectResponse(BaseModel):
    """Result of emergence detection on synthetic trajectory data."""

    run_id: str
    total_cycles: int
    event_count: int
    complexity_score: float
    events: list[dict]


# ─── Endpoints ─────────────────────────────────────────────────────


@physics_ext_router.get("/bioelectric", response_model=BioelectricResponse)
async def get_bioelectric_state(
    n_cells: int = 16,
    conductance: float = 0.3,
) -> BioelectricResponse:
    """Return BioelectricNetwork state — Levin-inspired collective intelligence.

    Creates a network with ``n_cells`` cells coupled at ``conductance``,
    runs 100 timesteps, and returns the resulting state including
    coherence, cognitive light cone, and percolation analysis.
    """
    from cohezion.physics.bioelectric_model import BioelectricNetwork

    net = BioelectricNetwork(n_cells=min(max(n_cells, 2), 128))
    net.set_uniform_conductance(max(0.0, min(conductance, 5.0)))
    net.simulate(n_steps=100, dt=0.01)

    data = net.to_dict()
    return BioelectricResponse(**data)


@physics_ext_router.get("/natural-capital", response_model=NaturalCapitalResponse)
async def get_natural_capital(
    coherence: float = 0.5,
    connectivity: float = 0.5,
    gauge_curvature: float = 0.0,
    spore_density: float = 0.0,
) -> NaturalCapitalResponse:
    """Return NaturalCapitalValuation metrics — InVEST-inspired ecosystem services.

    Evaluates habitat quality, carbon storage, water yield, pollination,
    and sediment retention for the given manifold parameters.  Includes
    a Seventh Generation sustainability projection.
    """

    from cohezion.physics.cosmogony import get_cosmogony
    from cohezion.physics.natural_capital import NaturalCapitalValuation

    cosmo = get_cosmogony()
    state_12d = cosmo.generate_12d_state()

    valuation = NaturalCapitalValuation()
    metrics = valuation.evaluate(
        state_12d=state_12d,
        coherence=max(0.0, min(coherence, 1.0)),
        connectivity=max(0.0, min(connectivity, 1.0)),
        gauge_curvature=max(0.0, gauge_curvature),
        spore_density=max(0.0, spore_density),
    )

    projection = valuation.seventh_generation_projection(metrics.total_natural_capital)

    return NaturalCapitalResponse(
        **metrics.to_dict(),
        seventh_generation=projection.to_dict(),
    )


@physics_ext_router.get("/cosmogony/full-chain", response_model=CosmogonyChainResponse)
async def get_cosmogony_full_chain() -> CosmogonyChainResponse:
    """Return the complete 10-step cosmogony chain status.

    Shows the current symmetry stage, all completed transitions,
    order parameters, Fisher eigenvalue, and Landau free energy.
    The 10 steps run from Void to Reality Precipitates.
    """
    from cohezion.physics.cosmogony import get_cosmogony

    cosmo = get_cosmogony()
    state = cosmo.state
    data = state.to_dict()

    return CosmogonyChainResponse(
        temperature=data["temperature"],
        symmetry=data["symmetry"],
        stage=data["stage"],
        total_steps=10,
        transitions_completed=len(data["transitions"]),
        transitions=data["transitions"],
        order_parameters=data["order_parameters"],
        fisher_eigenvalue_max=data["fisher_eigenvalue_max"],
        landau_free_energy=data["landau_free_energy"],
    )


@physics_ext_router.get("/hamiltonian/simulate", response_model=HamiltonianSimulateResponse)
async def get_hamiltonian_simulate(
    potential: str = "double_well",
    epochs: int = 50,
    n_agents: int = 4,
    z_dim: int = 8,
    dt: float = 0.01,
    temperature: float = 0.01,
    seed: int = 42,
) -> HamiltonianSimulateResponse:
    """Run a short Hamiltonian trajectory on a configurable potential surface.

    Simulates overdamped Langevin dynamics for ``n_agents`` in a
    ``z_dim``-dimensional latent space.  Returns energy statistics
    and trajectory checkpoint count.
    """
    import numpy as np

    from cohezion.physics.hamiltonian import HamiltonianDynamics, PotentialType

    pot_map = {p.value: p for p in PotentialType}
    pot_type = pot_map.get(potential, PotentialType.DOUBLE_WELL)

    dynamics = HamiltonianDynamics(
        potential=pot_type,
        dt=max(0.001, min(dt, 0.1)),
        temperature=max(0.0, min(temperature, 1.0)),
    )

    safe_epochs = max(1, min(epochs, 500))
    safe_agents = max(1, min(n_agents, 32))
    safe_dim = max(1, min(z_dim, 64))

    rng = np.random.default_rng(seed)
    z0 = rng.normal(0.5, 0.1, (safe_agents, safe_dim)).astype(np.float32)

    initial_energy = float(np.mean(dynamics.energy(z0)))
    trajectory = dynamics.simulate_with_trajectory(
        z0, safe_epochs, checkpoint_interval=max(1, safe_epochs // 10), seed=seed
    )
    z_final = trajectory[-1][1]
    final_energy = float(np.mean(dynamics.energy(z_final)))

    return HamiltonianSimulateResponse(
        potential=pot_type.value,
        epochs=safe_epochs,
        dt=dynamics.dt,
        temperature=dynamics.temperature,
        initial_energy=initial_energy,
        final_energy=final_energy,
        final_state_mean=float(np.mean(z_final)),
        final_state_std=float(np.std(z_final)),
        trajectory_checkpoints=len(trajectory),
    )


@physics_ext_router.get("/triune/state", response_model=TriuneStateResponse)
async def get_triune_state() -> TriuneStateResponse:
    """Return current Triune manifold state (Doer 12D / Thinker 512D / Knower 2048D).

    Creates a default Triune state at the HIHO stability point and
    computes coherence between the Thinker and Knower layers.
    """
    import torch

    from cohezion.universe.triune_manifold import (
        TriuneState,
        calculate_hiho_coherence,
        compute_restoring_force,
    )

    state = TriuneState(
        doer=torch.full((12,), 0.5),
        thinker=torch.randn(512) * 0.1 + 0.5,
        knower=torch.randn(2048) * 0.1 + 0.5,
    )

    coherence = calculate_hiho_coherence(state.thinker, state.knower[:512])
    force = compute_restoring_force(coherence)

    return TriuneStateResponse(
        doer=state.doer.tolist(),
        thinker=state.thinker.tolist(),
        knower=state.knower.tolist(),
        hiho_coherence=coherence,
        restoring_force=force,
    )


@physics_ext_router.get("/phonons/state", response_model=PhononStateResponse)
async def get_phonon_state(
    viscosity: float = 0.05,
    coupling: float = 0.12,
    delta_t: float = 0.1,
) -> PhononStateResponse:
    """Return spatial phonon dynamics — viscous dark energy model.

    Evolves a default 12D AxiomaticState by one timestep using the
    SpatialPhononsEngine and returns expansion/drag/coherence metrics.
    """
    from cohezion.universe.engine import AxiomaticState
    from cohezion.universe.spatial_phonons import PhononParameters, SpatialPhononsEngine

    params = PhononParameters(
        viscosity_alpha=max(0.0, min(viscosity, 1.0)),
        phonon_coupling=max(0.0, min(coupling, 1.0)),
    )
    engine = SpatialPhononsEngine(params=params)
    state = AxiomaticState()

    before = {
        "spatial_x": state.spatial_x,
        "spatial_y": state.spatial_y,
        "spatial_z": state.spatial_z,
        "temporal": state.temporal,
        "physics": state.physics,
    }

    safe_dt = max(0.01, min(delta_t, 1.0))
    new_state = engine.evolve_state(state, delta_t=safe_dt)

    viscous_drag = params.viscosity_alpha * (state.physics - params.hiho_threshold)
    expansion_rate = params.dark_energy_density - viscous_drag
    coherence_gain = engine.calculate_coherence_gain(state)

    after = {
        "spatial_x": new_state.spatial_x,
        "spatial_y": new_state.spatial_y,
        "spatial_z": new_state.spatial_z,
        "temporal": new_state.temporal,
        "physics": new_state.physics,
    }

    return PhononStateResponse(
        expansion_rate=expansion_rate,
        viscous_drag=viscous_drag,
        coherence_gain=coherence_gain,
        state_before=before,
        state_after=after,
    )


# ─── Morphospace Wiring ───────────────────────────────────────────


@physics_ext_router.get("/morphospace/wells", response_model=MorphospaceWellsResponse)
async def get_morphospace_wells() -> MorphospaceWellsResponse:
    """Return known stability wells in the 12D morphospace.

    Initializes a MorphospaceMapper and returns its pre-computed
    stability wells (HIHO_Origin and Pure_Awareness by default).
    """
    try:
        from cohezion.flume.morphospace import MorphospaceMapper
    except Exception as exc:
        logger.warning("morphospace module not available: %s", exc)
        return MorphospaceWellsResponse(wells=[], count=0)

    mapper = MorphospaceMapper()
    wells = [
        StabilityWellResponse(
            name=w.name,
            center=w.center.tolist(),
            radius=w.radius,
            depth=w.depth,
        )
        for w in mapper.known_wells
    ]
    return MorphospaceWellsResponse(wells=wells, count=len(wells))


# ─── LCSP Wiring ─────────────────────────────────────────────────


@physics_ext_router.get("/lcsp/predict", response_model=LCSPPredictResponse)
async def get_lcsp_predict(
    state: str = "0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5",
) -> LCSPPredictResponse:
    """Predict the next 12D state from a current state using LCSP.

    Accepts a comma-separated 12D state vector as query parameter.
    Defaults to the HIHO equilibrium point (all 0.5).
    """
    import numpy as np

    try:
        from cohezion.flume.lcsp import LCSPPredictor
    except Exception as exc:
        logger.warning("lcsp module not available: %s", exc)
        return LCSPPredictResponse(
            input_state=[0.0] * 12,
            next_state=[0.0] * 12,
            actions=[0.0] * 12,
            confidence=0.0,
            hiho_stability=0.0,
        )

    values = [float(v.strip()) for v in state.split(",")]
    if len(values) != 12:
        values = [0.5] * 12
    state_arr = np.array(values, dtype=np.float64)

    predictor = LCSPPredictor()
    prediction = predictor.predict(state_arr)

    return LCSPPredictResponse(
        input_state=state_arr.tolist(),
        next_state=prediction.next_state.tolist(),
        actions=prediction.actions,
        confidence=prediction.confidence,
        hiho_stability=prediction.hiho_stability,
    )


# ─── Emergent Detector Wiring ────────────────────────────────────


@physics_ext_router.get("/emergence/detect", response_model=EmergenceDetectResponse)
async def get_emergence_detect(
    n_agents: int = 8,
    n_cycles: int = 100,
    z_dim: int = 12,
    seed: int = 42,
) -> EmergenceDetectResponse:
    """Detect emergent phenomena in synthetic trajectory data.

    Generates a synthetic multi-agent simulation with ``n_agents``
    agents over ``n_cycles`` cycles, then runs all emergence
    detection methods (phase transitions, swarm coherence, novelty).
    """
    import numpy as np

    try:
        from cohezion.simulation.emergent_detector import EmergentDetector
    except Exception as exc:
        logger.warning("emergent_detector module not available: %s", exc)
        return EmergenceDetectResponse(
            run_id="unavailable",
            total_cycles=0,
            event_count=0,
            complexity_score=0.0,
            events=[],
        )

    safe_agents = max(2, min(n_agents, 64))
    safe_cycles = max(20, min(n_cycles, 1000))
    safe_dim = max(2, min(z_dim, 64))

    rng = np.random.default_rng(seed)

    # Generate synthetic coherence history (T, N)
    coherence = rng.random((safe_cycles, safe_agents)) * 0.5 + 0.25

    # Generate synthetic z-vectors (T, N, D) with a phase transition
    z_vectors = rng.normal(0.0, 0.3, (safe_cycles, safe_agents, safe_dim))
    # Inject a coherence shift midway to trigger phase detection
    midpoint = safe_cycles // 2
    z_vectors[midpoint:] += 0.5

    detector = EmergentDetector()
    agent_ids = [f"agent_{i}" for i in range(safe_agents)]
    report = detector.analyze(
        coherence_history=coherence,
        z_vectors=z_vectors,
        agent_ids=agent_ids,
        run_id=f"synthetic-{seed}",
    )

    events_dicts = [
        {
            "event_type": e.event_type,
            "cycle": e.cycle,
            "magnitude": e.magnitude,
            "description": e.description,
        }
        for e in report.events[:50]
    ]

    return EmergenceDetectResponse(
        run_id=report.run_id,
        total_cycles=report.total_cycles,
        event_count=report.event_count,
        complexity_score=report.complexity_score,
        events=events_dicts,
    )


__all__ = ["physics_ext_router"]
