"""HIHO Unified Engine - basic physics components.

Contains: CellularAutomata, ChaosTheory, EvoState, MHD, HIHOStabilization engines.
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, Field


try:
    import cohezion_physics_core  # type: ignore[import-untyped]

    RUST_CORE_AVAILABLE = True
except ImportError:
    RUST_CORE_AVAILABLE = False


# --- Cellular Automata ---


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

        for i in range(n):
            left = current[(i - 1) % n]
            center = current[i]
            right = current[(i + 1) % n]
            next_state[i] = patterns[(left, center, right)]

        self.config.state = next_state
        return next_state


# --- Chaos Theory ---


class ChaosTheoryParameters(BaseModel):
    """Parameters for Chaos Theory semantic butterfly effects."""

    lyapunov_exponent: float = Field(default=0.9, description="Lyapunov exponent (λ > 0 implies chaos)")
    sensitivity: float = Field(default=1e-5, description="Initial perturbation size")
    time_step: float = Field(default=0.01, description="Evolution time step")


class ChaosTheoryEngine:
    """Computes semantic butterfly effects via chaotic divergence."""

    def __init__(self, params: ChaosTheoryParameters):
        self.params = params

    def compute_divergence(self, delta_t: float) -> float:
        """Calculate the exponential divergence over time delta_t."""
        divergence = self.params.sensitivity * np.exp(self.params.lyapunov_exponent * delta_t)
        return float(divergence)

    def apply_butterfly_effect(self, latent_vector: np.ndarray, t: float) -> np.ndarray:
        """Apply a chaotic perturbation to a latent vector based on time t."""
        divergence = self.compute_divergence(t)
        noise = np.random.randn(*latent_vector.shape) * divergence
        return latent_vector + noise


# --- EVO State and MHD ---


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
            cohezion_physics_core.apply_mhd_forces_simd(vec, evo.magnetic_helicity, evo.toroidal_moment, dt)
            evo.charge_density *= np.exp(-dt * (1.0 - evo.coherence))
            return vec

        twist_angle = evo.magnetic_helicity * dt

        if vec.shape[0] >= 2:
            cos_theta = np.cos(twist_angle)
            sin_theta = np.sin(twist_angle)
            v0, v1 = vec[0].copy(), vec[1].copy()
            vec[0] = v0 * cos_theta - v1 * sin_theta
            vec[1] = v0 * sin_theta + v1 * cos_theta

        current_norm = float(np.linalg.norm(vec))
        if current_norm > 0:
            scale_factor = 1.0 + (evo.toroidal_moment - current_norm) * 0.1 * dt
            vec *= scale_factor

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
            magnetic_helicity=float(np.random.uniform(-0.5, 0.5)),
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

        delta_coherence = 0.5 - evo.coherence
        restoring_force = 2.0 * delta_coherence * dt
        evo.coherence += restoring_force

        if abs(evo.coherence - 0.5) > 0.4:
            vec *= np.exp(-dt * 5.0)

        return evo, vec
