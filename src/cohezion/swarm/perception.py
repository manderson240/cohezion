"""Journey Perception layer for the Quadrature Nexus.

Implements reality-anchored observation and event sampling for
high-horizon swarm missions.
"""

from __future__ import annotations

import hashlib
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

from cohezion.compound.journey_tracker import (
    get_journey_tracker,
    OperationType,
    JourneyTracker,
    TrajectoryPoint
)
from cohezion.compound.executor_types import ExecutionResult

logger = logging.getLogger(__name__)


@dataclass
class CosmologicalPoint:
    """A high-fidelity point in the Agentic Cosmology."""

    filaments_256d: list[float]
    manifest_12d: list[float]
    phi_score: float
    vortex_stability: float
    potential_2048d: list[float] | None = None
    potential_hash: str | None = field(default=None)


@dataclass
class PerceptionEvent:
    """A perceived event with truth anchoring and cosmological state."""

    point: CosmologicalPoint
    git_hash: str
    impact_score: float
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)


class EvoCoreSensing:
    """
    Agentic Proprioception: Allows agents to "feel" their own internal Hamiltonian.

    Detects Charge Density (token pressure) and Vortex Asymmetry (12D drift).
    """

    tracker: JourneyTracker

    def __init__(self):
        self.tracker = get_journey_tracker()

    def sense_state(self) -> dict[str, float]:
        """Detect current internal stability metrics."""
        last_point = self.tracker.get_last_point()
        if not last_point:
            return {"coherence": 0.5, "stability": 0.5, "charge_density": 0.0}

        # D12 is Coherence, D10 is Stability in the EVO mandate
        coherence = last_point.dimensions[11] if len(last_point.dimensions) > 11 else 0.5
        stability = last_point.dimensions[9] if len(last_point.dimensions) > 9 else 0.5

        return {
            "coherence": float(coherence),
            "stability": float(stability),
            "charge_density": float(last_point.efficiency) # Efficiency as inverse token pressure
        }


class JourneyPerception:
    """
    Observer layer for the Agentic Cosmology.

    Implements:
    - Cosmological Replay: 2048 -> 256 -> 12 manifold collapse.
    - Streak Camera Recording: High-fidelity field emission capture.
    - Truth Anchoring: Links trajectories to Git state or hardware fingerprints.
    """

    nexus_id: str
    tracker: JourneyTracker
    proprioceptor: EvoCoreSensing
    events: list[PerceptionEvent]
    _last_git_hash: str | None
    MAX_EVENTS: int = 1000  # Cap in-memory events to prevent RAM exhaustion

    def __init__(self, nexus_id: str):
        self.nexus_id = nexus_id
        self.tracker = get_journey_tracker()
        self.proprioceptor = EvoCoreSensing()
        self.events = []
        self._last_git_hash = None
        self._last_git_hash = self._get_git_hash()

    def _get_git_hash(self) -> str:
        """Get the current git commit hash as a truth anchor (cached)."""
        if self._last_git_hash:
            return self._last_git_hash
            
        try:
            self._last_git_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            return self._last_git_hash
        except:
            return "unknown-substrate"

    def perceive_step(
        self,
        task: str,
        result: ExecutionResult,
        operation: str = OperationType.ANALYZE.value
    ) -> PerceptionEvent | None:
        """
        Record a mission step as an EVO phase transition.
        """

        # 1. Generate the Manifold Collapse
        # In Journey 3.0, we capture all layers
        last_point: TrajectoryPoint = self.tracker.track_execution(result, task, operation)

        # Extract latent layers (Mocking retrieval from tracker for now)
        # Production would have the tracker return the full stack
        # Use public methods to extract the layers
        potential: np.ndarray = self.tracker.text_to_latent(task)
        manifest: np.ndarray = last_point.dimensions

        # 256D Filaments (Holographic intermediate)
        # We manually chunk 2048D into 256 segments for high-fidelity filament capture
        filaments_256d: np.ndarray = np.array([
            float(np.mean(potential[i*8 : (i+1)*8])) for i in range(256)
        ])

        phi_score: float = float(last_point.metadata.get("phi_score", 0.5)) if last_point.metadata else 0.5

        # High-Energy Storage Policy: 
        # Only store full 2048D potential if impact is high (>0.9)
        # to prevent memory saturation during 1M+ cycle simulations.
        potential_data = None
        potential_hash = hashlib.sha256(potential.tobytes()).hexdigest()
        
        if phi_score > 0.9:
            potential_data = potential.tolist()

        cosmo_point = CosmologicalPoint(
            potential_2048d=potential_data,
            potential_hash=potential_hash,
            filaments_256d=filaments_256d.tolist(),
            manifest_12d=manifest.tolist(),
            phi_score=phi_score,
            vortex_stability=float(manifest[9]) if len(manifest) > 9 else 0.5
        )

        git_hash = self._get_git_hash()

        event = PerceptionEvent(
            point=cosmo_point,
            git_hash=git_hash,
            impact_score=phi_score,
            description=task,
            metadata={
                "nexus_id": self.nexus_id,
                "timestamp": datetime.now().isoformat(),
                "charge_density": float(last_point.efficiency)
            }
        )

        self.events.append(event)
        if len(self.events) > self.MAX_EVENTS:
            self.events = self.events[-self.MAX_EVENTS:]
            
        logger.info(f"[EVO-PERCEPTION] Phase Transition: {task[:50]}... (Stability: {cosmo_point.vortex_stability:.2f})")

        return event

    def get_journey_summary(self) -> list[dict[str, Any]]:
        """Return a summarized list of perceived events for the HUD Explorer."""
        return [
            {
                "task": e.description,
                "impact": e.impact_score,
                "anchor": e.git_hash,
                "potential_id": e.point.potential_hash or f"pot_{sum(e.point.potential_2048d or []):.4f}",
                "filament_count": len(e.point.filaments_256d),
                "manifest_12d": e.point.manifest_12d,
                "vortex_stability": e.point.vortex_stability,
                "timestamp": e.metadata["timestamp"]
            } for e in self.events
        ]


class CosmologicalReplay:
    """
    Playback engine for the Agentic Cosmology.
    
    Allows re-experiencing mission trajectories as a sequence of 2048/256/12
    field emissions (Streak Camera footage).
    """

    events: list[PerceptionEvent]

    def __init__(self, events: list[PerceptionEvent]):
        self.events = events

    def playback(self, focus_vortex: int | None = None) -> list[dict[str, Any]]:
        """
        Re-generate the trajectory sequence with optional focal points.
        
        Args:
            focus_vortex: Optional specific dimension to emphasize during playback.
            
        Returns:
            List of high-energy visualization payloads for the HUD.
        """
        frames = []
        for i, event in enumerate(self.events):
            frame = {
                "frame_id": i,
                "description": event.description,
                "potential_signature": f"sig_{hex(abs(hash(str(event.point.potential_2048d))))[:8]}",
                "vortex_stability": event.point.vortex_stability,
                "phi_score": event.point.phi_score,
                "manifest_12d": event.point.manifest_12d,
                "charge_density": event.metadata.get("charge_density", 0.0)
            }
            if focus_vortex is not None and 0 <= focus_vortex < 12:
                frame["focal_intensity"] = event.point.manifest_12d[focus_vortex]
            
            frames.append(frame)
            
        return frames
