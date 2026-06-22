"""Ouroboros Architecture (Recursive Self-Improvement).

Consumes engine operation exhaust (failures, inefficiencies, context walls)
to systematically rewrite internal execution PRDs and system prompts.

Attribution bridge (2026-06-22):
    ``OuroborosAttribution.from_exhaust()`` converts ExecutionExhaust into a
    typed failure class + evidence dict ready for RecursiveTraceLoop.failure_map.
    When a numpy latent vector is provided, top concept directions are included
    via LatentDirectionProbe (if fitted) for mechanistic interpretability.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class ExecutionExhaust(BaseModel):
    """Data collected from a failed or inefficient execution."""

    task_id: str
    error_message: str | None
    coherence_drop: float
    token_usage: int
    diagnostics: dict[str, Any]


class OuroborosEngine:
    """The recursive self-improvement loop for the Cohezion intelligence pipeline."""

    def __init__(self, target_coherence: float = 0.5):
        self.target_coherence = target_coherence
        self.rewrite_history: list[dict[str, Any]] = []

    async def consume_exhaust(self, exhaust: ExecutionExhaust) -> bool:
        """Analyze failure exhaust and determine if a rewrite is needed."""
        logger.info(f"Ouroboros consuming exhaust for Task {exhaust.task_id}")

        # Heuristic for triggering a self-improvement cycle
        needs_rewrite = False
        if exhaust.error_message:
            logger.warning(f"Task failed with error: {exhaust.error_message}")
            needs_rewrite = True
        elif exhaust.coherence_drop > 0.3:
            logger.warning(f"Massive coherence drop detected: {exhaust.coherence_drop}")
            needs_rewrite = True

        if needs_rewrite:
            return await self._trigger_rewrite_cycle(exhaust)

        logger.debug("Exhaust within acceptable parameters. No rewrite needed.")
        return False

    async def _trigger_rewrite_cycle(self, exhaust: ExecutionExhaust) -> bool:
        """Generate a new prompt or system alignment rules based on the failure.

        Emits a HEALING_EVENT precipitation event so the Ouroboros feedback
        loop becomes visible to the orchestrator and downstream sinks.
        """
        logger.info("Initiating recursive rewrite cycle to prevent future failure.")

        # Simulate an LLM call analyzing the failure and updating the prompt
        new_rule = (
            f"Prevent failure class observed in {exhaust.task_id} by limiting context window sizes."
        )
        rewrite_entry = {
            "source_task": exhaust.task_id,
            "new_rule": new_rule,
            "metrics": exhaust.diagnostics,
        }
        self.rewrite_history.append(rewrite_entry)

        logger.info(f"Ouroboros rewrite successful. New dynamic rule: {new_rule}")

        _emit_healing_event(exhaust, new_rule)

        return True

    def get_latest_system_rules(self) -> list[str]:
        """Fetch the accumulated, self-improved system rules."""
        return [entry["new_rule"] for entry in self.rewrite_history]

    async def analyze_audio_telemetry(self, event_data: dict[str, Any]) -> bool:
        """Monitor audio training metrics for divergence or instability."""
        event_type = event_data.get("event_type")
        if event_type != "training_step":
            return False

        predictions = event_data.get("predictions", {})
        loss = predictions.get("loss", 0.0)
        coherence = event_data.get("coherence", 1.0)

        # Trigger self-correction if loss spikes or coherence drops
        if loss > 5.0:
            logger.warning(f"Audio training divergence detected (loss={loss:.2f})")
            exhaust = ExecutionExhaust(
                task_id="birdclef_training",
                error_message="High training loss detected",
                coherence_drop=1.0 - coherence,
                token_usage=0,
                diagnostics={"loss": loss, "event": event_data},
            )
            return await self._trigger_rewrite_cycle(exhaust)

        return False


@dataclass
class OuroborosAttribution:
    """Structured failure attribution produced from ExecutionExhaust.

    Bridges OuroborosEngine healing events to RecursiveTraceLoop.failure_map
    so the next strategy is conditioned on a TYPED failure class rather than
    an opaque error string.

    Fields
    ------
    failure_class : str
        Typed category: 'coherence_drop', 'error', 'token_spike', 'latent_drift', 'unknown'
    evidence : dict
        Raw diagnostics from the exhaust plus optional concept alignment scores.
    recommended_strategies : list[str]
        Ordered list suitable for use as failure_map[failure_class] value.
    latent_concepts : list[tuple[str, float]]
        Top concept alignments from LatentDirectionProbe (empty if probe unavailable).
    """

    failure_class: str
    evidence: dict[str, Any] = field(default_factory=dict)
    recommended_strategies: list[str] = field(default_factory=list)
    latent_concepts: list[tuple[str, float]] = field(default_factory=list)

    @classmethod
    def from_exhaust(
        cls,
        exhaust: ExecutionExhaust,
        *,
        latent_vector: np.ndarray | None = None,
        probe: Any = None,  # cohezion.flume.diversity.LatentDirectionProbe | None
    ) -> OuroborosAttribution:
        """Derive a typed failure class and evidence from an ExecutionExhaust.

        Parameters
        ----------
        exhaust:
            The ExecutionExhaust emitted by OuroborosEngine.
        latent_vector:
            Optional 256D FLUME vector for the failed execution. When provided
            and a fitted LatentDirectionProbe is supplied, concept alignments
            are added to evidence.
        probe:
            Optional LatentDirectionProbe. Must have .fitted == True to be used.
        """
        # Rule-based failure class from exhaust fields (deterministic, zero model calls)
        if exhaust.error_message:
            failure_class = "error"
            strategies = ["reduce_context", "retry_with_fallback", "escalate"]
        elif exhaust.coherence_drop > 0.5:
            failure_class = "coherence_drop"
            strategies = ["reduce_context", "increase_temperature", "retry_with_fallback"]
        elif exhaust.token_usage > 8000:
            failure_class = "token_spike"
            strategies = ["summarize_first", "reduce_context", "escalate"]
        else:
            failure_class = "unknown"
            strategies = ["retry_with_fallback", "escalate"]

        evidence: dict[str, Any] = {
            "task_id": exhaust.task_id,
            "error_message": exhaust.error_message,
            "coherence_drop": exhaust.coherence_drop,
            "token_usage": exhaust.token_usage,
        }
        evidence.update(exhaust.diagnostics)

        latent_concepts: list[tuple[str, float]] = []
        if latent_vector is not None and probe is not None:
            try:
                if getattr(probe, "fitted", False):
                    latent_concepts = probe.top_concepts(latent_vector, k=3)
                    evidence["latent_concepts"] = latent_concepts
                    # Refine failure class when latent evidence provides signal
                    if latent_concepts and failure_class == "unknown":
                        top_concept = latent_concepts[0][0]
                        if top_concept:
                            failure_class = f"latent_drift:{top_concept}"
                            strategies = [
                                "probe_latent_space",
                                "reduce_context",
                                "retry_with_fallback",
                            ]
            except Exception:
                pass  # probe failure must never surface to caller

        return cls(
            failure_class=failure_class,
            evidence=evidence,
            recommended_strategies=strategies,
            latent_concepts=latent_concepts,
        )


def _emit_healing_event(exhaust: ExecutionExhaust, new_rule: str) -> None:
    """Emit a HEALING_EVENT PrecipitationEvent. Best effort."""
    try:
        from cohezion.precipitation import (
            PrecipitationEvent,
            PrecipitationKind,
            emit,
        )

        # Healing coherence: higher recovery = higher coherence. We use (1 - coherence_drop).
        recovery_coherence = max(0.0, min(1.0, 1.0 - exhaust.coherence_drop))
        emit(
            PrecipitationEvent(
                kind=PrecipitationKind.HEALING_EVENT,
                universe_id="ouroboros",
                coherence=recovery_coherence,
                payload={
                    "source_task": exhaust.task_id,
                    "error_message": exhaust.error_message,
                    "coherence_drop": exhaust.coherence_drop,
                    "token_usage": exhaust.token_usage,
                    "new_rule": new_rule,
                    "diagnostics": exhaust.diagnostics,
                },
            )
        )
    except Exception:
        logger.debug("Precipitation emit failed for HEALING_EVENT", exc_info=True)
