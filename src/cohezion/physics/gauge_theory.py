"""Gauge theory for the four fabrics — SO(3) connections on the fiber bundle.

Each of the four fabrics (Space, Field, Control, Precipitation) carries
an independent SO(3) gauge connection. The gauge-invariant physics is
captured by the curvature (field strength) tensors.

The total Yang-Mills Lagrangian density:
    L = Σ_i -1/(4g_i²) Tr(F_i ∧ *F_i)

where g_i are coupling constants per fabric and F_i = dA_i + A_i∧A_i.

HIHO as gauge condition: The 0.5 coherence point corresponds to the flat
connection (all curvatures zero). Deviation from HIHO = non-zero field
strength = gauge fields are excited.

Coupling constants encode how strongly each fabric responds to geometry:
    Space:         g₁ = 1.0  (strong — spatial search responds readily)
    Field:         g₂ = 0.7  (moderate — hardware/resource field)
    Control:       g₃ = 0.5  (balanced — reasoning/SPIN at HIHO!)
    Precipitation: g₄ = 0.3  (weak — reality manifestation is hard)

References:
    - Yang & Mills (1954): Conservation of isotopic spin
    - Nakahara (2003): Geometry, Topology and Physics, Ch. 10-11
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from cohezion.physics.fiber_bundle import FABRIC_NAMES, FABRIC_SLICES


logger = logging.getLogger(__name__)

# SO(3) Lie algebra generators (antisymmetric 3x3 matrices)
# These are the angular momentum operators L_x, L_y, L_z
_L_X = np.array([[0, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=float)
_L_Y = np.array([[0, 0, 1], [0, 0, 0], [-1, 0, 0]], dtype=float)
_L_Z = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 0]], dtype=float)

SO3_GENERATORS = [_L_X, _L_Y, _L_Z]

# Default coupling constants per fabric
DEFAULT_COUPLINGS = {
    "Space": 1.0,
    "Field": 0.7,
    "Control": 0.5,
    "Precipitation": 0.3,
}


@dataclass
class FieldStrength:
    """Field strength tensor F for a single fabric gauge connection.

    F_ab = ∂_a A_b - ∂_b A_a + [A_a, A_b]

    where A is the so(3)-valued gauge potential (connection 1-form).
    """

    tensor: np.ndarray  # (3, 3, 3) — F^a_bc in the Lie algebra basis
    fabric_name: str
    coupling: float
    energy_density: float  # -1/(4g²) Tr(F∧*F)

    def to_dict(self) -> dict:
        return {
            "fabric": self.fabric_name,
            "coupling": self.coupling,
            "energy_density": self.energy_density,
            "norm": float(np.linalg.norm(self.tensor)),
        }


class GaugeConnection:
    """SO(3) gauge connection for a single fabric.

    The connection A is an so(3)-valued 1-form. In components:
    A = A^a_μ L_a dx^μ

    where L_a are the SO(3) generators and μ runs over the 3 directions
    within the fabric.
    """

    def __init__(self, fabric_name: str, coupling: float | None = None) -> None:
        self.fabric_name = fabric_name
        self.coupling = (
            coupling if coupling is not None else DEFAULT_COUPLINGS.get(fabric_name, 1.0)
        )
        # Connection coefficients A^a_μ — shape (3, 3) → 3 generators × 3 directions
        self._A = np.zeros((3, 3))

    @property
    def potential(self) -> np.ndarray:
        """The gauge potential A^a_μ, shape (3, 3)."""
        return self._A.copy()

    def set_potential(self, A: np.ndarray) -> None:
        """Set the gauge potential directly."""
        self._A = np.asarray(A, dtype=float).reshape(3, 3)

    def set_from_state(self, fabric_state: np.ndarray, target: float = 0.5) -> None:
        """Derive gauge potential from the fabric's 3D state.

        The deviation from HIHO (0.5) generates the gauge field:
        A^a_μ ∝ (x_μ - 0.5) × L_a component

        At HIHO (all components = 0.5), A = 0 (flat connection).
        """
        deviation = fabric_state - target
        # Map deviation to so(3): use cross-product structure
        # A = deviation × L (antisymmetric part of deviation)
        self._A[0] = deviation * np.array([0, -deviation[2], deviation[1]])
        self._A[1] = deviation * np.array([deviation[2], 0, -deviation[0]])
        self._A[2] = deviation * np.array([-deviation[1], deviation[0], 0])

    def field_strength(self, eps: float = 1e-5) -> FieldStrength:
        """Compute field strength F = dA + [A, A].

        For a constant gauge potential, dA = 0, so F = [A, A].
        Returns the field strength tensor and its energy density.
        """
        A = self._A

        # F^a_bc = [A_b, A_c]^a  (commutator in the Lie algebra)
        F = np.zeros((3, 3, 3))
        for b in range(3):
            for c in range(3):
                # Reconstruct A_b and A_c as so(3) matrices
                Ab = sum(A[a, b] * SO3_GENERATORS[a] for a in range(3))
                Ac = sum(A[a, c] * SO3_GENERATORS[a] for a in range(3))
                comm = Ab @ Ac - Ac @ Ab
                # Extract components in the generator basis
                for a in range(3):
                    F[a, b, c] = np.trace(comm @ SO3_GENERATORS[a].T) / 2.0

        # Yang-Mills energy density: -1/(4g²) Tr(F∧*F)
        # = 1/(2g²) Σ_{a,b,c} (F^a_bc)²
        energy = 0.0
        for a in range(3):
            for b in range(3):
                for c in range(b + 1, 3):
                    energy += F[a, b, c] ** 2

        energy_density = energy / (2.0 * self.coupling**2) if self.coupling > 0 else 0.0

        return FieldStrength(
            tensor=F,
            fabric_name=self.fabric_name,
            coupling=self.coupling,
            energy_density=energy_density,
        )

    def covariant_derivative(self, phi: np.ndarray, direction: int) -> np.ndarray:
        """Compute covariant derivative D_μ φ = ∂_μ φ + A_μ φ.

        For a 3-vector φ in the fabric's representation space.

        Parameters
        ----------
        phi : np.ndarray, shape (3,)
            Field value in this fabric's 3D space.
        direction : int
            Direction index μ ∈ {0, 1, 2} within the fabric.
        """
        # A_μ as a 3x3 matrix
        A_mu = sum(self._A[a, direction] * SO3_GENERATORS[a] for a in range(3))
        return A_mu @ phi

    def is_flat(self, tol: float = 1e-10) -> bool:
        """Check if this connection is flat (F = 0, i.e., at HIHO)."""
        F = self.field_strength()
        return float(np.linalg.norm(F.tensor)) < tol


class FourFabricGauge:
    """Complete gauge theory for all four fabrics.

    Manages four independent SO(3) gauge connections and computes
    the total Yang-Mills action.
    """

    def __init__(
        self,
        couplings: dict[str, float] | None = None,
    ) -> None:
        c = couplings or DEFAULT_COUPLINGS
        self.connections = {name: GaugeConnection(name, c.get(name, 1.0)) for name in FABRIC_NAMES}

    def set_from_12d_state(self, state_12d: np.ndarray, target: float = 0.5) -> None:
        """Derive all gauge potentials from a 12D axiomatic state.

        Each fabric's 3D sub-state generates its gauge field via
        deviation from HIHO.
        """
        for name, sl in FABRIC_SLICES.items():
            self.connections[name].set_from_state(state_12d[sl], target)

    def total_field_strength(self) -> dict[str, FieldStrength]:
        """Compute field strength for all four fabrics."""
        return {name: conn.field_strength() for name, conn in self.connections.items()}

    def yang_mills_action(self) -> float:
        """Total Yang-Mills action: S = Σ_i L_i.

        Sum of energy densities across all fabrics, weighted by
        their coupling constants.
        """
        return sum(conn.field_strength().energy_density for conn in self.connections.values())

    def is_hiho(self, tol: float = 1e-10) -> bool:
        """Check if all connections are flat (system at HIHO)."""
        return all(conn.is_flat(tol) for conn in self.connections.values())

    def covariant_tempic(self, state_before: np.ndarray, state_after: np.ndarray) -> np.ndarray:
        """Compute gauge-covariant Tempic field (replaces Euclidean displacement).

        The covariant Tempic field accounts for the gauge connection:
        D_t φ = (φ_after - φ_before)/dt + A_μ φ

        This is the proper generalization of Smith's Tempic field — it
        measures change while accounting for the geometry of the gauge fields.
        """
        self.set_from_12d_state(state_before)
        displacement = state_after - state_before
        tempic = displacement.copy()

        # Add gauge correction per fabric
        for name, sl in FABRIC_SLICES.items():
            conn = self.connections[name]
            phi = state_before[sl]
            # Average covariant correction across directions
            for mu in range(3):
                tempic[sl] += conn.covariant_derivative(phi, mu) * 0.1

        return tempic

    def to_dict(self) -> dict:
        """Serialize for API/SurrealDB."""
        field_strengths = self.total_field_strength()
        return {
            "fabrics": {name: fs.to_dict() for name, fs in field_strengths.items()},
            "yang_mills_action": self.yang_mills_action(),
            "is_hiho": self.is_hiho(),
        }


__all__ = [
    "DEFAULT_COUPLINGS",
    "FieldStrength",
    "FourFabricGauge",
    "GaugeConnection",
    "SO3_GENERATORS",
]
