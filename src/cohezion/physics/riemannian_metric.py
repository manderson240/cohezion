# ruff: noqa: E741, N806  # math/physics: T, F, B, P, S, G, R, A — single-letter conventions
"""Riemannian geometry for the 12D axiomatic manifold.

Provides the metric tensor, Christoffel symbols, geodesic equation,
and curvature for the manifold on which agent trajectories evolve.

The metric tensor g_ij defines:
  - Distances: ds² = g_ij dx^i dx^j
  - Kinetic energy: T = ½ g_ij ẋ^i ẋ^j
  - Geodesics (free particle paths): ẍ^i + Γ^i_jk ẋ^j ẋ^k = 0
  - Curvature (how the manifold bends)

In the Genesis Engine, the metric is NOT Euclidean — it encodes the
physics of the four fabrics. The Fisher information metric (Milestone 4)
will provide the principled derivation; here we provide the computational
infrastructure.

Performance optimization:
    For constant metrics (fabric_block_metric, euclidean_metric), all
    Christoffel symbols vanish because ∂_m g_{ab} = 0 everywhere. The
    inverse metric is also constant and precomputed once. These facts
    eliminate the O(dim³) numerical differentiation that was the dominant
    bottleneck in environment stepping (6.2ms → <1µs per christoffel call).

References:
  - do Carmo (1992): Riemannian Geometry
  - Nakahara (2003): Geometry, Topology and Physics, Ch. 7
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np


# solve_ivp imported lazily inside geodesic_ode() — see L290 (Session 94)


if TYPE_CHECKING:
    from collections.abc import Callable


logger = logging.getLogger(__name__)


class RiemannianMetric:
    """A Riemannian metric on an n-dimensional manifold.

    The metric can be:
    - Constant (same g_ij everywhere) — e.g., Euclidean, fabric_block
    - Position-dependent (callable) — e.g., Fisher metric, curved manifold

    For constant metrics (the common case with fabric_block_metric), all
    Christoffel symbols vanish (Γ^i_jk = 0) and the inverse metric is
    precomputed once. This eliminates the O(dim³) numerical gradient
    computation that was the dominant bottleneck in environment stepping.

    Parameters
    ----------
    dim : int
        Dimension of the manifold.
    metric_fn : callable or np.ndarray
        If callable: metric_fn(x) → (dim, dim) positive-definite matrix.
        If ndarray: constant metric tensor (dim, dim).
    """

    def __init__(
        self,
        dim: int,
        metric_fn: Callable[[np.ndarray], np.ndarray] | np.ndarray | None = None,
    ) -> None:
        self.dim = dim

        # Detect whether the metric is position-independent (constant).
        # For constant metrics, Christoffel symbols are identically zero
        # and the inverse can be precomputed once, avoiding repeated
        # O(dim³) numerical differentiation and O(dim³) matrix inversion.
        self._is_constant = isinstance(metric_fn, np.ndarray) or metric_fn is None

        if metric_fn is None:
            # Default: Euclidean (identity metric)
            self._metric_matrix = np.eye(dim)
            self._metric_fn = lambda _x: np.eye(dim)
        elif isinstance(metric_fn, np.ndarray):
            self._metric_matrix = metric_fn.copy()
            self._metric_fn = lambda _x: self._metric_matrix
        else:
            self._metric_fn = metric_fn
            # For callable metrics, we can't assume constancy
            self._metric_matrix = None

        # Precomputed caches for constant metrics
        self._cached_inverse: np.ndarray | None = None
        self._cached_christoffel: np.ndarray | None = None

        # Eagerly precompute for constant metrics
        if self._is_constant and self._metric_matrix is not None:
            self._cached_inverse = np.linalg.inv(self._metric_matrix)
            # Christoffel symbols of a constant metric are identically zero.
            # Γ^i_jk = ½ g^{il} (∂_j g_{lk} + ∂_k g_{jl} - ∂_l g_{jk})
            # All ∂_m g_{ab} = 0 when g is constant → Γ^i_jk = 0.
            self._cached_christoffel = np.zeros((dim, dim, dim))

    def evaluate(self, x: np.ndarray) -> np.ndarray:
        """Compute metric tensor g_ij at point x.

        For constant metrics, returns the precomputed matrix directly
        without any function call overhead.
        """
        if self._is_constant and self._metric_matrix is not None:
            return self._metric_matrix
        return self._metric_fn(x)

    def inverse(self, x: np.ndarray) -> np.ndarray:
        """Compute inverse metric g^ij at point x.

        For constant metrics, returns the precomputed inverse matrix
        directly without repeated np.linalg.inv() calls.
        """
        if self._cached_inverse is not None:
            return self._cached_inverse
        return np.linalg.inv(self.evaluate(x))

    def determinant(self, x: np.ndarray) -> float:
        """Compute det(g_ij) at point x."""
        return float(np.linalg.det(self.evaluate(x)))

    def distance_squared(self, x: np.ndarray, dx: np.ndarray) -> float:
        """Compute ds² = g_ij dx^i dx^j."""
        g = self.evaluate(x)
        return float(dx @ g @ dx)

    def norm(self, x: np.ndarray, v: np.ndarray) -> float:
        """Compute |v|_g = sqrt(g_ij v^i v^j) at point x."""
        return float(np.sqrt(max(self.distance_squared(x, v), 0.0)))

    def christoffel(self, x: np.ndarray, eps: float = 1e-5) -> np.ndarray:
        """Compute Christoffel symbols Γ^i_jk at point x.

        For constant metrics, returns precomputed zero array immediately
        (all Christoffel symbols vanish because ∂_m g_{ab} = 0 everywhere).
        For position-dependent metrics, uses numerical differentiation.

        Uses numerical differentiation of the metric tensor:
        Γ^i_jk = ½ g^il (∂_j g_lk + ∂_k g_jl - ∂_l g_jk)

        Returns shape (dim, dim, dim) array where result[i, j, k] = Γ^i_jk.
        """
        # Fast path: constant metrics have zero Christoffel symbols
        if self._cached_christoffel is not None:
            return self._cached_christoffel

        n = self.dim
        g_inv = self.inverse(x)

        # Compute ∂_m g_ab numerically
        dg = np.zeros((n, n, n))  # dg[m, a, b] = ∂_m g_ab
        for m in range(n):
            x_plus = x.copy()
            x_minus = x.copy()
            x_plus[m] += eps
            x_minus[m] -= eps
            dg[m] = (self.evaluate(x_plus) - self.evaluate(x_minus)) / (2 * eps)

        # Γ^i_jk = ½ g^il (∂_j g_lk + ∂_k g_jl - ∂_l g_jk)
        gamma = np.zeros((n, n, n))
        for i in range(n):
            for j in range(n):
                for k in range(n):
                    s = 0.0
                    for l in range(n):
                        s += g_inv[i, l] * (dg[j, l, k] + dg[k, j, l] - dg[l, j, k])
                    gamma[i, j, k] = 0.5 * s

        return gamma

    def geodesic_acceleration(self, x: np.ndarray, v: np.ndarray, eps: float = 1e-5) -> np.ndarray:
        """Compute geodesic acceleration: a^i = -Γ^i_jk v^j v^k.

        This is the right-hand side of the geodesic equation:
        ẍ^i = -Γ^i_jk ẋ^j ẋ^k

        For constant metrics, returns a zero vector immediately since
        all Christoffel symbols are zero, skipping the O(dim³) loop.

        Parameters
        ----------
        x : position on the manifold
        v : velocity (tangent vector)
        """
        # Fast path: constant metrics have zero Christoffel symbols → zero acceleration
        if self._cached_christoffel is not None:
            return np.zeros(self.dim)

        gamma = self.christoffel(x, eps)
        # Einstein summation: a^i = -Γ^i_jk v^j v^k
        # Using numpy einsum for O(dim³) but vectorized
        return -np.einsum("ijk,j,k->i", gamma, v, v)

    def geodesic(
        self,
        x0: np.ndarray,
        v0: np.ndarray,
        t_span: tuple[float, float] = (0.0, 1.0),
        n_steps: int = 100,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compute a geodesic starting from x0 with initial velocity v0.

        Solves the geodesic equation ẍ^i + Γ^i_jk ẋ^j ẋ^k = 0.

        Returns
        -------
        t : np.ndarray, shape (n_steps,)
        trajectory : np.ndarray, shape (n_steps, dim)
        """
        n = self.dim

        def ode_rhs(t: float, state: np.ndarray) -> np.ndarray:
            x = state[:n]
            v = state[n:]
            a = self.geodesic_acceleration(x, v)
            return np.concatenate([v, a])

        y0 = np.concatenate([x0, v0])
        t_eval = np.linspace(t_span[0], t_span[1], n_steps)

        from scipy.integrate import solve_ivp  # lazy — avoids BLAS conflict (L290)

        sol = solve_ivp(ode_rhs, t_span, y0, t_eval=t_eval, method="RK45", rtol=1e-8)

        return sol.t, sol.y[:n].T  # (n_steps,) and (n_steps, dim)

    def riemann_curvature_scalar(self, x: np.ndarray, eps: float = 1e-4) -> float:
        """Compute the Ricci scalar curvature R at point x.

        R = g^ij R_ij where R_ij is the Ricci tensor (trace of Riemann tensor).

        For the Euclidean metric, R = 0. For a sphere of radius r, R = 2/r².
        This is an expensive computation (O(n⁵) for n dimensions).
        """
        n = self.dim
        g_inv = self.inverse(x)

        # Compute Christoffel symbols and their derivatives
        gamma = self.christoffel(x, eps)

        # ∂_m Γ^i_jk
        dgamma = np.zeros((n, n, n, n))
        for m in range(n):
            x_plus = x.copy()
            x_minus = x.copy()
            x_plus[m] += eps
            x_minus[m] -= eps
            dgamma[m] = (self.christoffel(x_plus, eps) - self.christoffel(x_minus, eps)) / (2 * eps)

        # Riemann tensor R^i_jkl = ∂_k Γ^i_jl - ∂_l Γ^i_jk + Γ^i_km Γ^m_jl - Γ^i_lm Γ^m_jk
        # Ricci tensor R_jl = R^i_jil
        ricci = np.zeros((n, n))
        for j in range(n):
            for l in range(n):
                for i in range(n):
                    ricci[j, l] += dgamma[i, i, j, l] - dgamma[l, i, j, i]
                    for m in range(n):
                        ricci[j, l] += (
                            gamma[i, i, m] * gamma[m, j, l] - gamma[i, l, m] * gamma[m, j, i]
                        )

        # Ricci scalar R = g^jl R_jl
        R = 0.0
        for j in range(n):
            for l in range(n):
                R += g_inv[j, l] * ricci[j, l]

        return float(R)


# --- Common metric constructors ---


def euclidean_metric(dim: int) -> RiemannianMetric:
    """Flat Euclidean metric: g_ij = δ_ij.

    Christoffel symbols are zero. Inverse is identity.
    """
    return RiemannianMetric(dim)


def hiho_metric(dim: int = 12, sigma: float = 0.3) -> RiemannianMetric:
    """HIHO-weighted metric: distances are larger near 0.5 (the attractor).

    This makes the HIHO point a "deep valley" in the metric — geodesics
    curve toward it naturally. The metric is:

    g_ij(x) = δ_ij * (1 + λ * exp(-|x - 0.5|²/σ²))

    where λ controls how deep the HIHO well is.

    NOTE: This metric IS position-dependent, so Christoffel symbols
    are NOT zero and must be computed numerically.
    """
    target = np.full(dim, 0.5)

    def metric_fn(x: np.ndarray) -> np.ndarray:
        dist_sq = np.sum((x - target) ** 2)
        weight = 1.0 + 2.0 * np.exp(-dist_sq / sigma**2)
        return np.eye(dim) * weight

    return RiemannianMetric(dim, metric_fn)


def fabric_block_metric(dim: int = 12) -> RiemannianMetric:
    """Block-diagonal metric reflecting the four-fabric structure.

    Each fabric (3 dims) has its own coupling constant:
    - Space (dims 0-2): g₁ = 1.0
    - Field (dims 3-5): g₂ = 0.7
    - Control (dims 6-8): g₃ = 0.5
    - Precipitation (dims 9-11): g₄ = 0.3

    This encodes the gauge coupling constants from the plan.

    NOTE: This is a CONSTANT metric. All Christoffel symbols vanish,
    and the inverse is diag(1/1.0, ..., 1/0.3). The optimized
    RiemannianMetric class precomputes these.
    """
    couplings = [1.0] * 3 + [0.7] * 3 + [0.5] * 3 + [0.3] * 3
    g = np.diag(couplings)
    return RiemannianMetric(dim, g)


__all__ = [
    "RiemannianMetric",
    "euclidean_metric",
    "fabric_block_metric",
    "hiho_metric",
]
