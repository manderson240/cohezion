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

References:
  - do Carmo (1992): Riemannian Geometry
  - Nakahara (2003): Geometry, Topology and Physics, Ch. 7
"""

from __future__ import annotations

import logging
from typing import Callable

import numpy as np
from scipy.integrate import solve_ivp


logger = logging.getLogger(__name__)


class RiemannianMetric:
    """A Riemannian metric on an n-dimensional manifold.

    The metric can be:
    - Constant (same g_ij everywhere) — e.g., Euclidean, hyperbolic
    - Position-dependent (callable) — e.g., Fisher metric, curved manifold

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

        if metric_fn is None:
            # Default: Euclidean (identity metric)
            self._metric_fn = lambda _x: np.eye(dim)
        elif isinstance(metric_fn, np.ndarray):
            g = metric_fn.copy()
            self._metric_fn = lambda _x: g
        else:
            self._metric_fn = metric_fn

    def evaluate(self, x: np.ndarray) -> np.ndarray:
        """Compute metric tensor g_ij at point x."""
        return self._metric_fn(x)

    def inverse(self, x: np.ndarray) -> np.ndarray:
        """Compute inverse metric g^ij at point x."""
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

        Uses numerical differentiation of the metric tensor:
        Γ^i_jk = ½ g^il (∂_j g_lk + ∂_k g_jl - ∂_l g_jk)

        Returns shape (dim, dim, dim) array where result[i, j, k] = Γ^i_jk.
        """
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

        Parameters
        ----------
        x : position on the manifold
        v : velocity (tangent vector)
        """
        gamma = self.christoffel(x, eps)
        n = self.dim
        accel = np.zeros(n)
        for i in range(n):
            for j in range(n):
                for k in range(n):
                    accel[i] -= gamma[i, j, k] * v[j] * v[k]
        return accel

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
    """Flat Euclidean metric: g_ij = δ_ij."""
    return RiemannianMetric(dim)


def hiho_metric(dim: int = 12, sigma: float = 0.3) -> RiemannianMetric:
    """HIHO-weighted metric: distances are larger near 0.5 (the attractor).

    This makes the HIHO point a "deep valley" in the metric — geodesics
    curve toward it naturally. The metric is:

    g_ij(x) = δ_ij * (1 + λ * exp(-|x - 0.5|²/σ²))

    where λ controls how deep the HIHO well is.
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
