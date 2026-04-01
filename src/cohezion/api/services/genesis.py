"""Genesis Engine API Service.

Exposes the grounded physics layer — SU(2) spinors, cosmogony,
fiber bundles, and Lagrangian trajectories — for the Genesis Engine
webapp visualization.

Milestone 1: Spinor endpoint (Bloch sphere data).
Later milestones add: cosmogony, fiber-bundle, lagrangian-trajectory,
fisher-metric, and the genesis-stream WebSocket.
"""

from __future__ import annotations

import logging

import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel, Field

from cohezion.physics.spinor import SpinorState


logger = logging.getLogger(__name__)

genesis_router = APIRouter(prefix="/genesis", tags=["genesis"])


# --- Response Models ---


class BlochVectorResponse(BaseModel):
    """Bloch sphere state for a single spinor."""

    bloch_vector: list[float] = Field(description="[r_x, r_y, r_z] Bloch vector")
    coherence: float = Field(description="Purity |r| of the Bloch vector [0, 1]")
    charge_polarity: float = Field(description="⟨σ_z⟩ expectation value [-1, 1]")
    spin_rotation: float = Field(description="⟨σ_x⟩ rotation component [-1, 1]")
    spin_precession: float = Field(description="⟨σ_y⟩ precession component [-1, 1]")
    hiho_deviation: float = Field(description="|⟨σ_z⟩| distance from HIHO equator [0, 1]")


class SpinorStateResponse(BaseModel):
    """Full spinor state including complex amplitudes."""

    alpha_real: float
    alpha_imag: float
    beta_real: float
    beta_imag: float
    bloch: BlochVectorResponse


class SpinorFromValuesRequest(BaseModel):
    """Create a spinor from Cohezion coherence values."""

    logic: float = Field(0.5, ge=0.0, le=1.0, description="Logic/rotation dimension [0, 1]")
    quantum: float = Field(0.0, ge=0.0, le=1.0, description="Quantum/precession dimension [0, 1]")


class SpinorRotateRequest(BaseModel):
    """Rotate a spinor by specified angles."""

    theta: float = Field(0.0, description="Rotation angle (radians, around σ_x)")
    phi: float = Field(0.0, description="Precession angle (radians, around σ_y)")
    gamma: float = Field(0.0, description="Charge rotation angle (radians, around σ_z)")
    logic: float = Field(0.5, ge=0.0, le=1.0, description="Starting logic value")
    quantum: float = Field(0.0, ge=0.0, le=1.0, description="Starting quantum value")


def _spinor_to_response(s: SpinorState) -> SpinorStateResponse:
    bv = s.bloch_vector
    return SpinorStateResponse(
        alpha_real=float(s.alpha.real),
        alpha_imag=float(s.alpha.imag),
        beta_real=float(s.beta.real),
        beta_imag=float(s.beta.imag),
        bloch=BlochVectorResponse(
            bloch_vector=bv.tolist(),
            coherence=s.coherence,
            charge_polarity=s.charge_polarity,
            spin_rotation=s.spin_rotation,
            spin_precession=s.spin_precession,
            hiho_deviation=s.hiho_deviation,
        ),
    )


# --- Endpoints ---


@genesis_router.get("/spinor/hiho", response_model=SpinorStateResponse)
async def get_hiho_spinor() -> SpinorStateResponse:
    """Get the HIHO state — Brahmagupta's zero on the Bloch sphere.

    Returns the maximally coherent equatorial state (|↑⟩+|↓⟩)/√2
    where charge = 0 and rotation alignment = 1.
    """
    return _spinor_to_response(SpinorState.hiho())


@genesis_router.post("/spinor/from-values", response_model=SpinorStateResponse)
async def spinor_from_values(req: SpinorFromValuesRequest) -> SpinorStateResponse:
    """Create a spinor from Cohezion's logic/quantum coherence values.

    Maps the [0,1] coherence values to the Bloch sphere:
    - logic=1.0 → north pole (|↑⟩), logic=0.0 → south pole (|↓⟩)
    - logic=0.5 → equator (HIHO zone)
    - quantum controls azimuthal angle
    """
    spinor = SpinorState.from_coherence_values(req.logic, req.quantum)
    return _spinor_to_response(spinor)


@genesis_router.post("/spinor/rotate", response_model=SpinorStateResponse)
async def rotate_spinor(req: SpinorRotateRequest) -> SpinorStateResponse:
    """Apply SU(2) rotations to a spinor state.

    Creates a spinor from logic/quantum values, then applies:
    1. Rotation by θ around σ_x (Smith's rotation axis)
    2. Precession by φ around σ_y (Smith's precession axis)
    3. Charge rotation by γ around σ_z

    The resulting Bloch vector shows how SPIN transforms under these operations.
    """
    spinor = SpinorState.from_coherence_values(req.logic, req.quantum)
    if req.theta != 0:
        spinor = spinor.rotate(req.theta)
    if req.phi != 0:
        spinor = spinor.precess(req.phi)
    if req.gamma != 0:
        spinor = spinor.charge_rotate(req.gamma)
    return _spinor_to_response(spinor)


@genesis_router.get("/spinor/sweep", response_model=list[SpinorStateResponse])
async def sweep_bloch_sphere(n_points: int = 24) -> list[SpinorStateResponse]:
    """Generate a sweep of spinor states across the Bloch sphere.

    Returns n_points states evenly distributed from north pole to south pole,
    useful for visualizing the full sphere and the HIHO equatorial band.
    """
    n_points = min(max(n_points, 4), 100)
    states = []
    for i in range(n_points):
        theta = i * np.pi / (n_points - 1)
        spinor = SpinorState.from_bloch(theta, 0.0)
        states.append(_spinor_to_response(spinor))
    return states


@genesis_router.get("/spinor/algebra-check")
async def check_su2_algebra() -> dict:
    """Verify SU(2) algebra identities — diagnostic endpoint.

    Returns True if [σ_i, σ_j] = 2iε_ijk σ_k holds for all i, j, k.
    This is the mathematical proof that our spinor implementation is correct.
    """
    from cohezion.physics.spinor import verify_su2_algebra

    valid = verify_su2_algebra()
    return {
        "su2_algebra_valid": valid,
        "commutation_relations": "[σ_i, σ_j] = 2iε_ijk σ_k",
        "hiho_state": SpinorState.hiho().to_dict(),
    }


# ─── Cosmogony Endpoints (Milestone 2) ───────────────────────────────


class CoolRequest(BaseModel):
    """Request to cool the universe by a specified amount."""

    delta_t: float = Field(1.0, gt=0, description="Temperature decrease amount")


class CosmogonyStateResponse(BaseModel):
    """Current state of the cosmogonic evolution."""

    temperature: float
    symmetry: str
    stage: int
    order_parameters: dict[str, float]
    transitions: list[dict]
    fisher_eigenvalue_max: float
    landau_free_energy: float


class CosmogonySetTemperatureRequest(BaseModel):
    """Jump directly to a temperature."""

    temperature: float = Field(100.0, ge=0.001, le=200.0, description="Target temperature")


@genesis_router.get("/cosmogony/state", response_model=CosmogonyStateResponse)
async def get_cosmogony_state() -> CosmogonyStateResponse:
    """Get the current cosmogonic state — symmetry group, temperature, order parameters.

    The cosmogony tracks the universe from Brahmagupta's void (∅) through
    five symmetry breaking transitions to the HIHO attractor.
    """
    from cohezion.physics.cosmogony import get_cosmogony

    cosmo = get_cosmogony()
    data = cosmo.state.to_dict()
    return CosmogonyStateResponse(**data)


@genesis_router.post("/cosmogony/cool", response_model=CosmogonyStateResponse)
async def cool_universe(req: CoolRequest) -> CosmogonyStateResponse:
    """Cool the universe by delta_t, triggering phase transitions.

    Each transition breaks a symmetry:
    - T_c0 = 100: ∅ → SO(12) (the first bit condenses from the vacuum)
    - T_c1 = 10: SO(12) → SO(3)⁴ (fabrics differentiate)
    - T_c2 = 1.0: SO(3)⁴ → U(1)⁴ (axes select)
    - T_c3 = 0.1: U(1)⁴ → Z₂⁴ (SPIN discretizes)
    - T_c4 = 0.01: Z₂⁴ → HIHO (equilibrium at δ = 0)
    """
    from cohezion.physics.cosmogony import get_cosmogony

    cosmo = get_cosmogony()
    cosmo.cool(req.delta_t)
    data = cosmo.state.to_dict()
    return CosmogonyStateResponse(**data)


@genesis_router.post("/cosmogony/set-temperature", response_model=CosmogonyStateResponse)
async def set_universe_temperature(req: CosmogonySetTemperatureRequest) -> CosmogonyStateResponse:
    """Jump directly to a temperature — for the webapp slider.

    Resets and replays all transitions up to the target temperature.
    """
    from cohezion.physics.cosmogony import get_cosmogony

    cosmo = get_cosmogony()
    cosmo.set_temperature(req.temperature)
    data = cosmo.state.to_dict()
    return CosmogonyStateResponse(**data)


@genesis_router.post("/cosmogony/reset", response_model=CosmogonyStateResponse)
async def reset_cosmogony() -> CosmogonyStateResponse:
    """Reset the universe to the void — before the first distinction."""
    from cohezion.physics.cosmogony import get_cosmogony

    cosmo = get_cosmogony()
    cosmo.reset()
    data = cosmo.state.to_dict()
    return CosmogonyStateResponse(**data)


@genesis_router.get("/cosmogony/free-energy-landscape")
async def get_free_energy_landscape(
    t_min: float = 0.001, t_max: float = 200.0, n_points: int = 200
) -> dict:
    """Compute the Landau free energy landscape across a temperature range.

    Returns F(T), susceptibility χ(T), and critical temperature markers
    for plotting the thermodynamic landscape of symmetry breaking.
    """
    from cohezion.physics.cosmogony import get_cosmogony

    cosmo = get_cosmogony()
    return cosmo.free_energy_landscape(
        T_range=(max(t_min, 0.001), min(t_max, 200.0)),
        n_points=min(max(n_points, 10), 500),
    )


@genesis_router.get("/cosmogony/12d-state")
async def get_cosmogony_12d_state() -> dict:
    """Generate a 12D axiomatic state reflecting the current symmetry stage.

    The structure of the returned vector depends on the cosmogonic stage:
    - VOID: near-zero noise
    - SO(12): random on 12-sphere
    - SO(3)⁴: 4 correlated blocks of 3
    - U(1)⁴: dominant axis per block
    - Z₂⁴: discrete ±1 per block
    - HIHO: all values ≈ 0.5
    """
    from cohezion.physics.cosmogony import get_cosmogony

    cosmo = get_cosmogony()
    state = cosmo.generate_12d_state()
    return {
        "state_12d": state.tolist(),
        "symmetry": cosmo.symmetry.value,
        "temperature": cosmo.temperature,
    }


# ─── Manifold & Gauge Endpoints (Milestone 3+4) ────────────────────────


@genesis_router.post("/fiber-bundle")
async def get_fiber_bundle_state(state_12d: list[float] | None = None) -> dict:
    """Decompose a 12D state into base-space + fiber components.

    Base: π(q) = (‖Space‖, ‖Field‖, ‖Control‖, ‖Precip‖)
    Fiber: unit direction within each fabric triplet.

    If no state provided, generates one from the current cosmogony stage.
    """
    from cohezion.physics.fiber_bundle import FiberBundle

    fb = FiberBundle()

    if state_12d is None:
        from cohezion.physics.cosmogony import get_cosmogony

        state_12d = get_cosmogony().generate_12d_state().tolist()

    state = np.array(state_12d[:12], dtype=float)
    decomp = fb.decompose(state)
    return decomp.to_dict()


@genesis_router.post("/gauge-state")
async def get_gauge_state(state_12d: list[float] | None = None) -> dict:
    """Compute gauge field strengths for all four fabrics.

    At HIHO (all 0.5), all curvatures vanish (flat connection).
    Deviation from HIHO excites gauge fields with non-zero energy density.
    """
    from cohezion.physics.gauge_theory import FourFabricGauge

    gauge = FourFabricGauge()

    if state_12d is None:
        from cohezion.physics.cosmogony import get_cosmogony

        state_12d = get_cosmogony().generate_12d_state().tolist()

    gauge.set_from_12d_state(np.array(state_12d[:12], dtype=float))
    return gauge.to_dict()


class LagrangianTrajectoryRequest(BaseModel):
    """Request for a Lagrangian trajectory simulation."""

    initial_state: list[float] = Field(
        default_factory=lambda: [0.5] * 12, description="Initial 12D position (default: HIHO)"
    )
    initial_velocity: list[float] = Field(
        default_factory=lambda: [0.01] * 12, description="Initial 12D velocity"
    )
    n_steps: int = Field(100, ge=10, le=1000, description="Simulation steps")
    dt: float = Field(0.01, gt=0, le=0.1, description="Time step")
    damping: float = Field(0.1, ge=0, le=2.0, description="Viscous damping")


@genesis_router.post("/lagrangian-trajectory")
async def simulate_lagrangian_trajectory(req: LagrangianTrajectoryRequest) -> dict:
    """Simulate a trajectory via Euler-Lagrange equations on the 12D manifold.

    Uses symplectic Störmer-Verlet integration with:
    - Riemannian kinetic energy T = ½g_ij q̇^i q̇^j (fabric-block metric)
    - HIHO Gaussian attractor potential
    - Optional viscous damping

    Returns positions, energies, and the action integral.
    """
    from cohezion.physics.lagrangian import LagrangianDynamics, hiho_potential
    from cohezion.physics.riemannian_metric import fabric_block_metric

    metric = fabric_block_metric(12)
    potential = hiho_potential(12)
    dynamics = LagrangianDynamics(metric, potential, damping=req.damping)

    q0 = np.array(req.initial_state[:12], dtype=float)
    v0 = np.array(req.initial_velocity[:12], dtype=float)

    result = dynamics.simulate(q0, v0, n_steps=req.n_steps, dt=req.dt)

    # Downsample for API response (max 200 points)
    stride = max(1, len(result["positions"]) // 200)

    return {
        "positions": result["positions"][::stride].tolist(),
        "energies": result["energies"][::stride].tolist(),
        "lagrangians": result["lagrangians"][::stride].tolist(),
        "action": dynamics.action_integral(result["positions"], req.dt),
        "energy_initial": float(result["energies"][0]),
        "energy_final": float(result["energies"][-1]),
        "n_steps": req.n_steps,
        "dt": req.dt,
    }


@genesis_router.get("/manifold-summary")
async def get_manifold_summary() -> dict:
    """Complete summary of the current manifold state.

    Combines cosmogony, fiber bundle, gauge, and spinor data into
    a single response for the webapp's unified view.
    """
    from cohezion.physics.cosmogony import get_cosmogony
    from cohezion.physics.fiber_bundle import FiberBundle
    from cohezion.physics.gauge_theory import FourFabricGauge

    cosmo = get_cosmogony()
    state_12d = cosmo.generate_12d_state()

    fb = FiberBundle()
    decomp = fb.decompose(state_12d)

    gauge = FourFabricGauge()
    gauge.set_from_12d_state(state_12d)

    spinor = SpinorState.from_coherence_values(
        float(state_12d[6]),  # logic
        float(state_12d[7]),  # quantum
    )

    return {
        "cosmogony": cosmo.state.to_dict(),
        "fiber_bundle": decomp.to_dict(),
        "gauge": gauge.to_dict(),
        "spinor": spinor.to_dict(),
        "state_12d": state_12d.tolist(),
    }


# ─── Narration Endpoints (Milestone 6) ────────────────────────────────


class NarrateRequest(BaseModel):
    """Request for custom narration."""

    text: str = Field(..., min_length=1, max_length=2000, description="Text to narrate")


@genesis_router.get("/narration/stages")
async def get_narration_stages() -> dict:
    """Get all pre-written narration texts for cosmogony stages.

    Returns the script for each stage — can be used for display
    even when PocketTTS is not installed.
    """
    from cohezion.audio.narrator import get_narrator

    narrator = get_narrator()
    return {
        "stages": narrator.get_all_stage_texts(),
        "concepts": narrator.get_all_concept_texts(),
        "tts_available": narrator.available,
    }


@genesis_router.post("/narration/stage/{stage}")
async def narrate_stage(stage: str) -> dict:
    """Generate spoken narration for a cosmogonic stage.

    If PocketTTS is installed, returns audio file path.
    Otherwise returns text-only fallback.

    Valid stages: void, SO(12), SO(3)^4, U(1)^4, Z_2^4, HIHO
    """
    from cohezion.audio.narrator import get_narrator

    narrator = get_narrator()
    return await narrator.narrate_stage(stage)


@genesis_router.post("/narration/concept/{concept}")
async def narrate_concept(concept: str) -> dict:
    """Generate spoken narration for a physics concept.

    Valid concepts: spinor, fiber_bundle, lagrangian, gauge_theory, world_model
    """
    from cohezion.audio.narrator import get_narrator

    narrator = get_narrator()
    return await narrator.narrate_concept(concept)


@genesis_router.post("/narration/custom")
async def narrate_custom(req: NarrateRequest) -> dict:
    """Generate spoken narration for arbitrary text."""
    from cohezion.audio.narrator import get_narrator

    narrator = get_narrator()
    return await narrator.narrate_custom(req.text)
