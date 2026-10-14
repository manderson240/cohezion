"""Protocols and interfaces for Spatiotemporal Swarm State Tracking.

Abstracts the Biohub 1st Place Solution ("Tracking-by-detection with a per-cell visual tracker")
into a generic, domain-agnostic tracking framework for multi-agent swarms,
latent thought vectors, and evolving task lineages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable
import numpy as np


@dataclass
class Detection:
    """A generic spatiotemporal detection in N-dimensional state space."""

    timestamp: float
    position: np.ndarray  # Shape (D,), e.g., spatial coordinates or 12D/256D latent state
    confidence: float = 1.0
    entity_type: str = "agent"
    intensity_or_mass: float = 1.0  # Mass/intensity for COM conservation checks
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.position, np.ndarray):
            self.position = np.asarray(self.position, dtype=np.float64)


@runtime_checkable
class DetectionSource(Protocol):
    """Protocol for sources emitting spatiotemporal detections."""

    def get_detections(self, t: float) -> List[Detection]:
        """Returns all detections observed at timestamp t."""
        ...


@runtime_checkable
class StateEstimator(Protocol):
    """Protocol for predictive state filtering (e.g., constant velocity, Kalman, or ODE)."""

    def predict(self, state: np.ndarray, dt: float) -> np.ndarray:
        """Predicts the next state given time delta dt."""
        ...

    def update(self, prior: np.ndarray, observation: np.ndarray) -> np.ndarray:
        """Updates the state estimate given a new observation."""
        ...


@runtime_checkable
class AssociationPolicy(Protocol):
    """Protocol for bipartite matching between prior track states and current detections."""

    def compute_cost_matrix(
        self,
        predicted_positions: np.ndarray,  # (N, D)
        detection_positions: np.ndarray,   # (M, D)
    ) -> np.ndarray:                      # (N, M)
        """Computes pairwise association costs."""
        ...

    def associate(
        self,
        cost_matrix: np.ndarray,
        max_distance: float,
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """Returns (matched_pairs, unmatched_tracks, unmatched_detections)."""
        ...
