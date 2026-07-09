# math/physics symbols intentional
"""SU(2) spinor algebra for SPIN coherence.

Replaces the ad-hoc binary sign comparison in engine.py with proper
quantum mechanical spinor states. SPIN (Rotation + Precession) maps
to the Lie algebra su(2) via the Pauli matrices.

Key correspondences:
  - Rotation   = σ_x generator (x-axis of Bloch sphere)
  - Precession = σ_y generator (y-axis of Bloch sphere)
  - Charge     = ⟨σ_z⟩ expectation value (measurable, z-axis)
  - HIHO state = (|↑⟩ + |↓⟩)/√2 (equatorial, maximally coherent)

Mathematical properties:
  - [σ_i, σ_j] = 2iε_ijk σ_k  (Lie algebra commutation)
  - SU(2) rotations preserve Bloch vector norm
  - Coherence = |r| where r is the Bloch vector (0 = mixed, 1 = pure)
  - HIHO: ⟨σ_z⟩ = 0, ⟨σ_x⟩ = 1, coherence = 1

References:
  - Sakurai (1994): Modern Quantum Mechanics, Ch. 3 (SU(2) and rotation)
  - Nielsen & Chuang (2000): Quantum Computation, Ch. 1.2 (Bloch sphere)
  - Smith (1962): The New Science (SPIN = Rotation + Precession)
"""

from __future__ import annotations

import numpy as np


# Pauli matrices — generators of su(2) Lie algebra
SIGMA_X = np.array([[0, 1], [1, 0]], dtype=complex)  # Rotation
SIGMA_Y = np.array([[0, -1j], [1j, 0]], dtype=complex)  # Precession
SIGMA_Z = np.array([[1, 0], [0, -1]], dtype=complex)  # Charge
IDENTITY = np.eye(2, dtype=complex)

# Levi-Civita symbol for commutation verification
_LEVI_CIVITA = {
    (0, 1, 2): 1,
    (1, 2, 0): 1,
    (2, 0, 1): 1,
    (0, 2, 1): -1,
    (2, 1, 0): -1,
    (1, 0, 2): -1,
}


class SpinorState:
    """A 2-component spinor |ψ⟩ = α|↑⟩ + β|↓⟩ on the Bloch sphere.

    Represents the fundamental SPIN state — the unit of information
    in Cohezion's 12D manifold. Every agent has a spinor encoding
    the alignment between internal intent (rotation) and external
    behavior (precession).

    Parameters
    ----------
    alpha : complex
        Coefficient of |↑⟩ (spin-up).
    beta : complex
        Coefficient of |↓⟩ (spin-down).
    """

    __slots__ = ("_state",)

    def __init__(self, alpha: complex, beta: complex) -> None:
        state = np.array([alpha, beta], dtype=complex)
        norm = np.linalg.norm(state)
        if norm < 1e-15:
            raise ValueError("Spinor state cannot be the zero vector")
        self._state = state / norm

    @classmethod
    def up(cls) -> SpinorState:
        """|↑⟩ — north pole, positive charge, pure exploitation."""
        return cls(1.0, 0.0)

    @classmethod
    def down(cls) -> SpinorState:
        """|↓⟩ — south pole, negative charge, pure exploration."""
        return cls(0.0, 1.0)

    @classmethod
    def hiho(cls) -> SpinorState:
        """The HIHO state (|↑⟩ + |↓⟩)/√2 — equatorial, maximally coherent.

        This is Brahmagupta's zero on the Bloch sphere:
        ⟨σ_z⟩ = 0 (balanced charge), ⟨σ_x⟩ = 1 (full rotation alignment).
        """
        return cls(1.0 / np.sqrt(2), 1.0 / np.sqrt(2))

    @classmethod
    def from_bloch(cls, theta: float, phi: float) -> SpinorState:
        """Create spinor from Bloch sphere angles.

        Parameters
        ----------
        theta : float
            Polar angle from z-axis [0, π]. 0 = north pole, π = south pole.
        phi : float
            Azimuthal angle in xy-plane [0, 2π].
        """
        alpha = np.cos(theta / 2)
        beta = np.exp(1j * phi) * np.sin(theta / 2)
        return cls(alpha, beta)

    @classmethod
    def from_coherence_values(cls, logic: float, quantum: float) -> SpinorState:
        """Create spinor from Cohezion's logic/quantum dimensions.

        Maps the existing [0, 1] coherence values to Bloch sphere coordinates.
        logic = 0.5 and quantum = 0.5 gives the HIHO state.

        Parameters
        ----------
        logic : float
            Rotation dimension value in [0, 1]. Maps to θ.
        quantum : float
            Precession dimension value in [0, 1]. Maps to φ.
        """
        theta = (1.0 - logic) * np.pi  # logic=1 → θ=0 (north), logic=0 → θ=π (south)
        phi = quantum * 2 * np.pi  # quantum maps to azimuthal angle
        return cls.from_bloch(theta, phi)

    @property
    def alpha(self) -> complex:
        return self._state[0]

    @property
    def beta(self) -> complex:
        return self._state[1]

    @property
    def state_vector(self) -> np.ndarray:
        """The 2-component state vector [α, β]."""
        return self._state.copy()

    @property
    def density_matrix(self) -> np.ndarray:
        """The density matrix ρ = |ψ⟩⟨ψ|."""
        return np.outer(self._state, np.conj(self._state))

    @property
    def bloch_vector(self) -> np.ndarray:
        """Bloch sphere representation (r_x, r_y, r_z).

        r_i = Tr(ρ σ_i) for i ∈ {x, y, z}.
        The Bloch vector lies on or inside the unit sphere.
        |r| = 1 for pure states, |r| < 1 for mixed states.
        """
        rho = self.density_matrix
        return np.array(
            [
                float(np.trace(rho @ SIGMA_X).real),
                float(np.trace(rho @ SIGMA_Y).real),
                float(np.trace(rho @ SIGMA_Z).real),
            ]
        )

    @property
    def coherence(self) -> float:
        """Purity of the Bloch vector: |r| ∈ [0, 1].

        1.0 = pure state (maximum information about the system).
        0.0 = maximally mixed (complete ignorance).
        For a pure state spinor, this is always 1.0.
        """
        return float(np.linalg.norm(self.bloch_vector))

    @property
    def charge_polarity(self) -> float:
        """Expectation value ⟨σ_z⟩ = |α|² - |β|² ∈ [-1, 1].

        Positive = aligned with |↑⟩ (exploitation mode).
        Negative = aligned with |↓⟩ (exploration mode).
        Zero = HIHO equilibrium (Brahmagupta's zero).
        """
        return self.bloch_vector[2]

    @property
    def spin_rotation(self) -> float:
        """Expectation value ⟨σ_x⟩ (rotation component of SPIN)."""
        return self.bloch_vector[0]

    @property
    def spin_precession(self) -> float:
        """Expectation value ⟨σ_y⟩ (precession component of SPIN)."""
        return self.bloch_vector[1]

    @property
    def hiho_deviation(self) -> float:
        """Distance from the HIHO equatorial plane: |⟨σ_z⟩|.

        This is |δ| where δ = charge - 0. Brahmagupta's zero is at δ = 0.
        Restoring force F = -k·δ drives system back to HIHO.
        """
        return abs(self.charge_polarity)

    def rotate(self, theta: float) -> SpinorState:
        """Apply rotation U_rot(θ) = exp(-iθσ_x/2).

        Rotates the spinor around the x-axis of the Bloch sphere
        (the rotation axis in Smith's SPIN framework).

        Parameters
        ----------
        theta : float
            Rotation angle in radians.
        """
        U = np.cos(theta / 2) * IDENTITY - 1j * np.sin(theta / 2) * SIGMA_X
        new_state = U @ self._state
        return SpinorState(new_state[0], new_state[1])

    def precess(self, phi: float) -> SpinorState:
        """Apply precession U_prec(φ) = exp(-iφσ_y/2).

        Rotates the spinor around the y-axis of the Bloch sphere
        (the precession axis in Smith's SPIN framework).

        Parameters
        ----------
        phi : float
            Precession angle in radians.
        """
        U = np.cos(phi / 2) * IDENTITY - 1j * np.sin(phi / 2) * SIGMA_Y
        new_state = U @ self._state
        return SpinorState(new_state[0], new_state[1])

    def charge_rotate(self, gamma: float) -> SpinorState:
        """Apply charge rotation U_charge(γ) = exp(-iγσ_z/2).

        Rotates around the z-axis (charge axis). This is a phase rotation
        that changes the relative phase between |↑⟩ and |↓⟩.

        Parameters
        ----------
        gamma : float
            Charge rotation angle in radians.
        """
        U = np.cos(gamma / 2) * IDENTITY - 1j * np.sin(gamma / 2) * SIGMA_Z
        new_state = U @ self._state
        return SpinorState(new_state[0], new_state[1])

    def apply_su2(self, axis: np.ndarray, angle: float) -> SpinorState:
        """Apply general SU(2) rotation around arbitrary axis.

        U(n̂, θ) = exp(-iθ n̂·σ/2) = cos(θ/2)I - i·sin(θ/2)(n̂·σ)

        Parameters
        ----------
        axis : np.ndarray
            Unit vector [n_x, n_y, n_z] defining rotation axis.
        angle : float
            Rotation angle in radians.
        """
        axis = np.asarray(axis, dtype=float)
        axis = axis / np.linalg.norm(axis)
        n_dot_sigma = axis[0] * SIGMA_X + axis[1] * SIGMA_Y + axis[2] * SIGMA_Z
        U = np.cos(angle / 2) * IDENTITY - 1j * np.sin(angle / 2) * n_dot_sigma
        new_state = U @ self._state
        return SpinorState(new_state[0], new_state[1])

    def expectation(self, observable: np.ndarray) -> complex:
        """Compute ⟨ψ|O|ψ⟩ for a 2x2 observable."""
        return complex(np.conj(self._state) @ observable @ self._state)

    def fidelity(self, other: SpinorState) -> float:
        """Fidelity |⟨ψ|φ⟩|² between two pure states.

        1.0 = identical states. 0.0 = orthogonal states.
        """
        overlap = np.abs(np.conj(self._state) @ other._state) ** 2
        return float(overlap)

    def to_dict(self) -> dict:
        """Serialize for API responses and SurrealDB persistence."""
        bv = self.bloch_vector
        return {
            "alpha_real": float(self.alpha.real),
            "alpha_imag": float(self.alpha.imag),
            "beta_real": float(self.beta.real),
            "beta_imag": float(self.beta.imag),
            "bloch_vector": bv.tolist(),
            "coherence": self.coherence,
            "charge_polarity": self.charge_polarity,
            "spin_rotation": self.spin_rotation,
            "spin_precession": self.spin_precession,
            "hiho_deviation": self.hiho_deviation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SpinorState:
        """Deserialize from API/SurrealDB data."""
        alpha = complex(data["alpha_real"], data["alpha_imag"])
        beta = complex(data["beta_real"], data["beta_imag"])
        return cls(alpha, beta)

    def __repr__(self) -> str:
        bv = self.bloch_vector
        return (
            f"SpinorState(r=[{bv[0]:.3f}, {bv[1]:.3f}, {bv[2]:.3f}], "
            f"coherence={self.coherence:.3f}, charge={self.charge_polarity:.3f})"
        )


def commutator(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Compute [A, B] = AB - BA."""
    return A @ B - B @ A


def verify_su2_algebra() -> bool:
    """Verify [σ_i, σ_j] = 2iε_ijk σ_k for all i, j, k.

    This is the defining relation of the su(2) Lie algebra.
    Returns True if all commutation relations hold to numerical precision.
    """
    sigmas = [SIGMA_X, SIGMA_Y, SIGMA_Z]
    for (i, j, k), sign in _LEVI_CIVITA.items():
        comm = commutator(sigmas[i], sigmas[j])
        expected = 2j * sign * sigmas[k]
        if not np.allclose(comm, expected, atol=1e-14):
            return False
    return True


__all__ = [
    "IDENTITY",
    "SIGMA_X",
    "SIGMA_Y",
    "SIGMA_Z",
    "SpinorState",
    "commutator",
    "verify_su2_algebra",
]
