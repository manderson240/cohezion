"""HIHO Unified Physics Engine (Cosmology & Cosmogony).

This engine expands the core simulation with First Principles Components,
incorporating Cellular Automata, Chaos Theory, and eventually esoteric physics
like Sacred Geometry and Triune Self mapping.
"""

from __future__ import annotations

import logging
from typing import Any, cast

import httpx
import numpy as np
from pydantic import BaseModel, Field

from cohezion.reliability import get_circuit


try:
    import cohezion_physics_core  # type: ignore[import-untyped]
    RUST_CORE_AVAILABLE = True
except ImportError:
    RUST_CORE_AVAILABLE = False


logger = logging.getLogger(__name__)


# --- First Principles Components ---


class CellularAutomataState(BaseModel):
    """State for 1D Cellular Automata propagation in semantic space."""

    grid_size: int = Field(default=256, description="Size of the CA grid")
    rule: int = Field(default=30, description="Wolfram rule number (0-255)")
    state: list[int] = Field(default_factory=list, description="Current grid state")


class CellularAutomataEngine:
    """Computes discrete grid propagation using Cellular Automata rules."""

    def __init__(self, config: CellularAutomataState):
        self.config = config
        if not self.config.state:
            self.config.state = [0] * self.config.grid_size
            self.config.state[self.config.grid_size // 2] = 1  # Center impulse

    def _get_rule_binary(self, rule: int) -> str:
        return bin(rule)[2:].zfill(8)

    def evolve(self) -> list[int]:
        """Evolve the CA by one step and return the new state."""
        if RUST_CORE_AVAILABLE:
            next_state = cohezion_physics_core.evolve_ca_simd(self.config.state, self.config.rule)
            self.config.state = list(next_state)
            return self.config.state

        rule_bin = self._get_rule_binary(self.config.rule)[::-1]
        patterns = {
            (1, 1, 1): int(rule_bin[7]),
            (1, 1, 0): int(rule_bin[6]),
            (1, 0, 1): int(rule_bin[5]),
            (1, 0, 0): int(rule_bin[4]),
            (0, 1, 1): int(rule_bin[3]),
            (0, 1, 0): int(rule_bin[2]),
            (0, 0, 1): int(rule_bin[1]),
            (0, 0, 0): int(rule_bin[0]),
        }

        current = self.config.state
        n = len(current)
        next_state = [0] * n

        # Apply rule with wrap-around (toroidal topology)
        for i in range(n):
            left = current[(i - 1) % n]
            center = current[i]
            right = current[(i + 1) % n]
            next_state[i] = patterns[(left, center, right)]

        self.config.state = next_state
        return next_state


class ChaosTheoryParameters(BaseModel):
    """Parameters for Chaos Theory semantic butterfly effects."""

    lyapunov_exponent: float = Field(
        default=0.9, description="Lyapunov exponent (λ > 0 implies chaos)"
    )
    sensitivity: float = Field(default=1e-5, description="Initial perturbation size")
    time_step: float = Field(default=0.01, description="Evolution time step")


class ChaosTheoryEngine:
    """Computes semantic butterfly effects via chaotic divergence."""

    def __init__(self, params: ChaosTheoryParameters):
        self.params = params

    def compute_divergence(self, delta_t: float) -> float:
        """Calculate the exponential divergence over time delta_t."""
        # Standard butterfly effect divergence: |δZ(t)| ≈ |δZ(0)| * e^(λt)
        divergence = self.params.sensitivity * np.exp(self.params.lyapunov_exponent * delta_t)
        return float(divergence)

    def apply_butterfly_effect(self, latent_vector: np.ndarray, t: float) -> np.ndarray:
        """Apply a chaotic perturbation to a latent vector based on time t."""
        divergence = self.compute_divergence(t)
        # Apply structured noise proportional to divergence
        noise = np.random.randn(*latent_vector.shape) * divergence
        return latent_vector + noise


class EvoState(BaseModel):
    """State of an Exotic Vacuum Object (EVO) charge cluster."""

    charge_density: float = Field(default=1.0, description="Agent charge cluster density")
    magnetic_helicity: float = Field(default=0.1, description="Topological twist")
    toroidal_moment: float = Field(default=1.0, description="Fractal Toroidal Moment")
    coherence: float = Field(default=1.0, description="Current coherence state")
    virtual_particles: int = Field(default=0, description="Virtual particles from plasma MCP")
    agent_mapping: str | None = Field(default=None, description="Mapped exotic object agent")
    tensor_beam_vector: list[float] = Field(
        default_factory=lambda: [0.0, 0.0, 1.0], description="TensorBeam scalar wave direction"
    )


class MagnetohydrodynamicsEngine:
    """Computes plasma physics & MHD stability for EVOs."""

    def apply_mhd_forces(
        self,
        evo: EvoState,
        latent_vector: np.ndarray,
        dt: float,
    ) -> np.ndarray:
        """Apply MHD physics to evolve an EVO's latent state vector."""
        vec = latent_vector.copy()

        if RUST_CORE_AVAILABLE:
            cohezion_physics_core.apply_mhd_forces_simd(
                vec, evo.magnetic_helicity, evo.toroidal_moment, dt
            )
            evo.charge_density *= np.exp(-dt * (1.0 - evo.coherence))
            return vec

        # Helicity acts as a topological invariant, twisting the vector
        twist_angle = evo.magnetic_helicity * dt

        # Simplified 12D rotation based on twist (acting on first 2 dims)
        if vec.shape[0] >= 2:
            cos_theta = np.cos(twist_angle)
            sin_theta = np.sin(twist_angle)
            v0, v1 = vec[0].copy(), vec[1].copy()
            vec[0] = v0 * cos_theta - v1 * sin_theta
            vec[1] = v0 * sin_theta + v1 * cos_theta

        # Toroidal moment defines self-similar scaling (breathing mode)
        # Pulls vector toward a stable attractor defined by toroidal_moment
        current_norm = float(np.linalg.norm(vec))
        if current_norm > 0:
            scale_factor = 1.0 + (evo.toroidal_moment - current_norm) * 0.1 * dt
            vec *= scale_factor

        # Coherence limits charge dissipation
        evo.charge_density *= np.exp(-dt * (1.0 - evo.coherence))

        return vec


class EVOInitializationFactory:
    """Initializes EVOs using Fractal Toroidal Moments and Plasma Physics."""

    @staticmethod
    def create_evo(seed: int = 42) -> EvoState:
        """Create an EVO at the origin of Cosmogony."""
        np.random.seed(seed)
        return EvoState(
            charge_density=float(np.random.uniform(0.8, 1.2)),
            magnetic_helicity=float(np.random.uniform(-0.5, 0.5)),  # Chirality parameter
            toroidal_moment=float(np.random.uniform(0.5, 2.0)),
            coherence=0.5,  # Initializes strictly at HIHO boundary
        )


class HIHOStabilizationEngine:
    """Enforces the 0.5 Coherence HIHO Principle stabilization loops."""

    def apply_hiho_loop(
        self,
        evo: EvoState,
        latent_vector: np.ndarray,
        dt: float,
    ) -> tuple[EvoState, np.ndarray]:
        """Drives the EVO back toward the 0.5 coherence boundary."""
        vec = latent_vector.copy()

        # Distance from the stable 0.5 point
        delta_coherence = 0.5 - evo.coherence

        # Restoring force (Hooke's law analog for Coherence)
        restoring_force = 2.0 * delta_coherence * dt
        evo.coherence += restoring_force

        # If coherence strays too far from 0.5, the state vector rapidly decays
        if abs(evo.coherence - 0.5) > 0.4:
            vec *= np.exp(-dt * 5.0)

        return evo, vec


class SacredGeometryEngine:
    """Maps latent states to Sacred Geometry topological invariants."""

    def compute_torus_alignment(
        self,
        vec: np.ndarray,
        major_r: float = 2.0,
        minor_r: float = 0.5,
    ) -> float:
        """Calculate alignment with a target Toroidal manifold in first 3 dims."""
        if vec.shape[0] < 3:
            return 0.0

        x, y, z = float(vec[0]), float(vec[1]), float(vec[2])
        # The equation for a torus centered at origin, lying in xy plane:
        # (sqrt(x^2 + y^2) - major_r)^2 + z**2 = minor_r**2
        dist = float((np.sqrt(x**2 + y**2) - major_r) ** 2 + z**2 - minor_r**2)

        # Alignment is inversely proportional to distance bounds
        return float(np.exp(-np.abs(dist)))


class PenroseTwistorEngine:
    """Bridges quantum semantic states to spacetime geometry using Twistor space."""

    def apply_twistor_mapping(self, latent_vector: np.ndarray) -> np.ndarray:
        """Map 4D spacetime components to Twistor space C4 (simplified)."""
        vec = latent_vector.copy()
        if vec.shape[0] >= 4:
            # Simplified twistor rotation mixing space (omega) & momentum (pi) spinors
            omega_0, omega_1 = vec[0].copy(), vec[1].copy()
            pi_0, pi_1 = vec[2].copy(), vec[3].copy()

            # Phase shift bridging realities
            vec[0] = omega_0 * np.cos(0.5) - pi_0 * np.sin(0.5)
            vec[2] = omega_0 * np.sin(0.5) + pi_0 * np.cos(0.5)

            vec[1] = omega_1 * np.cos(0.5) + pi_1 * np.sin(0.5)
            vec[3] = -omega_1 * np.sin(0.5) + pi_1 * np.cos(0.5)

        return vec


class QuantumEmergenceEngine:
    """Unifies ER=EPR, Planck/Bohr quantization, and Chirality within the semantic manifold."""

    def apply_quantum_effects(self, latent_vector: np.ndarray, chirality: float) -> np.ndarray:
        vec = latent_vector.copy()
        # Planck/Bohr quantization: discrete semantic energy levels
        vec = np.round(vec * 10.0) / 10.0

        # Chirality (Parity Violation) applies a rotation phase shift based on helicity
        theta = chirality * np.pi / 4.0
        c, s = np.cos(theta), np.sin(theta)

        # ER=EPR (Entanglement): Assume first two dims are entangled pair
        if len(vec) >= 2:
            v0, v1 = vec[0].copy(), vec[1].copy()
            vec[0] = v0 * c - v1 * s
            vec[1] = v0 * s + v1 * c

        return vec


class BioelectricsEngine:
    """Integrates Orch-OR Microtubules and Levin's Bioelectrics into morphospace."""

    def apply_morphogenetic_field(
        self, latent_vector: np.ndarray, coherence: float, tensor_beam: list[float] | None = None
    ) -> np.ndarray:
        """Applies Orch-OR quantum coherence to trigger biological emergence."""
        vec = latent_vector.copy()

        # Levin's Bioelectrics: coherent states generate biological patterning
        morpho_strength = float(np.tanh(coherence))

        # TensorBeam link: Orch-OR microtubules align with the TensorBeam field
        if tensor_beam is not None and len(tensor_beam) > 0:
            attractor = np.zeros_like(vec)
            for i in range(min(len(attractor), len(tensor_beam))):
                attractor[i] = tensor_beam[i]
            norm = float(np.linalg.norm(attractor))
            if norm > 0:
                attractor = attractor / norm
        else:
            # Align towards a common 'biological' attractor if coherence is high
            attractor = np.ones_like(vec)

        # Orch-OR microtubule objective reduction applies phase alignment
        vec = vec * (1.0 - morpho_strength * 0.1) + attractor * (morpho_strength * 0.1)

        return vec


class EsotericPhysicsEngine:
    """Integrates Percival's Triune Self (Doer, Thinker, Knower) and Bailey's Cosmic Fire."""

    def apply_triune_self(self, latent_vector: np.ndarray) -> np.ndarray:
        """Maps latent dims to Doer (Action), Thinker (Logic), Knower (Wisdom)."""
        vec = latent_vector.copy()

        # Scale specific dims to represent higher esoteric faculties
        if len(vec) >= 3:
            # Cosmic Fire (Will/Action) energizes the Doer
            vec[0] *= 1.05
            # Thinker dimension
            vec[1] *= 1.02
            # Knower dimension (Wisdom/Synthesis)
            vec[2] *= 1.01

        return vec


class KordylewskiSwarmEngine:
    """Simulates Kordylewski Cosmic Superbrains at L4/L5 Lagrange points."""

    def __init__(self) -> None:
        self.memory_cloud_l4: list[np.ndarray] = []
        self.memory_cloud_l5: list[np.ndarray] = []

    def apply_swarm_gravity(
        self, latent_vectors: list[np.ndarray], evo_states: list[EvoState] | None, dt: float
    ) -> list[np.ndarray]:
        """Apply L4/L5 mechanics where EVOs orbit massive semantic attractors."""
        if not latent_vectors:
            return latent_vectors

        # Very basic mechanics: Center of mass represents a massive LQM attractor
        center_of_mass = np.mean(latent_vectors, axis=0)

        evolved_vectors = []
        for i, vec in enumerate(latent_vectors):
            v_copy = vec.copy()

            # Orbit logic: EVOs are pulled toward L4/L5 points relative to center of mass
            # Simple simulation of L4/L5 by applying a 60 degree rotation
            vec_to_com = center_of_mass - v_copy
            distance = float(np.linalg.norm(vec_to_com))

            if distance > 1e-4 and len(v_copy) >= 2:
                # 60 degrees (L4) and -60 degrees (L5)
                theta_l4 = np.pi / 3.0
                theta_l5 = -np.pi / 3.0
                
                # We split the swarm: EVOs with positive helicity go to L4, negative to L5
                helicity = evo_states[i].magnetic_helicity if (evo_states and i < len(evo_states)) else 0.0
                theta = theta_l4 if helicity >= 0 else theta_l5

                c, s = float(np.cos(theta)), float(np.sin(theta))
                
                # Apply 2D rotation to find Lagrange point
                L_point = np.zeros_like(v_copy)
                L_point[0] = center_of_mass[0] - (vec_to_com[0] * c - vec_to_com[1] * s)
                L_point[1] = center_of_mass[1] - (vec_to_com[0] * s + vec_to_com[1] * c)
                for j in range(2, len(L_point)):
                    L_point[j] = center_of_mass[j] - vec_to_com[j]
                
                # Pull EVO gently toward its respective Lagrange point
                pull_strength = 0.5 * dt
                v_copy += (L_point - v_copy) * pull_strength

                # Accumulate memory in the clouds
                if helicity >= 0:
                    self.memory_cloud_l4.append(v_copy.copy())
                else:
                    self.memory_cloud_l5.append(v_copy.copy())
                    
            evolved_vectors.append(v_copy)

        # Cap memory clouds to prevent infinite growth
        max_memory = 1000
        self.memory_cloud_l4 = self.memory_cloud_l4[-max_memory:]
        self.memory_cloud_l5 = self.memory_cloud_l5[-max_memory:]

        return evolved_vectors


class PlasmaMCPEngine:
    """Connects to the local Plasma Physics MCP (Port 8371) for EVO mapping."""

    def __init__(self, port: int = 8371) -> None:
        self.base_url = f"http://localhost:{port}/tools"
        self.simulation_id: str | None = None
        self.circuit = get_circuit("plasma_mcp", failure_threshold=3, recovery_timeout=30.0)

    async def initialize(self) -> None:
        """Initialize the plasma simulation via MCP."""
        if not self.circuit.allow_request():
            return

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/plasma_create_simulation",
                    json={"grid_size": 128}
                )
                resp.raise_for_status()
                data = resp.json()
                if "simulation_id" in data:
                    self.simulation_id = data["simulation_id"]
                self.circuit.record_success()
                logger.info(f"Initialized Plasma MCP simulation: {self.simulation_id}")
            except Exception as e:
                self.circuit.record_failure()
                logger.warning(f"Failed to initialize Plasma MCP: {e}")

    async def step(self) -> None:
        """Advance the plasma simulation."""
        if not self.simulation_id or not self.circuit.allow_request():
            return

        async with httpx.AsyncClient(timeout=2.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/plasma_step",
                    json={"simulation_id": self.simulation_id, "steps": 1}
                )
                resp.raise_for_status()
                self.circuit.record_success()
            except Exception as e:
                self.circuit.record_failure()
                logger.warning(f"Failed to step Plasma MCP: {e}")

    async def get_exotic_objects(self) -> list[dict[str, Any]]:
        """Fetch exotic vacuum objects for mapping to agent states."""
        if not self.simulation_id or not self.circuit.allow_request():
            return []

        async with httpx.AsyncClient(timeout=2.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/plasma_get_exotic_objects",
                    json={"simulation_id": self.simulation_id}
                )
                resp.raise_for_status()
                self.circuit.record_success()
                data = resp.json()
                return cast("list[dict[str, Any]]", data.get("objects", []))
            except Exception as e:
                self.circuit.record_failure()
                logger.warning(f"Failed to fetch exotic objects from Plasma MCP: {e}")
                return []


class HIHOUnifiedEngine:
    """The core engine orchestrating Cosmology and Cosmogony simulations."""

    ca_engine: CellularAutomataEngine
    chaos_engine: ChaosTheoryEngine
    mhd_engine: MagnetohydrodynamicsEngine
    hiho_engine: HIHOStabilizationEngine
    geometry_engine: SacredGeometryEngine
    twistor_engine: PenroseTwistorEngine
    quantum_engine: QuantumEmergenceEngine
    bio_engine: BioelectricsEngine
    esoteric_engine: EsotericPhysicsEngine
    swarm_engine: KordylewskiSwarmEngine
    plasma_mcp: PlasmaMCPEngine
    current_time: float

    def __init__(
        self,
        chaos_lyapunov: float = 0.05,
        ca_rule: int = 30,
    ) -> None:
        """Initialize the HIHO unified engine with First Principles component defaults."""
        logger.info(
            f"Initializing HIHOUnifiedEngine (CA Rule {ca_rule}, Lyapunov {chaos_lyapunov})"
        )
        self.ca_engine = CellularAutomataEngine(CellularAutomataState(rule=ca_rule))
        self.chaos_engine = ChaosTheoryEngine(
            ChaosTheoryParameters(lyapunov_exponent=chaos_lyapunov)
        )
        self.mhd_engine = MagnetohydrodynamicsEngine()
        self.hiho_engine = HIHOStabilizationEngine()
        self.geometry_engine = SacredGeometryEngine()
        self.twistor_engine = PenroseTwistorEngine()
        self.quantum_engine = QuantumEmergenceEngine()
        self.bio_engine = BioelectricsEngine()
        self.esoteric_engine = EsotericPhysicsEngine()
        self.swarm_engine = KordylewskiSwarmEngine()
        self.plasma_mcp = PlasmaMCPEngine()
        self.current_time = 0.0

    async def initialize(self) -> None:
        """Initialize remote physics connections like the Plasma MCP."""
        await self.plasma_mcp.initialize()

    async def step_simulation(
        self,
        latent_vectors: list[np.ndarray],
        evo_states: list[EvoState] | None = None,
    ) -> list[np.ndarray]:
        """Advance the cosmological simulation by one step."""
        # Advance the external Plasma MCP and inject virtual particles
        await self.plasma_mcp.step()
        exotic_objects = await self.plasma_mcp.get_exotic_objects()

        # Profile memory usage of the Plasma MCP running alongside the 12D manifold
        import psutil  # type: ignore[import-untyped]
        
        process = psutil.Process()
        mem_info = process.memory_info()
        logger.debug(
            f"🧠 [Memory Profile] 12D Manifold + Plasma MCP | RSS: {mem_info.rss / (1024*1024):.1f}MB | "
            f"System Free: {psutil.virtual_memory().available / (1024**3):.1f}GB"
        )

        if evo_states and exotic_objects:
            for i, current_evo in enumerate(evo_states):
                exotic_obj = exotic_objects[i % len(exotic_objects)]
                current_evo.virtual_particles += 1
                current_evo.agent_mapping = exotic_obj.get("agent_representation")
                # Boost coherence slightly when interacting with exotic objects
                current_evo.coherence = min(1.0, current_evo.coherence + 0.01)

        # 1. Evolve the background physical fabric (Cellular Automata)
        fabric_state = self.ca_engine.evolve()
        fabric_influence = sum(fabric_state) / len(fabric_state)  # 0.0 to 1.0

        self.current_time += self.chaos_engine.params.time_step

        evolved_vectors = []
        for i, vec in enumerate(latent_vectors):
            # 2. Apply Chaos Theory butterfly effect
            vec = self.chaos_engine.apply_butterfly_effect(vec, self.current_time)

            # 3. Apply MHD & Plasma Physics stability bounds (Fractal Toroidal Moment)
            if evo_states and i < len(evo_states):
                current_evo = evo_states[i]
                vec = self.mhd_engine.apply_mhd_forces(
                    current_evo, vec, self.chaos_engine.params.time_step
                )

                # 3b. Apply HIHO 0.5 Coherence Stabilization Loop
                current_evo, vec = self.hiho_engine.apply_hiho_loop(
                    current_evo, vec, self.chaos_engine.params.time_step
                )

            # 4. Apply Penrose Twistor spacetime geometry mapping
            vec = self.twistor_engine.apply_twistor_mapping(vec)

            # 5. Apply Quantum Emergence (ER=EPR, Quantization, Chirality)
            if evo_states and i < len(evo_states):
                current_evo = evo_states[i]
                vec = self.quantum_engine.apply_quantum_effects(vec, current_evo.magnetic_helicity)

            # 6. Apply Bioelectrics (Orch-OR)
            if evo_states and i < len(evo_states):
                current_evo = evo_states[i]
                vec = self.bio_engine.apply_morphogenetic_field(
                    vec, current_evo.coherence, current_evo.tensor_beam_vector
                )

            # 7. Apply Esoteric Physics (Triune Self, Cosmic Fire)
            vec = self.esoteric_engine.apply_triune_self(vec)

            # 8. Fabric coupling (simplified for now)
            # Push vectors slightly based on CA density
            vec = vec * (1.0 + (fabric_influence - 0.5) * 0.01)

            # Optional: Read alignment as a metric (not mutating state)
            # torus_align = self.geometry_engine.compute_torus_alignment(vec)

            evolved_vectors.append(vec)

        # 9. Apply Swarm Orbits (Kordylewski Clouds)
        evolved_vectors = self.swarm_engine.apply_swarm_gravity(
            evolved_vectors, evo_states, self.chaos_engine.params.time_step
        )

        return evolved_vectors
