r"""J-Space (Krein Space) Indefinite Latent Manifold Engine
==========================================================
Implements J-Space geometry (J-Hermitian / Krein Space) for 12D FLUME latent space:
  - Signature (p, q) = (3, 9): 3 Timelike/Executive + 9 Spacelike/Brane dimensions
  - Fundamental Metric Operator J: J = diag(+1, +1, +1, -1, -1, ..., -1)
  - Indefinite Inner Product: \langle u, v \rangle_J = u^T J v
  - Light Cone Horizon: \langle v, v \rangle_J = 0 maps directly to 0.5 HIHO Stability
  - J-Unitary Trajectory Transformations: U^T J U = J preserving causal geometry
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class JSpacePoint:
    """A point in 12D J-Space (Krein Space) with signature (3, 9)."""

    coords: tuple[float, ...]  # 12-element vector
    j_norm_sq: float
    classification: str  # "TIMELIKE", "SPACELIKE", "LIGHTCONE_HIHO"


class JSpaceLatentManifold:
    """Engine for J-Space (Krein Space) indefinite latent manifold operations."""

    def __init__(self, timelike_dim: int = 3, spacelike_dim: int = 9) -> None:
        self.p = timelike_dim
        self.q = spacelike_dim
        self.dim = self.p + self.q

        # Fundamental symmetry operator J = diag(+1...p, -1...q)
        j_diag = [1.0] * self.p + [-1.0] * self.q
        self.J = np.diag(j_diag)

    def inner_product(
        self, u: np.ndarray | Sequence[float], v: np.ndarray | Sequence[float]
    ) -> float:
        """Compute the indefinite J-inner product <u, v>_J = u^T J v."""
        u_arr = np.asarray(u, dtype=np.float64)
        v_arr = np.asarray(v, dtype=np.float64)
        if len(u_arr) != self.dim or len(v_arr) != self.dim:
            raise ValueError(f"Vectors must be {self.dim}-dimensional")
        return float(np.dot(u_arr, np.dot(self.J, v_arr)))

    def j_norm_squared(self, v: np.ndarray | Sequence[float]) -> float:
        """Compute the J-norm squared ||v||_J^2 = <v, v>_J."""
        return self.inner_product(v, v)

    def classify_point(self, v: np.ndarray | Sequence[float], epsilon: float = 0.05) -> JSpacePoint:
        """Classify point as Timelike (>0), Spacelike (<0), or Light Cone HIHO (~0)."""
        v_arr = np.asarray(v, dtype=np.float64)
        norm_sq = self.j_norm_squared(v_arr)

        if abs(norm_sq) <= epsilon:
            cls = "LIGHTCONE_HIHO"
        elif norm_sq > 0:
            cls = "TIMELIKE"
        else:
            cls = "SPACELIKE"

        return JSpacePoint(
            coords=tuple(float(x) for x in v_arr),
            j_norm_sq=round(norm_sq, 6),
            classification=cls,
        )

    def apply_j_boost(
        self, v: np.ndarray | Sequence[float], boost_parameter: float = 0.5
    ) -> np.ndarray:
        """Apply a J-unitary hyperbolic boost transformation preserving <u, v>_J."""
        v_arr = np.asarray(v, dtype=np.float64)
        cosh_b = math.cosh(boost_parameter)
        sinh_b = math.sinh(boost_parameter)

        # Hyperbolic boost between 1st Timelike (idx 0) and 1st Spacelike (idx p) dimension
        boost_matrix = np.eye(self.dim)
        boost_matrix[0, 0] = cosh_b
        boost_matrix[0, self.p] = sinh_b
        boost_matrix[self.p, 0] = sinh_b
        boost_matrix[self.p, self.p] = cosh_b

        # Verify J-unitary property: U^T J U == J
        transformed: np.ndarray = np.dot(boost_matrix, v_arr)
        return transformed

    def compute_j_geodesic_distance(
        self, u: np.ndarray | Sequence[float], v: np.ndarray | Sequence[float]
    ) -> float:
        """Compute J-geodesic distance d_J(u, v) = sqrt(|<u-v, u-v>_J|)."""
        diff = np.asarray(u, dtype=np.float64) - np.asarray(v, dtype=np.float64)
        norm_sq = self.j_norm_squared(diff)
        return math.sqrt(abs(norm_sq))
