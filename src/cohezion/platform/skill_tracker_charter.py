# long lines: SQL/URLs/docstrings — wrapping reduces readability
"""
Charter-aligned skill tracking with HIHO stability measurement.
Integrates Phase 0 infrastructure for 100% Charter compliance.
"""

import logging
import uuid
from datetime import datetime

import numpy as np
from pydantic import BaseModel

from cohezion.core.persistence.surreal_client import get_surreal_client
from cohezion.flume.vae_encoder import get_encoder
from cohezion.platform.coherence_tracker import get_coherence_tracker
from cohezion.platform.journey_logger import get_journey_logger


logger = logging.getLogger(__name__)


class SkillUsageEvent(BaseModel):
    """Single skill usage event with Charter metrics."""

    skill_name: str
    invoked_at: datetime
    execution_id: str
    tokens_used: int
    success: bool
    error_message: str | None = None
    latency_ms: float
    coherence_score: float  # Individual execution coherence
    hiho_stable: bool  # Was this execution HIHO stable?
    flume_state: list[float]  # 256D FLUME state at execution


class CharterAlignedSkillTracker:
    """Track skill usage with Charter compliance."""

    def __init__(self):
        self.db = get_surreal_client()
        self.coherence_tracker = get_coherence_tracker()
        self.journey_logger = get_journey_logger()
        self.vae = get_encoder()

    async def log_skill_usage(self, event: SkillUsageEvent, journey_id: str | None = None):
        """
        Log skill usage with Charter-compliant tracking.

        Charter Requirements:
        1. Measure against 0.5 HIHO baseline
        2. Track FLUME trajectory
        3. Persist to journey
        """

        # Check HIHO stability (Charter: 0.4-0.6 range)
        hiho_stable = 0.4 <= event.coherence_score <= 0.6

        # Update event
        event.hiho_stable = hiho_stable

        # Persist to SurrealDB
        try:
            await self.db.query(
                """
                CREATE skill_usage CONTENT {
                    skill_name: $skill_name,
                    invoked_at: $invoked_at,
                    execution_id: $execution_id,
                    tokens_used: $tokens_used,
                    success: $success,
                    error_message: $error_message,
                    latency_ms: $latency_ms,
                    coherence_score: $coherence_score,
                    hiho_stable: $hiho_stable,
                    flume_state: $flume_state,
                    journey_id: $journey_id
                };
            """,
                {
                    "skill_name": event.skill_name,
                    "invoked_at": event.invoked_at.isoformat(),
                    "execution_id": event.execution_id,
                    "tokens_used": event.tokens_used,
                    "success": event.success,
                    "error_message": event.error_message,
                    "latency_ms": event.latency_ms,
                    "coherence_score": event.coherence_score,
                    "hiho_stable": hiho_stable,
                    "flume_state": event.flume_state,
                    "journey_id": journey_id,
                },
            )
        except Exception as e:
            logger.warning("Failed to persist skill usage to SurrealDB: %s", e)

        # If HIHO unstable and journey exists, log as potential issue
        if not hiho_stable and journey_id:
            try:
                await self.journey_logger.extract_learning(
                    journey_id=journey_id,
                    learning=f"Skill {event.skill_name} executed outside HIHO range: {event.coherence_score:.3f}",
                    pattern_type="hiho_violation",
                )
            except Exception as e:
                logger.warning("Failed to log HIHO violation to journey: %s", e)

    async def create_skill_usage_event(
        self,
        skill_name: str,
        tokens_used: int,
        success: bool,
        latency_ms: float,
        coherence_before: float,
        coherence_after: float,
        prompt: str,
        error_message: str | None = None,
    ) -> SkillUsageEvent:
        """
        Create a skill usage event with Charter metrics.

        Args:
            skill_name: Name of the skill executed
            tokens_used: Number of tokens consumed
            success: Whether execution succeeded
            latency_ms: Execution time in milliseconds
            coherence_before: System coherence before execution
            coherence_after: System coherence after execution
            prompt: The prompt that was executed
            error_message: Optional error message if failed

        Returns:
            SkillUsageEvent with computed Charter metrics
        """

        # Calculate execution coherence (how much coherence changed?)
        # Lower change = better coherence preservation
        execution_coherence = 1.0 - abs(coherence_after - coherence_before)

        # Encode prompt in FLUME space
        flume_state = self.vae.encode(prompt)

        # Convert numpy array to list for JSON serialization
        if isinstance(flume_state, np.ndarray):
            flume_state = flume_state.tolist()

        # Create event
        return SkillUsageEvent(
            skill_name=skill_name,
            invoked_at=datetime.now(),
            execution_id=str(uuid.uuid4()),
            tokens_used=tokens_used,
            success=success,
            error_message=error_message,
            latency_ms=latency_ms,
            coherence_score=execution_coherence,
            hiho_stable=(0.4 <= execution_coherence <= 0.6),
            flume_state=flume_state,
        )


# Singleton accessor
_skill_tracker = None


def get_skill_tracker() -> CharterAlignedSkillTracker:
    """Get global Charter-aligned skill tracker instance."""
    global _skill_tracker
    if _skill_tracker is None:
        _skill_tracker = CharterAlignedSkillTracker()
    return _skill_tracker


def reset_skill_tracker():
    """Reset global skill tracker (for testing)."""
    global _skill_tracker
    _skill_tracker = None
