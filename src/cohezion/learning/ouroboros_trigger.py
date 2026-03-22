"""Ouroboros Trigger — VAE Fine-Tuning Loop (Story 5.1, NFR-4, NFR-8).

TDD failures automatically trigger VAE fine-tuning iterations.
Includes a divergence watchdog that halts training if loss increases
for 3+ consecutive epochs, and consensus gating to prevent
deploying degraded encoders.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)

DIVERGENCE_PATIENCE = 3  # Epochs of increasing loss before rollback
CONSENSUS_TIMEOUT_SEC = 30.0


class TriggerState(Enum):
    IDLE = "idle"
    TRAINING = "training"
    DIVERGED = "diverged"
    COMPLETED = "completed"
    DEFERRED = "deferred"


@dataclass
class TrainingEvent:
    """A VAE fine-tuning event triggered by a TDD failure."""

    failure_hash: str
    trigger_source: str  # "tdd_red" | "coherence_collapse"
    state: TriggerState = TriggerState.IDLE
    epoch_losses: list[float] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    rollback_checkpoint: str | None = None

    def to_dict(self) -> dict:
        return {
            "failure_hash": self.failure_hash,
            "trigger_source": self.trigger_source,
            "state": self.state.value,
            "epoch_losses": self.epoch_losses,
            "timestamp": self.timestamp,
            "rollback_checkpoint": self.rollback_checkpoint,
        }


class OuroborosTrigger:
    """Manages VAE fine-tuning triggered by TDD failures.

    Flow:
    1. TDD failure detected -> trigger() called
    2. Consensus check (simulated) -> proceed or defer
    3. Training begins with divergence watchdog
    4. If loss diverges for 3+ epochs -> rollback
    5. If training completes -> update encoder
    """

    def __init__(self, patience: int = DIVERGENCE_PATIENCE) -> None:
        self._patience = patience
        self._events: list[TrainingEvent] = []
        self._active_event: TrainingEvent | None = None

    @property
    def events(self) -> list[TrainingEvent]:
        return list(self._events)

    @property
    def active_event(self) -> TrainingEvent | None:
        return self._active_event

    def trigger(
        self,
        failure_hash: str,
        trigger_source: str = "tdd_red",
        consensus_reached: bool = True,
        checkpoint: str | None = None,
    ) -> TrainingEvent:
        """Trigger a VAE fine-tuning iteration from a TDD failure."""
        event = TrainingEvent(
            failure_hash=failure_hash,
            trigger_source=trigger_source,
            rollback_checkpoint=checkpoint,
        )

        if not consensus_reached:
            event.state = TriggerState.DEFERRED
            logger.info("Ouroboros deferred: no consensus for %s", failure_hash[:16])
            self._events.append(event)
            return event

        event.state = TriggerState.TRAINING
        self._active_event = event
        logger.info("Ouroboros triggered: training for %s", failure_hash[:16])
        self._events.append(event)
        return event

    def record_epoch(self, loss: float) -> TriggerState:
        """Record a training epoch loss. Returns current state."""
        if self._active_event is None:
            return TriggerState.IDLE

        self._active_event.epoch_losses.append(loss)

        # Check divergence: loss increasing for patience consecutive epochs
        if len(self._active_event.epoch_losses) >= self._patience:
            recent = self._active_event.epoch_losses[-self._patience :]
            if all(recent[i] < recent[i + 1] for i in range(len(recent) - 1)):
                self._active_event.state = TriggerState.DIVERGED
                logger.warning(
                    "Ouroboros diverged after %d epochs, rolling back",
                    len(self._active_event.epoch_losses),
                )
                self._active_event = None
                return TriggerState.DIVERGED

        return TriggerState.TRAINING

    def complete(self) -> TrainingEvent | None:
        """Mark active training as completed."""
        if self._active_event is None:
            return None
        self._active_event.state = TriggerState.COMPLETED
        completed = self._active_event
        self._active_event = None
        logger.info("Ouroboros training completed: %s", completed.failure_hash[:16])
        return completed

    def get_training_history(self) -> list[dict]:
        """Export training history for analysis."""
        return [e.to_dict() for e in self._events]
