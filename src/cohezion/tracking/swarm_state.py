"""Swarm State representation and track history management.

Tracks persistent agent lineages, positions, velocities, and lineage branching
(mitosis/split/merge events) across time.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class Track:
    """A single persistent track representing an agent or latent thought entity."""

    track_id: str
    initial_timestamp: float
    current_timestamp: float
    position: np.ndarray  # Shape (D,)
    velocity: np.ndarray  # Shape (D,)
    history: List[np.ndarray] = field(default_factory=list)
    timestamps: List[float] = field(default_factory=list)
    age: int = 1
    total_hits: int = 1
    consecutive_misses: int = 0
    parent_track_id: Optional[str] = None
    children_track_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True

    def update(self, new_position: np.ndarray, timestamp: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        dt = max(1e-6, timestamp - self.current_timestamp)
        self.velocity = (new_position - self.position) / dt
        self.position = new_position.copy()
        self.current_timestamp = timestamp
        self.history.append(new_position.copy())
        self.timestamps.append(timestamp)
        self.age += 1
        self.total_hits += 1
        self.consecutive_misses = 0
        if metadata:
            self.metadata.update(metadata)

    def mark_missed(self, timestamp: float) -> None:
        dt = max(1e-6, timestamp - self.current_timestamp)
        # Extrapolate position with current velocity
        self.position = self.position + self.velocity * dt
        self.current_timestamp = timestamp
        self.age += 1
        self.consecutive_misses += 1


@dataclass
class SwarmState:
    """Aggregate snapshot of all swarm entities at timestamp t."""

    timestamp: float
    tracks: Dict[str, Track] = field(default_factory=dict)
    lineage_events: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def active_tracks(self) -> List[Track]:
        return [t for t in self.tracks.values() if t.is_active and t.consecutive_misses == 0]

    @property
    def center_of_mass(self) -> np.ndarray:
        active = self.active_tracks
        if not active:
            return np.zeros(1)
        positions = np.stack([t.position for t in active], axis=0)
        return np.mean(positions, axis=0)

    @property
    def velocity_flux(self) -> float:
        active = self.active_tracks
        if not active:
            return 0.0
        speeds = [float(np.linalg.norm(t.velocity)) for t in active]
        return float(np.mean(speeds))

    @property
    def swarm_entropy(self) -> float:
        """Computes spatial dispersion entropy of active tracks."""
        active = self.active_tracks
        if len(active) <= 1:
            return 0.0
        positions = np.stack([t.position for t in active], axis=0)
        cov = np.cov(positions, rowvar=False)
        if cov.ndim == 0:
            return 0.5 * np.log(max(1e-9, float(cov) * 2 * np.pi * np.e))
        sign, logdet = np.linalg.slogdet(cov + np.eye(cov.shape[0]) * 1e-6)
        if sign <= 0:
            return 0.0
        d = positions.shape[1]
        return float(0.5 * logdet + 0.5 * d * (1 + np.log(2 * np.pi)))
