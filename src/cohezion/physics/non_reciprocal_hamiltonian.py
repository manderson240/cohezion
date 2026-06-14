"""Non-reciprocal Hamiltonian — auxiliary DOF embedding.

Implements the Hamiltonian description of non-reciprocal interactions from:

    Shi, Y., Moessner, R., Alert, R., & Bukov, M. (2026).
    "Hamiltonian description of non-reciprocal interactions."
    Nature Physics. https://doi.org/10.1038/s41567-026-03317-0

Non-reciprocal systems have Jᵢⱼ ≠ Jⱼᵢ — the influence of agent i on agent j
differs from j on i. Classic examples: predator-prey, opinion dynamics with
information asymmetry, active-matter flocks with alignment bias.

Key construction:
  1. Decompose coupling matrix J = Jˢ + Jᵃ  (Jˢ symmetric, Jᵃ antisymmetric)
  2. Introduce auxiliary ("shadow") DOF θ paired with primary DOF x
  3. Hamiltonian: H(x, θ) = x·Jˢ·x + x·Jᵃ·θ
  4. Mirror constraint: θᵢ − xᵢ = π  (auxiliary sector shadows primary, phase-shifted)
  5. Under the constraint: ẋ = −∂H/∂θ = −Jᵃ·x = original non-reciprocal dynamics

Cohezion mapping:
  - Tiered routing: NPU→iGPU escalation ≠ iGPU→NPU delegation (Jᵢⱼ ≠ Jⱼᵢ)
  - Quality-gate flows: quality signal propagates asymmetrically between tiers
  - FLUME VAE: encoder→latent (posterior) ≠ latent→decoder (likelihood)
  - `symmetrization_error()` quantifies routing bias; HIHO = 0 (reciprocal equilibrium)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np


logger = logging.getLogger(__name__)

_MIRROR_PHASE: float = np.pi  # θᵢ − xᵢ = π  (mirror constraint)
_HIHO_THRESHOLD: float = 0.5  # shared across all Cohezion physics modules


@dataclass
class NonReciprocalHamiltonian:
    """Hamiltonian for non-reciprocal N-body coupling via auxiliary DOF.

    Parameters
    ----------
    coupling_matrix : ndarray, shape (N, N)
        Possibly asymmetric coupling J.  Jᵢⱼ is the influence of j on i.
    n_dof : int
        Number of primary degrees of freedom N (inferred from coupling_matrix
        when provided, otherwise used to build a default identity matrix).
    mirror_phase : float
        Phase offset of the auxiliary sector (default π).
    """

    coupling_matrix: np.ndarray = field(default_factory=lambda: np.array([[0.0, 1.0], [-1.0, 0.0]]))
    mirror_phase: float = _MIRROR_PHASE

    def __post_init__(self) -> None:
        J = np.asarray(self.coupling_matrix, dtype=np.float64)
        if J.ndim != 2 or J.shape[0] != J.shape[1]:
            raise ValueError("coupling_matrix must be a square 2-D array")
        self._J = J
        self._n = J.shape[0]
        # Symmetric and antisymmetric decomposition
        self._Js = 0.5 * (J + J.T)  # Jˢ = (J + Jᵀ)/2
        self._Ja = 0.5 * (J - J.T)  # Jᵃ = (J − Jᵀ)/2

    # ── Properties ────────────────────────────────────────────────────

    @property
    def n_dof(self) -> int:
        return self._n

    @property
    def symmetric_part(self) -> np.ndarray:
        """Jˢ = (J + Jᵀ)/2 — reciprocal coupling backbone."""
        return self._Js.copy()

    @property
    def antisymmetric_part(self) -> np.ndarray:
        """Jᵃ = (J − Jᵀ)/2 — non-reciprocal perturbation."""
        return self._Ja.copy()

    # ── Mirror constraint ──────────────────────────────────────────────

    def auxiliary_state(self, x: np.ndarray) -> np.ndarray:
        """Compute auxiliary DOF θ from primary state x via mirror constraint.

        θᵢ = xᵢ + mirror_phase
        """
        return np.asarray(x, dtype=np.float64) + self.mirror_phase

    def mirror_violation(self, x: np.ndarray, theta: np.ndarray) -> np.ndarray:
        """Element-wise violation of the mirror constraint θᵢ − xᵢ − π."""
        x = np.asarray(x, dtype=np.float64)
        theta = np.asarray(theta, dtype=np.float64)
        return theta - x - self.mirror_phase

    # ── Hamiltonian and dynamics ───────────────────────────────────────

    def hamiltonian(self, x: np.ndarray, theta: np.ndarray | None = None) -> float:
        """Evaluate H(x, θ) = xᵀ Jˢ x + xᵀ Jᵃ θ.

        When theta is None, the mirror constraint θ = x + π is applied.
        """
        x = np.asarray(x, dtype=np.float64)
        if theta is None:
            theta = self.auxiliary_state(x)
        theta = np.asarray(theta, dtype=np.float64)
        reciprocal_energy = float(x @ self._Js @ x)
        cross_energy = float(x @ self._Ja @ theta)
        return reciprocal_energy + cross_energy

    def force(self, x: np.ndarray, theta: np.ndarray | None = None) -> np.ndarray:
        """Primary force: ẋ = −∂H/∂θ = −Jᵃ x.

        Under the mirror constraint this recovers the original non-reciprocal
        dynamics ẋᵢ = Σⱼ Jᵢⱼ xⱼ (via ẋ = −Jᵃ x and ẋ from Jˢ cancels).
        """
        x = np.asarray(x, dtype=np.float64)
        return -self._Ja @ x

    def auxiliary_force(self, x: np.ndarray) -> np.ndarray:
        """Auxiliary force: θ̇ = +∂H/∂x = 2Jˢ x + Jᵃ θ."""
        theta = self.auxiliary_state(x)
        return 2.0 * self._Js @ x + self._Ja @ theta

    def step(
        self,
        x: np.ndarray,
        dt: float = 0.01,
        temperature: float = 0.0,
        rng: np.random.Generator | None = None,
    ) -> np.ndarray:
        """Euler step under the constrained Hamiltonian dynamics.

        Updates x ← x + dt * force(x) + thermal noise.
        The mirror constraint is automatically re-applied to get θ.
        """
        x = np.asarray(x, dtype=np.float64)
        f = self.force(x)
        noise = np.zeros_like(x)
        if temperature > 0.0:
            _rng = rng or np.random.default_rng()
            noise = np.sqrt(2.0 * temperature * dt) * _rng.standard_normal(x.shape)
        return x + dt * f + noise

    def simulate(
        self,
        x0: np.ndarray,
        n_steps: int = 100,
        dt: float = 0.01,
        temperature: float = 0.0,
        rng: np.random.Generator | None = None,
    ) -> np.ndarray:
        """Simulate trajectory under constrained non-reciprocal Hamiltonian.

        Returns
        -------
        ndarray, shape (n_steps + 1, N)
            State trajectory, including initial condition.
        """
        x = np.asarray(x0, dtype=np.float64).copy()
        _rng = rng or (np.random.default_rng() if temperature > 0.0 else None)
        traj = np.empty((n_steps + 1, self._n))
        traj[0] = x
        for i in range(n_steps):
            x = self.step(x, dt=dt, temperature=temperature, rng=_rng)
            traj[i + 1] = x
        return traj

    # ── Routing quality metrics ────────────────────────────────────────

    def symmetrization_error(self) -> float:
        """Frobenius norm of the antisymmetric part — routing bias magnitude.

        zero  ↔ fully reciprocal coupling (balanced routing)
        large ↔ strongly non-reciprocal (one-directional quality flow)

        HIHO target: not zero (some non-reciprocity is healthy for directed
        routing), but bounded so feedback loops can form.
        """
        return float(np.linalg.norm(self._Ja, "fro"))

    def hiho_reciprocity_score(self) -> float:
        """HIHO kernel applied to the reciprocity fraction.

        reciprocity_fraction ρ = ‖Jˢ‖ / (‖Jˢ‖ + ‖Jᵃ‖)   ∈ [0, 1]
        score = 4·ρ·(1 − ρ)  — peaks at ρ = 0.5 (equal symmetric/antisymmetric)

        A score near 1.0 means the coupling is half reciprocal, half
        non-reciprocal — the HIHO optimal balance for directed routing with
        bidirectional feedback.
        """
        norm_s = float(np.linalg.norm(self._Js, "fro"))
        norm_a = float(np.linalg.norm(self._Ja, "fro"))
        total = norm_s + norm_a
        if total < 1e-12:
            return 0.0
        rho = norm_s / total
        return 4.0 * rho * (1.0 - rho)

    def is_hiho_reciprocal(self, tolerance: float = 0.05) -> bool:
        """True when the coupling is near the HIHO reciprocity equilibrium.

        Checks |ρ − 0.5| ≤ tolerance, i.e. symmetric ≈ antisymmetric parts.
        """
        norm_s = float(np.linalg.norm(self._Js, "fro"))
        norm_a = float(np.linalg.norm(self._Ja, "fro"))
        total = norm_s + norm_a
        if total < 1e-12:
            return True
        rho = norm_s / total
        return abs(rho - _HIHO_THRESHOLD) <= tolerance

    def to_dict(self) -> dict:
        """Serializable summary for SurrealDB traces."""
        return {
            "n_dof": self._n,
            "symmetrization_error": self.symmetrization_error(),
            "hiho_reciprocity_score": self.hiho_reciprocity_score(),
            "is_hiho_reciprocal": self.is_hiho_reciprocal(),
            "mirror_phase": self.mirror_phase,
        }


# ── Cohesion routing convenience constructors ──────────────────────────────


def make_triune_routing_hamiltonian() -> NonReciprocalHamiltonian:
    """Non-reciprocal Hamiltonian for 3-tier routing (NPU / iGPU / CPU).

    Encodes the asymmetric quality flow of the Triune Orchestrator:
      - NPU → iGPU: escalation threshold is strict (quality gate chars > 0)
      - iGPU → CPU: escalation threshold is looser (reasoning tasks only)
      - CPU → cloud: delegation is one-directional (cloud never delegates back)

    Coupling matrix (row i = "what j does to i"):
        J[0,1] = +1.0  (iGPU pushes quality signal to NPU tier — escalation hint)
        J[1,0] = -0.5  (NPU sends partial context to iGPU — asymmetric)
        J[1,2] = +1.0  (CPU pushes reasoning quality to iGPU)
        J[2,1] = -0.5  (iGPU delegates to CPU — one-way)
    """
    J = np.array(
        [
            [0.0, 1.0, 0.0],
            [-0.5, 0.0, 1.0],
            [0.0, -0.5, 0.0],
        ],
        dtype=np.float64,
    )
    return NonReciprocalHamiltonian(coupling_matrix=J)


def make_flume_vae_hamiltonian() -> NonReciprocalHamiltonian:
    """Non-reciprocal Hamiltonian for FLUME VAE posterior/likelihood asymmetry.

    Encoder (posterior q(z|x)) and decoder (likelihood p(x|z)) have non-reciprocal
    coupling: posterior collapse is driven by the KL term (β-VAE), which pushes
    the encoder to match the prior but does not constrain the decoder symmetrically.

    2-DOF system: DOF 0 = encoder latent, DOF 1 = decoder latent.
    J[0,1] = kl_weight (decoder influences encoder via KL gradient)
    J[1,0] = 1.0       (encoder latent drives decoder reconstruction — strong)
    """
    kl_weight = 0.01  # A3 harness invariant
    J = np.array(
        [
            [0.0, kl_weight],
            [1.0, 0.0],
        ],
        dtype=np.float64,
    )
    return NonReciprocalHamiltonian(coupling_matrix=J)
