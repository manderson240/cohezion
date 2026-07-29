from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:  # keep this module numpy-free at import time
    from cohezion.physics.riemannian_metric import RiemannianMetric


@dataclass
class RiemannianGlideTrajectory:
    """Trajectory on a Riemannian manifold.

    With ``metric=None`` the step is a straight line, ``x_{t+dt} = x_t + dt*v_t``.
    That is a geodesic ONLY when the Christoffel symbols vanish, i.e. when the
    metric is CONSTANT -- not merely diagonal. A diagonal but position-dependent
    metric has ``Gamma != 0``: for conformal ``g_ij = delta_ij * h(x)``,
    ``Gamma^1_11 = d_1 h / (2h)``. ``hiho_metric`` in ``riemannian_metric`` is
    exactly such a metric, so the unwired straight-line step does not curve
    toward the HIHO attractor.

    Supply ``metric=`` to integrate the true geodesic equation
    ``x'' = -Gamma x' x'`` via ``RiemannianMetric.geodesic_acceleration``.
    """

    metric_tensor: list[list[float]]  # n x n positive-definite; identity for Euclidean
    position: list[float]  # current point
    velocity: list[float]  # current tangent vector
    metric: RiemannianMetric | None = None  # wire for true geodesic integration

    def _g(self) -> list[list[float]]:
        """Metric at the CURRENT position; the frozen tensor when unwired."""
        if self.metric is None:
            return self.metric_tensor
        import numpy as np

        return self.metric.evaluate(np.array(self.position)).tolist()

    def _inner_product(self, u: list[float], v: list[float]) -> float:
        """g(u, v) = u^T G v using the metric at the current position."""
        g = self._g()
        n = len(u)
        return sum(u[i] * sum(g[i][j] * v[j] for j in range(n)) for i in range(n))

    def step(self, dt: float = 0.01) -> list[float]:
        """Explicit Euler-Cromer step on the geodesic equation.

        NOT symplectic: the geodesic system is non-separable (the acceleration
        depends on velocity, ``a = -Gamma(x) v v``), so the symplectic-Euler
        guarantee does not apply and ``|v|_g`` is not conserved. First order.

        With ``metric=None`` this reduces exactly to ``x + dt*v``.
        """
        if self.metric is not None:
            import numpy as np

            a = self.metric.geodesic_acceleration(np.array(self.position), np.array(self.velocity))
            # Advancing position alone would leave the path straight regardless
            # of the acceleration computed. float() keeps self.velocity
            # list[float] rather than list[np.float64].
            self.velocity = [float(v + dt * ai) for v, ai in zip(self.velocity, a)]
        self.position = [p + dt * v for p, v in zip(self.position, self.velocity)]
        return list(self.position)

    def arc_length_element(self) -> float:
        """ds = sqrt(g(v, v)) -- infinitesimal arc length."""
        return math.sqrt(max(0.0, self._inner_product(self.velocity, self.velocity)))

    def arc_length(self, n_steps: int = 100, dt: float = 0.01) -> float:
        """Approximate arc length by Euler integration.

        Non-mutating: ``position`` and ``velocity`` are restored on return. A
        measurement must not consume the trajectory it measures.
        """
        pos0, vel0 = list(self.position), list(self.velocity)
        try:
            total = 0.0
            for _ in range(n_steps):
                total += self.arc_length_element() * dt
                self.step(dt)
            return total
        finally:
            self.position, self.velocity = pos0, vel0

    def curvature_proxy(self) -> float:
        """Mean metric SCALE tr(G)/n -- NOT a curvature.

        Returns 1.0 for the identity metric and 0.625 for ``fabric_block_metric``,
        both of which are FLAT (constant metric => Gamma == 0 => R == 0).
        Use :meth:`ricci_scalar` for actual curvature.
        """
        g = self._g()
        n = len(g)
        return sum(g[i][i] for i in range(n)) / n

    def ricci_scalar(self) -> float:
        """Ricci scalar R at the current position.

        Returns 0.0 when unwired -- NOT a fallback: a ``metric_tensor`` given as
        ``list[list[float]]`` is position-independent by construction, hence
        flat, hence R == 0 exactly.
        """
        if self.metric is None:
            return 0.0
        import numpy as np

        return float(self.metric.riemann_curvature_scalar(np.array(self.position)))
