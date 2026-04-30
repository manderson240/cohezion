"""HIHO Unified Engine - advanced physics components.

Contains: SacredGeometry, Twistor, QuantumEmergence, Bioelectrics, Esoteric,
KordylewskiSwarm, and PlasmaMCPEngine.
"""

from __future__ import annotations

import logging
from typing import Any, cast, TYPE_CHECKING

import httpx
import numpy as np

from cohezion.reliability import get_circuit


if TYPE_CHECKING:
    from .components import EvoState


logger = logging.getLogger(__name__)


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
        dist = float((np.sqrt(x**2 + y**2) - major_r) ** 2 + z**2 - minor_r**2)
        return float(np.exp(-np.abs(dist)))


class PenroseTwistorEngine:
    """Bridges quantum semantic states to spacetime geometry using Twistor space."""

    def apply_twistor_mapping(self, latent_vector: np.ndarray) -> np.ndarray:
        """Map 4D spacetime components to Twistor space C4 (simplified)."""
        vec = latent_vector.copy()
        if vec.shape[0] >= 4:
            omega_0, omega_1 = vec[0].copy(), vec[1].copy()
            pi_0, pi_1 = vec[2].copy(), vec[3].copy()

            vec[0] = omega_0 * np.cos(0.5) - pi_0 * np.sin(0.5)
            vec[2] = omega_0 * np.sin(0.5) + pi_0 * np.cos(0.5)
            vec[1] = omega_1 * np.cos(0.5) + pi_1 * np.sin(0.5)
            vec[3] = -omega_1 * np.sin(0.5) + pi_1 * np.cos(0.5)

        return vec


class QuantumEmergenceEngine:
    """Unifies ER=EPR, Planck/Bohr quantization, and Chirality within the semantic manifold."""

    def apply_quantum_effects(self, latent_vector: np.ndarray, chirality: float) -> np.ndarray:
        vec = latent_vector.copy()
        vec = np.round(vec * 10.0) / 10.0

        theta = chirality * np.pi / 4.0
        c, s = np.cos(theta), np.sin(theta)

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
        morpho_strength = float(np.tanh(coherence))

        if tensor_beam is not None and len(tensor_beam) > 0:
            attractor = np.zeros_like(vec)
            for i in range(min(len(attractor), len(tensor_beam))):
                attractor[i] = tensor_beam[i]
            norm = float(np.linalg.norm(attractor))
            if norm > 0:
                attractor = attractor / norm
        else:
            attractor = np.ones_like(vec)

        vec = vec * (1.0 - morpho_strength * 0.1) + attractor * (morpho_strength * 0.1)
        return vec


class EsotericPhysicsEngine:
    """Integrates Percival's Triune Self (Doer, Thinker, Knower) and Bailey's Cosmic Fire."""

    def apply_triune_self(self, latent_vector: np.ndarray) -> np.ndarray:
        """Maps latent dims to Doer (Action), Thinker (Logic), Knower (Wisdom)."""
        vec = latent_vector.copy()

        if len(vec) >= 3:
            vec[0] *= 1.05  # Cosmic Fire (Will/Action) energizes the Doer
            vec[1] *= 1.02  # Thinker dimension
            vec[2] *= 1.01  # Knower dimension (Wisdom/Synthesis)

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

        center_of_mass = np.mean(latent_vectors, axis=0)

        evolved_vectors = []
        for i, vec in enumerate(latent_vectors):
            v_copy = vec.copy()

            vec_to_com = center_of_mass - v_copy
            distance = float(np.linalg.norm(vec_to_com))

            if distance > 1e-4 and len(v_copy) >= 2:
                theta_l4 = np.pi / 3.0
                theta_l5 = -np.pi / 3.0

                helicity = (
                    evo_states[i].magnetic_helicity if (evo_states and i < len(evo_states)) else 0.0
                )
                theta = theta_l4 if helicity >= 0 else theta_l5

                c, s = float(np.cos(theta)), float(np.sin(theta))

                L_point = np.zeros_like(v_copy)
                L_point[0] = center_of_mass[0] - (vec_to_com[0] * c - vec_to_com[1] * s)
                L_point[1] = center_of_mass[1] - (vec_to_com[0] * s + vec_to_com[1] * c)
                for j in range(2, len(L_point)):
                    L_point[j] = center_of_mass[j] - vec_to_com[j]

                pull_strength = 0.5 * dt
                v_copy += (L_point - v_copy) * pull_strength

                if helicity >= 0:
                    self.memory_cloud_l4.append(v_copy.copy())
                else:
                    self.memory_cloud_l5.append(v_copy.copy())

            evolved_vectors.append(v_copy)

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
                    f"{self.base_url}/plasma_create_simulation", json={"grid_size": 128}
                )
                resp.raise_for_status()
                data = resp.json()
                if "simulation_id" in data:
                    self.simulation_id = data["simulation_id"]
                self.circuit.record_success()
                logger.info("Initialized Plasma MCP simulation: %s", self.simulation_id)
            except Exception as e:
                self.circuit.record_failure()
                logger.warning("Failed to initialize Plasma MCP: %s", e)

    async def step(self) -> None:
        """Advance the plasma simulation."""
        if not self.simulation_id or not self.circuit.allow_request():
            return

        async with httpx.AsyncClient(timeout=2.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/plasma_step",
                    json={"simulation_id": self.simulation_id, "steps": 1},
                )
                resp.raise_for_status()
                self.circuit.record_success()
            except Exception as e:
                self.circuit.record_failure()
                logger.warning("Failed to step Plasma MCP: %s", e)

    async def get_exotic_objects(self) -> list[dict[str, Any]]:
        """Fetch exotic vacuum objects for mapping to agent states."""
        if not self.simulation_id or not self.circuit.allow_request():
            return []

        async with httpx.AsyncClient(timeout=2.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/plasma_get_exotic_objects",
                    json={"simulation_id": self.simulation_id},
                )
                resp.raise_for_status()
                self.circuit.record_success()
                data = resp.json()
                return cast("list[dict[str, Any]]", data.get("objects", []))
            except Exception as e:
                self.circuit.record_failure()
                logger.warning("Failed to fetch exotic objects from Plasma MCP: %s", e)
                return []
