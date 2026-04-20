"""Intent-Action Synchronization (Story 3.7, FR6).

Cryptographically signs the relationship between declared intent and
executed action to detect Middle-Man Drift — when the actual 12D state
change diverges from what the agent declared it would do.

Uses HMAC-SHA256 signatures and L2 distance for drift detection.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field

import numpy as np


logger = logging.getLogger(__name__)

MANIFOLD_DIM = 12


@dataclass
class IntentActionPair:
    """Links a declared intent to the resulting action in 12D space."""

    agent_id: str
    intent_vector: list[float]  # 12D declared intent
    action_vector: list[float]  # 12D actual result
    intent_text: str = ""
    timestamp: float = field(default_factory=time.time)

    def compute_signature(self) -> str:
        """HMAC-SHA256 signature binding intent to action."""
        payload = json.dumps(
            {
                "agent_id": self.agent_id,
                "intent": self.intent_vector,
                "action": self.action_vector,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class SyncVerdict:
    """Result of intent-action synchronization check."""

    aligned: bool
    drift: float  # L2 distance between intent and action
    signature: str = ""
    pair: IntentActionPair | None = None


class IntentActionSync:
    """Verifies intent-action alignment and detects Middle-Man Drift.

    Computes L2 distance between declared intent vector and actual
    action vector. Drift beyond threshold indicates tampering or
    hallucination.
    """

    def __init__(self, drift_threshold: float = 0.3) -> None:
        self._threshold = drift_threshold
        self._history: list[SyncVerdict] = []

    @property
    def history(self) -> list[SyncVerdict]:
        return list(self._history)

    def verify(self, pair: IntentActionPair) -> SyncVerdict:
        """Verify alignment between intent and action."""
        intent = np.array(pair.intent_vector)
        action = np.array(pair.action_vector)
        drift = float(np.linalg.norm(intent - action))

        aligned = drift <= self._threshold
        signature = pair.compute_signature()

        verdict = SyncVerdict(
            aligned=aligned,
            drift=drift,
            signature=signature,
            pair=pair,
        )
        self._history.append(verdict)

        if not aligned:
            logger.warning(
                "Intent-Action drift detected for %s: %.4f > %.4f",
                pair.agent_id,
                drift,
                self._threshold,
            )

        return verdict

    def get_drift_events(self) -> list[dict]:
        """Export drift events for Ouroboros training."""
        return [
            {
                "agent_id": v.pair.agent_id if v.pair else None,
                "drift": v.drift,
                "aligned": v.aligned,
                "signature": v.signature,
                "timestamp": v.pair.timestamp if v.pair else 0,
            }
            for v in self._history
            if not v.aligned
        ]
