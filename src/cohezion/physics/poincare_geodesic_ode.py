"""Continuous Geodesic Flow Neural ODEs on Poincaré Hyperbolic Manifolds.

Implements Riemannian geodesic flow integrating:
    dx^mu / dt = f_theta(x) - Gamma^mu_{alpha beta} u^alpha u^beta
Clamps hyperbolic norm ||u|| <= 0.95 to maintain numerical stability and eliminate divergence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, List, Optional
import numpy as np

@dataclass(slots=True)
class PoincareGeodesicODE:
    dim: int = 2048
    curvature: float = -1.0
    max_norm: float = 0.95

    def compute_conformal_factor(self, x: np.ndarray) -> float:
        norm_sq = float(np.sum(x ** 2))
        norm_sq = min(norm_sq, self.max_norm ** 2)
        return 2.0 / (1.0 - norm_sq)

    def christoffel_symbols_contraction(self, x: np.ndarray, v: np.ndarray) -> np.ndarray:
        """Computes Gamma^mu_{alpha beta} v^alpha v^beta in the Poincaré ball."""
        norm_sq = float(np.sum(x ** 2))
        norm_sq = min(norm_sq, self.max_norm ** 2)
        denom = 1.0 - norm_sq
        if denom < 1e-6:
            denom = 1e-6
        # Gamma^mu_{alpha beta} v^alpha v^beta = 2 ( <x, v> v - 0.5 ||v||^2 x ) / (1 - ||x||^2)
        x_dot_v = float(np.dot(x, v))
        v_sq = float(np.sum(v ** 2))
        gamma_term = (2.0 / denom) * (x_dot_v * v - 0.5 * v_sq * x)
        return gamma_term

    def rk4_step(self, x: np.ndarray, v: np.ndarray, vector_field: Callable[[np.ndarray], np.ndarray], dt: float = 0.01) -> tuple[np.ndarray, np.ndarray]:
        """4th-order Runge-Kutta step along hyperbolic Riemannian manifold."""
        def derivatives(curr_x: np.ndarray, curr_v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            # dx/dt = v
            # dv/dt = f(x) - Gamma(x, v)
            f_x = vector_field(curr_x)
            gamma = self.christoffel_symbols_contraction(curr_x, curr_v)
            dv_dt = f_x - gamma
            return curr_v, dv_dt

        k1_x, k1_v = derivatives(x, v)
        k2_x, k2_v = derivatives(x + 0.5 * dt * k1_x, v + 0.5 * dt * k1_v)
        k3_x, k3_v = derivatives(x + 0.5 * dt * k2_x, v + 0.5 * dt * k2_v)
        k4_x, k4_v = derivatives(x + dt * k3_x, v + dt * k3_v)

        next_x = x + (dt / 6.0) * (k1_x + 2 * k2_x + 2 * k3_x + k4_x)
        next_v = v + (dt / 6.0) * (k1_v + 2 * k2_v + 2 * k3_v + k4_v)

        # Riemannian projection onto Poincare Ball
        norm = np.linalg.norm(next_x)
        if norm >= self.max_norm:
            next_x = (next_x / norm) * self.max_norm

        return next_x, next_v
