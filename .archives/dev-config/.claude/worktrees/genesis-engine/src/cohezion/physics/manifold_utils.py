"""Manifold Utilities - High-dimensional geometric operations for 12D spaces."""

from __future__ import annotations

from typing import Any

import numpy as np


class SemanticLagrangeFinder:
    """
    Finds stable 'Semantic Lagrange Points' (SLPs) in the 12D manifold.
    Based on the Restricted Three-Body Problem (Kordylewsky Cloud physics).
    """

    def __init__(self, mu_limit: float = 0.0385):
        self.mu_limit = mu_limit

    def find_triangular_points(
        self, topic_a: np.ndarray, topic_b: np.ndarray, weight_a: float, weight_b: float
    ) -> dict[str, Any]:
        """
        Calculate L4 and L5 points between two semantic topics.

        L4 and L5 form equilateral triangles with the two main masses.
        """
        total_weight = weight_a + weight_b
        mu = weight_b / total_weight if total_weight > 0 else 0

        if mu >= self.mu_limit:
            return {
                "stable": False,
                "reason": f"Mass ratio mu={mu:.4f} exceeds Routh critical value {self.mu_limit}",
                "mu": mu,
            }

        # Vector from A to B
        r_ab = topic_b - topic_a
        distance = np.linalg.norm(r_ab)

        if distance == 0:
            return {"stable": False, "reason": "Topics are identical (distance=0)"}

        # Barycenter position
        barycenter = (1 - mu) * topic_a + mu * topic_b

        # In a 12D space, we define the 'orbital plane' using the difference vector
        # and a robust orthogonal basis vector found via Gram-Schmidt.

        # Unit vector from A to B
        u = r_ab / distance

        # Robust 12D orthogonalization:
        # 1. Find dimension with minimum influence in u to use as seed
        min_dim = np.argmin(np.abs(u))
        v = np.zeros_like(u)
        v[min_dim] = 1.0

        # 2. Project v onto the subspace orthogonal to u (Gram-Schmidt)
        v = v - np.dot(v, u) * u
        v_norm = np.linalg.norm(v)

        # 3. Handle edge case (should be impossible with min_dim seed)
        if v_norm < 1e-10:
            v = np.zeros_like(u)
            v[0] = 1.0  # Emergency fallback
            v = v - np.dot(v, u) * u
            v_norm = np.linalg.norm(v)

        v = v / v_norm

        height = distance * np.sqrt(3) / 2
        midpoint = topic_a + 0.5 * r_ab

        l4 = midpoint + height * v
        l5 = midpoint - height * v

        return {
            "stable": True,
            "mu": mu,
            "distance": distance,
            "l4_point": l4.tolist(),
            "l5_point": l5.tolist(),
            "barycenter": barycenter.tolist(),
        }
