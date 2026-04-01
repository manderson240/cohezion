"""Ouroboros Bridge — Connect self-healing to Genesis physics metrics.

Maps Ouroboros exhaust consumption to cosmogony phases and triggers
anomalies when coherence drops or JEPA prediction errors spike.
Healing events are interpreted as the manifold self-correcting.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum

from cohezion.learning.ouroboros import ExecutionExhaust, OuroborosEngine
from cohezion.learning.ouroboros_trigger import OuroborosTrigger, TriggerState


logger = logging.getLogger(__name__)

COHERENCE_DROP_THRESHOLD = 0.3
JEPA_ERROR_THRESHOLD = 0.5


class HealingPhase(Enum):
    """Maps healing events to cosmogony phases."""

    DETECTION = "detection"  # Anomaly detected — void fluctuation
    DIAGNOSIS = "diagnosis"  # Root cause analysis — symmetry breaking
    PATCHING = "patching"  # Fix applied — gauge field correction
    VERIFICATION = "verification"  # Tests pass — HIHO restoration
    STABLE = "stable"  # System healthy — manifold equilibrium


@dataclass
class PhysicsAnomaly:
    """An anomaly detected by the physics layer."""

    source: str
    severity: float
    metric_name: str
    metric_value: float
    threshold: float
    healing_phase: HealingPhase = HealingPhase.DETECTION
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "severity": self.severity,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "healing_phase": self.healing_phase.value,
            "timestamp": self.timestamp,
        }


@dataclass
class HealingEvent:
    """A healing event mapped to cosmogony."""

    task_id: str
    phase: HealingPhase
    triggered_rewrite: bool
    cosmogony_interpretation: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "phase": self.phase.value,
            "triggered_rewrite": self.triggered_rewrite,
            "cosmogony_interpretation": self.cosmogony_interpretation,
            "timestamp": self.timestamp,
        }


class OuroborosBridge:
    """Bridge between Ouroboros self-healing and Genesis physics layer.

    Monitors physics metrics (coherence, JEPA error) and feeds failures
    back through the Ouroboros loop. Healing events are mapped to
    cosmogony phases for the Genesis UI.
    """

    def __init__(
        self,
        engine: OuroborosEngine | None = None,
        trigger: OuroborosTrigger | None = None,
        coherence_threshold: float = COHERENCE_DROP_THRESHOLD,
        jepa_threshold: float = JEPA_ERROR_THRESHOLD,
    ) -> None:
        self._engine = engine or OuroborosEngine()
        self._trigger = trigger or OuroborosTrigger()
        self._coherence_threshold = coherence_threshold
        self._jepa_threshold = jepa_threshold
        self._anomalies: list[PhysicsAnomaly] = []
        self._healing_events: list[HealingEvent] = []

    @property
    def anomalies(self) -> list[PhysicsAnomaly]:
        return list(self._anomalies)

    @property
    def healing_events(self) -> list[HealingEvent]:
        return list(self._healing_events)

    async def check_coherence(
        self, coherence_drop: float, task_id: str = "physics"
    ) -> PhysicsAnomaly | None:
        """Check coherence and trigger anomaly if drop exceeds threshold."""
        if coherence_drop <= self._coherence_threshold:
            return None

        anomaly = PhysicsAnomaly(
            source="coherence_monitor",
            severity=min(coherence_drop / 1.0, 1.0),
            metric_name="coherence_drop",
            metric_value=coherence_drop,
            threshold=self._coherence_threshold,
        )
        self._anomalies.append(anomaly)

        logger.warning(
            "Coherence drop %.3f > threshold %.3f", coherence_drop, self._coherence_threshold
        )

        exhaust = ExecutionExhaust(
            task_id=task_id,
            error_message=None,
            coherence_drop=coherence_drop,
            token_usage=0,
            diagnostics={"anomaly": anomaly.to_dict()},
        )
        triggered = await self._engine.consume_exhaust(exhaust)
        self._record_healing(task_id, triggered, "manifold_coherence_correction")
        return anomaly

    async def check_jepa_error(
        self, prediction_error: float, task_id: str = "jepa"
    ) -> PhysicsAnomaly | None:
        """Check JEPA prediction error and trigger VAE fine-tuning if needed."""
        if prediction_error <= self._jepa_threshold:
            return None

        anomaly = PhysicsAnomaly(
            source="jepa_predictor",
            severity=min(prediction_error / 1.0, 1.0),
            metric_name="prediction_error",
            metric_value=prediction_error,
            threshold=self._jepa_threshold,
        )
        self._anomalies.append(anomaly)

        logger.warning("JEPA error %.3f > threshold %.3f", prediction_error, self._jepa_threshold)

        failure_hash = f"jepa_{task_id}_{int(time.time())}"
        event = self._trigger.trigger(failure_hash, trigger_source="coherence_collapse")

        interpretation = (
            "vae_fine_tuning_initiated" if event.state == TriggerState.TRAINING else "vae_deferred"
        )
        self._record_healing(task_id, event.state == TriggerState.TRAINING, interpretation)
        return anomaly

    def _record_healing(self, task_id: str, triggered: bool, interpretation: str) -> None:
        phase = HealingPhase.PATCHING if triggered else HealingPhase.DETECTION
        event = HealingEvent(
            task_id=task_id,
            phase=phase,
            triggered_rewrite=triggered,
            cosmogony_interpretation=interpretation,
        )
        self._healing_events.append(event)

    def get_health_summary(self) -> dict:
        """Summarize the current health state for the API."""
        recent_anomalies = self._anomalies[-10:]
        return {
            "status": "healthy" if not recent_anomalies else "anomalous",
            "total_anomalies": len(self._anomalies),
            "total_healings": len(self._healing_events),
            "recent_anomalies": [a.to_dict() for a in recent_anomalies],
            "ouroboros_rules": self._engine.get_latest_system_rules(),
            "trigger_history": self._trigger.get_training_history(),
        }
