"""Poincaré Hyperbolic Manifold Trajectory Tracker.

Computes 2048D Poincaré disk hyperbolic embedding distances, conformal factors,
and geodesic trajectory tracking for agent states.
"""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


POINCARE_DIM = 2048


@dataclass
class PoincareState:
    """Agent state vector embedded in Poincaré hyperbolic space."""

    state_id: str
    vector: np.ndarray  # 2048D vector inside open ball ||x|| < 1.0
    conformal_factor: float
    norm: float
    timestamp: float


class PoincareManifoldTracker:
    """Poincaré Hyperbolic Space Trajectory Tracker."""

    def __init__(self, dimension: int = POINCARE_DIM, max_norm: float = 0.999) -> None:
        self.dimension = dimension
        self.max_norm = max_norm
        self._history: List[PoincareState] = []

    def conformal_factor(self, x: np.ndarray) -> float:
        """Compute Poincaré metric conformal factor lambda(x) = 2 / (1 - ||x||^2)."""
        norm_sq = float(np.sum(x**2))
        norm_sq = min(norm_sq, self.max_norm**2)
        return 2.0 / max(1.0 - norm_sq, 1e-6)

    def poincare_distance(self, x: np.ndarray, y: np.ndarray) -> float:
        """Compute hyperbolic geodesic distance in Poincaré open ball model."""
        x = self._project_to_ball(x)
        y = self._project_to_ball(y)

        diff_norm_sq = float(np.sum((x - y) ** 2))
        x_norm_sq = min(float(np.sum(x**2)), self.max_norm**2)
        y_norm_sq = min(float(np.sum(y**2)), self.max_norm**2)

        denom = (1.0 - x_norm_sq) * (1.0 - y_norm_sq)
        arg = 1.0 + 2.0 * (diff_norm_sq / max(denom, 1e-8))

        return float(np.arccosh(max(arg, 1.0)))

    def project_and_track(self, state_id: str, raw_vector: np.ndarray | bytes | List[float], timestamp: float) -> PoincareState:
        """Project raw vector to 2048D Poincaré ball and record trajectory step."""
        # 1. Convert bytes or list to float ndarray
        if isinstance(raw_vector, bytes):
            vec = np.frombuffer(raw_vector, dtype=np.uint8).astype(np.float64)
        else:
            vec = np.asarray(raw_vector, dtype=np.float64).ravel()
        if len(vec) < self.dimension:
            vec = np.pad(vec, (0, self.dimension - len(vec)))
        else:
            vec = vec[: self.dimension]

        # 2. Project into open ball ||x|| < 1.0
        vec = self._project_to_ball(vec)
        norm = float(np.linalg.norm(vec))
        lambda_x = self.conformal_factor(vec)

        p_state = PoincareState(
            state_id=state_id,
            vector=vec,
            conformal_factor=lambda_x,
            norm=norm,
            timestamp=timestamp,
        )

        self._history.append(p_state)
        return p_state

    def _project_to_ball(self, x: np.ndarray) -> np.ndarray:
        """Project vector inside open ball ||x|| <= max_norm."""
        norm = float(np.linalg.norm(x))
        if norm >= self.max_norm:
            return x * (self.max_norm / (norm + 1e-10))
        return x

    def get_trajectory_drift(self) -> float:
        """Compute mean hyperbolic geodesic distance along recent state trajectory."""
        if len(self._history) < 2:
            return 0.0
        distances = []
        for i in range(1, len(self._history)):
            d = self.poincare_distance(self._history[i - 1].vector, self._history[i].vector)
            distances.append(d)
        return float(np.mean(distances))

    def get_recent_history(self) -> List[PoincareState]:
        return list(self._history)
