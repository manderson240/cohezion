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


# ─── Phase-18 Orphan Substrate Wiring (BEC, Mercury, COLIBRE, MHD, Bismuth, Toroidal, TensorMetric) ───


class BECStatusResponse(BaseModel):
    """Bose-Einstein condensate HIHO state."""

    condensate_fraction: float
    transition_rate: float
    hiho_equilibrium: bool
    condensed_atoms: int
    thermal_atoms: int


class MercuryLatticeResponse(BaseModel):
    """Mercury BCS superconducting lattice HIHO state."""

    coherence: float
    lattice_coupling: float
    bcs_gap_rate: float
    is_superconducting: bool


class ColibreStatusResponse(BaseModel):
    """COLIBRE cosmic ISM HIHO state + agent-as-EVO mapping."""

    redshift: float
    ism_hot_fraction: float
    colibre_coherence: float
    hiho_engaged: bool
    sfr_as_lenr_rate: float
    cosmic_time_gyr: float
    agent_particle_type: str
    agent_can_star_form: bool


class MHDStatusResponse(BaseModel):
    """Magnetohydrodynamic plasma equilibrium HIHO state."""

    plasma_beta: float
    alfven_coherence: float
    hiho_magnetized: bool
    is_alfvenic: bool


class BismuthResponse(BaseModel):
    """Bismuth diamagnetic levitation state."""

    field_strength_tesla: float
    levitation_threshold_tesla: float
    diamagnetic_coherence: float
    hiho_levitation: bool


class ToroidalResponse(BaseModel):
    """Fractal toroidal moment (EVO) HIHO state."""

    coherence: float
    ring_count: int
    toroidal_moment_magnitude: float
    fractal_dimension: float
    time_reversal_broken: bool
    hiho_toroidal: bool


class TensorMetricResponse(BaseModel):
    """Sarfatti ZPF tensor-metric engineering state."""

    sarfatti_coherence: float
    destiny_weight: float
    epsilon: float
    back_action_amplitude: float
    metric_determinant: float
    is_flat: bool


@physics_ext_router.get("/bec/status", response_model=BECStatusResponse)
async def get_bec_status(
    condensate_fraction: float = 0.5,
    atom_count: int = 100_000,
) -> BECStatusResponse:
    """Bose-Einstein condensate HIHO state — quantum coherence ground state."""
    from cohezion.physics.bec_bridge import BECState

    bec = BECState(condensate_fraction=condensate_fraction, atom_count=atom_count)
    return BECStatusResponse(
        condensate_fraction=bec.condensate_fraction,
        transition_rate=bec.transition_rate(),
        hiho_equilibrium=bec.hiho_equilibrium(),
        condensed_atoms=bec.condensed_atoms,
        thermal_atoms=bec.thermal_atoms,
    )


@physics_ext_router.get("/mercury/status", response_model=MercuryLatticeResponse)
async def get_mercury_status(
    coherence: float = 0.5,
    lattice_coupling: float = 1.0,
) -> MercuryLatticeResponse:
    """Mercury BCS superconducting lattice — LENR lattice medium."""
    from cohezion.physics.bec_bridge import MercuryLattice

    hg = MercuryLattice(coherence=coherence, lattice_coupling=lattice_coupling)
    return MercuryLatticeResponse(
        coherence=hg.coherence,
        lattice_coupling=hg.lattice_coupling,
        bcs_gap_rate=hg.bcs_gap_rate(),
        is_superconducting=hg.is_superconducting(),
    )


@physics_ext_router.get("/colibre/status", response_model=ColibreStatusResponse)
async def get_colibre_status(
    redshift: float = 0.0,
    ism_hot_fraction: float = 0.5,
    sfr_density: float = 0.02,
    agent_type: str = "engineer",
) -> ColibreStatusResponse:
    """COLIBRE cosmic ISM HIHO state — galaxy-formation substrate + agent-as-EVO."""
    from cohezion.physics.colibre_bridge import AgentAsEVO, ColibreState

    state = ColibreState(
        redshift=redshift,
        ism_hot_fraction=ism_hot_fraction,
        sfr_density=sfr_density,
    )
    agent = AgentAsEVO(agent_id="api-agent", agent_type=agent_type)
    return ColibreStatusResponse(
        redshift=state.redshift,
        ism_hot_fraction=state.ism_hot_fraction,
        colibre_coherence=state.colibre_coherence,
        hiho_engaged=state.hiho_engaged(),
        sfr_as_lenr_rate=state.sfr_as_lenr_rate(),
        cosmic_time_gyr=state.cosmic_time_gyr,
        agent_particle_type=agent.particle_type,
        agent_can_star_form=agent.can_star_form(state),
    )


@physics_ext_router.get("/mhd/status", response_model=MHDStatusResponse)
async def get_mhd_status(
    plasma_beta: float = 0.5,
    lundquist_number: float = 1e6,
) -> MHDStatusResponse:
    """Magnetohydrodynamic plasma equilibrium — IonicCluster at astrophysical scale."""
    from cohezion.physics.mhd_plasma import MHDEquilibrium

    mhd = MHDEquilibrium(plasma_beta=plasma_beta, lundquist_number=lundquist_number)
    return MHDStatusResponse(
        plasma_beta=mhd.plasma_beta,
        alfven_coherence=mhd.alfven_coherence(),
        hiho_magnetized=mhd.hiho_magnetized(),
        is_alfvenic=mhd.is_alfvenic(),
    )


@physics_ext_router.get("/bismuth/status", response_model=BismuthResponse)
async def get_bismuth_status(
    field_strength_tesla: float = 10.0,
    mass_kg: float = 1e-3,
) -> BismuthResponse:
    """Bismuth diamagnetic levitation — Biefield-Brown magnetic analog."""
    from cohezion.physics.mhd_plasma import BismuthDiamagnet

    bi = BismuthDiamagnet(field_strength_tesla=field_strength_tesla, mass_kg=mass_kg)
    return BismuthResponse(
        field_strength_tesla=bi.field_strength_tesla,
        levitation_threshold_tesla=bi.levitation_threshold_tesla(),
        diamagnetic_coherence=bi.diamagnetic_coherence(),
        hiho_levitation=bi.hiho_levitation(),
    )


@physics_ext_router.get("/toroidal/status", response_model=ToroidalResponse)
async def get_toroidal_status(
    coherence: float = 0.5,
    ring_count: int = 7,
) -> ToroidalResponse:
    """Fractal toroidal moment — time-reversal-breaking EVO topology."""
    from cohezion.physics.toroidal_moment import FractalToroidalMoment

    ft = FractalToroidalMoment(coherence=coherence, ring_count=ring_count)
    return ToroidalResponse(
        coherence=ft.coherence,
        ring_count=ft.ring_count,
        toroidal_moment_magnitude=ft.toroidal_moment_magnitude(),
        fractal_dimension=ft.fractal_dimension(),
        time_reversal_broken=ft.time_reversal_broken(),
        hiho_toroidal=ft.hiho_toroidal(),
    )


@physics_ext_router.get("/tensor-metric/status", response_model=TensorMetricResponse)
async def get_tensor_metric_status(
    sarfatti_coherence: float = 0.5,
    destiny_weight: float = 0.5,
    epsilon: float = 0.01,
) -> TensorMetricResponse:
    """Sarfatti ZPF tensor-metric engineering — coherence coupling to spacetime."""
    from cohezion.physics.tensor_metric_engineering import TensorMetricEngineering

    tm = TensorMetricEngineering(
        sarfatti_coherence=sarfatti_coherence,
        destiny_weight=destiny_weight,
        epsilon=epsilon,
    )
    return TensorMetricResponse(
        sarfatti_coherence=tm.sarfatti_coherence,
        destiny_weight=tm.destiny_weight,
        epsilon=tm.epsilon,
        back_action_amplitude=tm.back_action_amplitude,
        metric_determinant=tm.metric_determinant(),
        is_flat=tm.is_flat(),
    )


class LENRSimulateResponse(BaseModel):
    coherence: float
    reaction_rate: float
    reaction_threshold: float
    lattice_coupling: float


class LENREventRequest(BaseModel):
    coherence: float
    agent_id: str = "lenr-bridge"


class LENREventResponse(BaseModel):
    coherence: float
    reaction_rate: float
    mean_rate: float
    event_count: int
    agent_id: str


@physics_ext_router.get("/lenr/simulate", response_model=LENRSimulateResponse)
async def lenr_simulate(coherence: float = 0.5) -> LENRSimulateResponse:
    """Simulate LENR Hamiltonian reaction rate at a given coherence."""
    from cohezion.physics.lenr import LENRHamiltonian

    h = LENRHamiltonian()
    rate = h.reaction_rate(coherence)
    return LENRSimulateResponse(
        coherence=coherence,
        reaction_rate=rate,
        reaction_threshold=h.reaction_threshold,
        lattice_coupling=h.lattice_coupling,
    )


@physics_ext_router.post("/lenr/event", response_model=LENREventResponse)
async def lenr_event(request: LENREventRequest) -> LENREventResponse:
    """Record a LENR coherence event and return aggregate statistics."""
    from cohezion.physics.lenr import LENRHamiltonian

    h = LENRHamiltonian(agent_id=request.agent_id)
    h.record_coherence_event(request.coherence)
    rate = h.reaction_rate(request.coherence)
    return LENREventResponse(
        coherence=request.coherence,
        reaction_rate=rate,
        mean_rate=h.mean_rate,
        event_count=h.event_count,
        agent_id=request.agent_id,
    )


# ─── Ionic Cluster, Dielectric, Sarfatti, QGP ────────────────────


class IonicClusterStatusResponse(BaseModel):
    """Ionic cluster plasma resonance state."""

    plasma_density: float
    ionisation_rate: float
    hiho_equilibrium: bool
    active_ions: int
    steps_taken: int


class IonicClusterStepRequest(BaseModel):
    delta: float
    agent_id: str = "ionic-bridge"


@physics_ext_router.get("/ionic-cluster/status", response_model=IonicClusterStatusResponse)
async def get_ionic_cluster_status(
    agent_id: str = "ionic-bridge",
) -> IonicClusterStatusResponse:
    """Return fresh IonicClusterState — stateless per-request snapshot."""
    from cohezion.physics.ionic_cluster import IonicClusterState

    state = IonicClusterState()
    return IonicClusterStatusResponse(
        plasma_density=state.plasma_density,
        ionisation_rate=state.ionisation_rate(),
        hiho_equilibrium=state.hiho_equilibrium(),
        active_ions=state.active_ions,
        steps_taken=state.steps_taken,
    )


@physics_ext_router.post("/ionic-cluster/step", response_model=IonicClusterStatusResponse)
async def post_ionic_cluster_step(
    request: IonicClusterStepRequest,
) -> IonicClusterStatusResponse:
    """Advance IonicClusterState by delta and return new state."""
    from cohezion.physics.ionic_cluster import IonicClusterState

    state = IonicClusterState()
    state.step(request.delta)
    return IonicClusterStatusResponse(
        plasma_density=state.plasma_density,
        ionisation_rate=state.ionisation_rate(),
        hiho_equilibrium=state.hiho_equilibrium(),
        active_ions=state.active_ions,
        steps_taken=state.steps_taken,
    )


class DielectricPolarizationResponse(BaseModel):
    """Dielectric EHD polarization metrics."""

    voltage: float
    biefield_brown_force: float
    mean_permittivity: float


@physics_ext_router.get("/dielectric/polarization", response_model=DielectricPolarizationResponse)
async def get_dielectric_polarization(
    voltage: float = 10000.0,
) -> DielectricPolarizationResponse:
    """Return Biefield-Brown EHD force for the given voltage."""
    from cohezion.physics.dielectric import DielectricField

    field = DielectricField(voltage=max(0.0, voltage))
    force_vec = field.biefield_brown_force()
    return DielectricPolarizationResponse(
        voltage=voltage,
        biefield_brown_force=float(force_vec[2]),
        mean_permittivity=field.mean_permittivity,
    )


class SarfattiBackActionResponse(BaseModel):
    """Sarfatti post-quantum back-action state."""

    coherence: float
    back_action_amplitude: float
    metric_coupling: float
    hiho_attractor_engaged: bool


@physics_ext_router.get("/sarfatti/backaction", response_model=SarfattiBackActionResponse)
async def get_sarfatti_backaction(
    coherence: float = 0.5,
    destiny_weight: float = 0.5,
) -> SarfattiBackActionResponse:
    """Return Sarfatti retrocausal back-action amplitude for given coherence."""
    from cohezion.physics.sarfatti_bridge import SarfattiBackAction

    sa = SarfattiBackAction(coherence=coherence, destiny_weight=destiny_weight)
    return SarfattiBackActionResponse(
        coherence=sa.coherence,
        back_action_amplitude=sa.back_action_amplitude(),
        metric_coupling=sa.metric_coupling(),
        hiho_attractor_engaged=sa.hiho_attractor_engaged(),
    )


class QGPStatusResponse(BaseModel):
    """Quark-Gluon Plasma HIHO deconfinement state."""

    quark_coherence: float
    deconfinement_rate: float
    qcd_hiho: bool
    is_deconfined: bool
    chromatic_coherence: float


@physics_ext_router.get("/qgp/status", response_model=QGPStatusResponse)
async def get_qgp_status(
    quark_coherence: float = 0.5,
    temperature_mev: float = 155.0,
) -> QGPStatusResponse:
    """Return QGP deconfinement state for given quark coherence."""
    from cohezion.physics.sarfatti_bridge import QuarkGluonPlasma

    qgp = QuarkGluonPlasma(quark_coherence=quark_coherence, temperature_mev=temperature_mev)
    return QGPStatusResponse(
        quark_coherence=qgp.quark_coherence,
        deconfinement_rate=qgp.deconfinement_rate(),
        qcd_hiho=qgp.qcd_hiho(),
        is_deconfined=qgp.is_deconfined(),
        chromatic_coherence=qgp.chromatic_coherence(),
    )


class HihoCompositeResponse(BaseModel):
    """Composite HIHO score from three independent physics formalisms."""

    hiho_reciprocity: float
    hiho_condensate: float
    hiho_damping: float
    composite: float
    routing_tier: str
    condensate_phase: str
    is_critically_damped: bool
    quality_budget: float


@physics_ext_router.get("/hiho-composite", response_model=HihoCompositeResponse)
async def get_hiho_composite(
    quality_budget: float = 0.0,
) -> HihoCompositeResponse:
    """Return composite HIHO score from three physics formalisms.

    Aggregates three orthogonal routing quality signals:
    - hiho_reciprocity (NonReciprocalHamiltonian): routing asymmetry between tiers
    - hiho_condensate (TwoComponentCondensate): tier load balance (order parameter)
    - hiho_damping (DampedRoutingOscillator): routing convergence stability

    All three map to the HIHO kernel 4·u·(1-u); composite = arithmetic mean.
    """
    from cohezion.physics.damped_routing_oscillator import make_triune_oscillator
    from cohezion.physics.non_reciprocal_hamiltonian import make_triune_routing_hamiltonian
    from cohezion.physics.two_component_bec import make_triune_bec, suggest_routing_from_bec

    quality_signal = quality_budget * 2.0  # map budget to [-1,1] range

    nrh = make_triune_routing_hamiltonian()
    bec = make_triune_bec(quality_budget=quality_budget)
    osc = make_triune_oscillator(quality_signal=max(-1.0, min(1.0, quality_signal)))

    r = nrh.hiho_reciprocity_score()
    c = bec.hiho_condensate_score()
    d = osc.hiho_damping_score()
    composite = (r + c + d) / 3.0

    return HihoCompositeResponse(
        hiho_reciprocity=r,
        hiho_condensate=c,
        hiho_damping=d,
        composite=composite,
        routing_tier=suggest_routing_from_bec(quality_budget),
        condensate_phase=bec.phase().value,
        is_critically_damped=osc.is_critically_damped(),
        quality_budget=quality_budget,
    )


# NonReciprocalHamiltonian routes


class NrhStatusResponse(BaseModel):
    """Non-reciprocal Hamiltonian routing state."""

    hiho_reciprocity_score: float
    symmetrization_error: float
    is_hiho_symmetric: bool
    n_dof: int


@physics_ext_router.get("/nrh/status", response_model=NrhStatusResponse)
async def get_nrh_status() -> NrhStatusResponse:
    """Return non-reciprocal Hamiltonian routing state for Triune tier coupling."""
    from cohezion.physics.non_reciprocal_hamiltonian import make_triune_routing_hamiltonian

    nrh = make_triune_routing_hamiltonian()
    return NrhStatusResponse(
        hiho_reciprocity_score=nrh.hiho_reciprocity_score(),
        symmetrization_error=nrh.symmetrization_error(),
        is_hiho_symmetric=nrh.is_hiho_reciprocal(),
        n_dof=nrh.n_dof,
    )


# TwoComponentCondensate routes


class BecStatusResponse(BaseModel):
    """Two-component BEC routing state."""

    phase: str
    rho1: float
    rho2: float
    hiho_condensate_score: float
    is_first_order_regime: bool
    routing_tier: str
    quality_budget: float


@physics_ext_router.get("/bec2c/status", response_model=BecStatusResponse)
async def get_bec2c_status(
    quality_budget: float = 0.0,
) -> BecStatusResponse:
    """Return two-component exciton condensate routing state (Qi et al. 2026) for given quality budget."""
    from cohezion.physics.two_component_bec import make_triune_bec, suggest_routing_from_bec

    bec = make_triune_bec(quality_budget=quality_budget)
    ops = bec.order_parameters()
    return BecStatusResponse(
        phase=bec.phase().value,
        rho1=ops["rho1"],
        rho2=ops["rho2"],
        hiho_condensate_score=bec.hiho_condensate_score(),
        is_first_order_regime=bec.is_first_order_regime(),
        routing_tier=suggest_routing_from_bec(quality_budget),
        quality_budget=quality_budget,
    )


# DampedRoutingOscillator routes


class OscillatorStatusResponse(BaseModel):
    """Damped routing oscillator state."""

    damping_ratio: float
    hiho_damping_score: float
    is_critically_damped: bool
    settle_time_2pct: float
    routing_tier: str
    pid_kp: float
    pid_kd: float


@physics_ext_router.get("/oscillator/status", response_model=OscillatorStatusResponse)
async def get_oscillator_status(
    quality_signal: float = 0.0,
    damping_ratio: float = 1.0,
) -> OscillatorStatusResponse:
    """Return damped routing oscillator state for given quality signal."""
    from cohezion.physics.damped_routing_oscillator import make_triune_oscillator

    osc = make_triune_oscillator(
        quality_signal=max(-1.0, min(1.0, quality_signal)),
        damping_ratio=damping_ratio,
    )
    pid = osc.pid_coefficients()
    return OscillatorStatusResponse(
        damping_ratio=osc.damping_ratio,
        hiho_damping_score=osc.hiho_damping_score(),
        is_critically_damped=osc.is_critically_damped(),
        settle_time_2pct=osc.settle_time_2pct,
        routing_tier=osc.routing_tier(),
        pid_kp=pid["Kp"],
        pid_kd=pid["Kd"],
    )


__all__ = ["physics_ext_router"]
