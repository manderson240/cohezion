r"""Arbitrary-Dimensional Poincaré-Ball Hyperbolic Manifold Physics
===================================================================
Implements arbitrary N-dimensional hyperbolic space operations (Poincaré ball model $\|x\| < 1$)
supporting 12D, 16D (Octonionic), 26D (Bosonic String), 32D (Dirac-Kähler),
256D (FLUME J-Space Vector), and 2048D (Full Cohezion SOUL_DIM).

Equations:
  - Hyperbolic Distance: d_H(u, v) = arcosh(1 + 2 * ||u - v||^2 / ((1 - ||u||^2) * (1 - ||v||^2)))
  - Metric Tensor: g_ij(x) = (4 / (1 - ||x||^2)^2) * delta_ij
  - Parallel Transport: Transport of tangent vector V along geodesic in N-dimensions
"""

from __future__ import annotations

import math
from typing import Sequence

from cohezion.contracts import PoincarePoint


class PoincareManifoldND:
    """Arbitrary N-dimensional Poincaré-ball hyperbolic manifold math provider."""

    MAX_RADIUS: float = 0.9999
    EPS: float = 1e-7

    @classmethod
    def origin(cls, dim: int) -> PoincarePoint:
        """Create origin point in N-dimensional hyperbolic space."""
        return PoincarePoint(tuple(0.0 for _ in range(dim)), dim=dim)

    @classmethod
    def project(cls, coords: Sequence[float], target_dim: int | None = None) -> PoincarePoint:
        """Project any N-dimensional vector into the unit Poincaré ball (|x| < 1)."""
        dim = target_dim or len(coords)
        if len(coords) != dim:
            raise ValueError(f"Expected {dim} dimensions, got {len(coords)}")

        norm_sq = sum(c * c for c in coords)
        norm = math.sqrt(norm_sq)

        if norm >= cls.MAX_RADIUS:
            scale = cls.MAX_RADIUS / (norm + cls.EPS)
            projected = tuple(c * scale for c in coords)
        else:
            projected = tuple(float(c) for c in coords)

        return PoincarePoint(projected, dim=dim)

    @classmethod
    def distance(cls, u: PoincarePoint, v: PoincarePoint) -> float:
        """Compute exact hyperbolic distance between two points in N-dimensional Poincaré ball."""
        if u.dim != v.dim:
            raise ValueError(f"Dimensional mismatch: u is {u.dim}D, v is {v.dim}D")

        u_sq = sum(c * c for c in u.coords)
        v_sq = sum(c * c for c in v.coords)

        diff_sq = sum((uc - vc) ** 2 for uc, vc in zip(u.coords, v.coords, strict=True))

        denom = (1.0 - u_sq) * (1.0 - v_sq)
        if denom <= 0:
            denom = cls.EPS

        arg = 1.0 + (2.0 * diff_sq / denom)
        arg = max(1.0, arg)  # Clamp for arcosh domain

        return math.acosh(arg)

    @classmethod
    def parallel_transport(
        cls,
        v_tangent: Sequence[float],
        u_start: PoincarePoint,
        u_end: PoincarePoint,
    ) -> tuple[float, ...]:
        """Parallel transport tangent vector v_tangent from u_start to u_end along geodesic via Levi-Civita connection."""
        from cohezion.physics.fiber_connection import FiberConnectionEngine
        from cohezion.physics.tensor_calculus import VectorTensor

        dim = u_start.dim
        if len(v_tangent) != dim or u_end.dim != dim:
            raise ValueError(f"Dimensional mismatch in parallel transport ({dim}D required)")

        v_vec = VectorTensor(tuple(v_tangent), is_covariant=False)
        dir_vec = VectorTensor(tuple(e - s for s, e in zip(u_start.coords, u_end.coords, strict=True)), is_covariant=False)

        # Covariant derivative update step
        cov_step = FiberConnectionEngine.covariant_derivative_step(v_vec, u_start, dir_vec)
        transported = tuple(vt + cov_step.components[i] for i, vt in enumerate(v_tangent))

        # Conformal norm preservation with boundary clamping against infinity overflow
        u_sq = min(0.9998, sum(c * c for c in u_start.coords))
        v_sq = min(0.9998, sum(c * c for c in u_end.coords))
        lambda_start = 2.0 / (1.0 - u_sq)
        lambda_end = 2.0 / (1.0 - v_sq)
        scale = lambda_start / lambda_end

        return tuple(t * scale for t in transported)

    @classmethod
    def curvature_regularization_loss(cls, points: Sequence[PoincarePoint]) -> float:
        """Compute average curvature distortion loss across a cluster of N-dimensional points."""
        if len(points) < 2:
            return 0.0

        total_loss = 0.0
        count = 0
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                d = cls.distance(points[i], points[j])
                boundary_penalty = max(0.0, points[i].norm - 0.95) + max(0.0, points[j].norm - 0.95)
                total_loss += d + (10.0 * boundary_penalty)
                count += 1

        return total_loss / count if count > 0 else 0.0


# Backward compatibility alias
PoincareManifold12D = PoincareManifoldND
