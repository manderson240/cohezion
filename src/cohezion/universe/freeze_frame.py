"""Freeze-Frame Reality Capture (Story 3.4, NFR-8).

Captures full 12D state snapshots during TDD failures as high-fidelity
training data for the Ouroboros fine-tuning loop. Each frame includes
the latent state, failure hash, agent context, and a content hash
for deduplication.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)

MANIFOLD_DIM = 12


@dataclass
class FreezeFrame:
    """An immutable snapshot of 12D state captured during a failure."""

    trigger: str  # "tdd_red" | "divergence" | "coherence_collapse"
    latent_state: list[float]  # 12D axiomatic vector
    failure_hash: str  # Hash identifying the specific failure
    agent_id: str
    context: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Serialize for vault persistence."""
        return {
            "trigger": self.trigger,
            "latent_state": self.latent_state,
            "failure_hash": self.failure_hash,
            "agent_id": self.agent_id,
            "context": self.context,
            "timestamp": self.timestamp,
        }

    def content_hash(self) -> str:
        """Deterministic SHA-256 hash for deduplication."""
        payload = json.dumps(
            {
                "trigger": self.trigger,
                "latent_state": self.latent_state,
                "failure_hash": self.failure_hash,
                "agent_id": self.agent_id,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


class FreezeFrameCapture:
    """Service that creates freeze-frames from failure events."""

    def capture(
        self,
        trigger: str,
        latent_state: list[float],
        failure_hash: str,
        agent_id: str,
        context: dict | None = None,
    ) -> FreezeFrame:
        """Capture a freeze-frame, validating inputs."""
        if len(latent_state) != MANIFOLD_DIM:
            raise ValueError(f"Latent state must be 12D (got {len(latent_state)}D)")
        if not failure_hash or not failure_hash.strip():
            raise ValueError("failure_hash is required for deduplication")

        frame = FreezeFrame(
            trigger=trigger,
            latent_state=latent_state,
            failure_hash=failure_hash,
            agent_id=agent_id,
            context=context or {},
        )
        logger.info(
            "Freeze-frame captured: %s from %s (hash=%s)",
            trigger,
            agent_id,
            frame.content_hash()[:16],
        )
        return frame


class FreezeFrameStore:
    """In-memory store for freeze-frames with deduplication."""

    def __init__(self) -> None:
        self._frames: list[FreezeFrame] = []
        self._seen_hashes: set[str] = set()

    @property
    def frames(self) -> list[FreezeFrame]:
        return list(self._frames)

    def add(self, frame: FreezeFrame) -> bool:
        """Add a frame, deduplicating by content hash. Returns True if added."""
        h = frame.content_hash()
        if h in self._seen_hashes:
            logger.debug("Duplicate freeze-frame skipped: %s", h[:16])
            return False
        self._seen_hashes.add(h)
        self._frames.append(frame)
        return True

    def export_training_data(self) -> list[dict]:
        """Export all frames as training data for Ouroboros."""
        return [f.to_dict() for f in self._frames]

    def clear(self) -> None:
        """Clear all frames after Ouroboros consumption."""
        self._frames.clear()
        self._seen_hashes.clear()
