from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class RiemannianGlideTrajectory:
    """Geodesic (zero-curvature) trajectory on a Riemannian manifold.

    Models compound-loop quality evolution as a curve with the Levi-Civita connection.
    Uses flat-space Euler integration (exact for diagonal metrics).
    """

    metric_tensor: list[list[float]]  # n x n positive-definite; identity for Euclidean
    position: list[float]  # current point
    velocity: list[float]  # current tangent vector

    def _inner_product(self, u: list[float], v: list[float]) -> float:
        """g(u, v) = u^T G v using metric_tensor G."""
        n = len(u)
        return sum(u[i] * sum(self.metric_tensor[i][j] * v[j] for j in range(n)) for i in range(n))

    def step(self, dt: float = 0.01) -> list[float]:
        """Euler step: x_{t+dt} = x_t + dt * v_t (geodesic in flat/diagonal metric)."""
        self.position = [p + dt * v for p, v in zip(self.position, self.velocity)]
        return list(self.position)

    def arc_length_element(self) -> float:
        """ds = sqrt(g(v, v)) -- infinitesimal arc length."""
        return math.sqrt(max(0.0, self._inner_product(self.velocity, self.velocity)))

    def arc_length(self, n_steps: int = 100, dt: float = 0.01) -> float:
        """Approximate arc length by Euler integration."""
        total = 0.0
        for _ in range(n_steps):
            total += self.arc_length_element() * dt
            self.step(dt)
        return total

    def curvature_proxy(self) -> float:
        """tr(G) / n -- simplest Riemannian invariant (= 1.0 for identity metric)."""
        n = len(self.metric_tensor)
        return sum(self.metric_tensor[i][i] for i in range(n)) / n
