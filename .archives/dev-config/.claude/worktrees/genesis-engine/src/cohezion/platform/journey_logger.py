"""
Journey persistence to SurrealDB with FLUME trajectories.
Constitution requirement: "All plans, milestones, learnings synced to platform memory"
"""

import uuid
from datetime import datetime

import numpy as np
from pydantic import BaseModel

from cohezion.core.persistence.surreal_client import get_surreal_client
from cohezion.flume.vae_encoder import get_encoder
from cohezion.platform.coherence_tracker import get_coherence_tracker


class Journey(BaseModel):
    """Platform journey record."""

    journey_id: str
    journey_type: str  # 'design', 'implementation', 'decision', 'health_check'
    timestamp: datetime
    coherence_at_start: float
    coherence_at_end: float
    hiho_stable: bool
    flume_trajectory: list[float]  # 256D latent state
    decisions_made: list[str]
    learnings_extracted: list[str]
    outcome: str
    metadata: dict


class JourneyLogger:
    """Log platform journeys to SurrealDB."""

    def __init__(self):
        self.db = get_surreal_client()
        self.vae = get_encoder()
        self.coherence_tracker = get_coherence_tracker()

    async def start_journey(self, journey_type: str, context: str) -> str:
        """
        Start a new journey and return journey_id.

        Charter: All significant platform operations are journeys
        that must be tracked with coherence progression.
        """

        journey_id = str(uuid.uuid4())

        # Measure starting coherence
        coherence_metrics = await self.coherence_tracker.measure_system_coherence()

        # Encode context in FLUME space
        flume_state = self.vae.encode(context)

        # Convert numpy array to list for JSON serialization
        if isinstance(flume_state, np.ndarray):
            flume_state = flume_state.tolist()

        # Create journey record
        await self.db.query(
            """
            CREATE platform_journeys CONTENT {
                journey_id: $journey_id,
                journey_type: $journey_type,
                started_at: $timestamp,
                coherence_at_start: $coherence_start,
                flume_state_start: $flume_state,
                status: 'in_progress'
            };
        """,
            {
                "journey_id": journey_id,
                "journey_type": journey_type,
                "timestamp": datetime.now().isoformat(),
                "coherence_start": coherence_metrics.coherence,
                "flume_state": flume_state,
            },
        )

        return journey_id

    async def log_decision(self, journey_id: str, decision: str, rationale: str):
        """Log a decision made during journey."""

        await self.db.query(
            """
            UPDATE platform_journeys
            SET decisions_made += [$decision]
            WHERE journey_id = $journey_id;
        """,
            {
                "journey_id": journey_id,
                "decision": {
                    "timestamp": datetime.now().isoformat(),
                    "decision": decision,
                    "rationale": rationale,
                },
            },
        )

    async def extract_learning(self, journey_id: str, learning: str, pattern_type: str):
        """Extract a learning from journey."""

        await self.db.query(
            """
            UPDATE platform_journeys
            SET learnings_extracted += [$learning]
            WHERE journey_id = $journey_id;
        """,
            {
                "journey_id": journey_id,
                "learning": {
                    "timestamp": datetime.now().isoformat(),
                    "learning": learning,
                    "pattern_type": pattern_type,
                },
            },
        )

    async def complete_journey(self, journey_id: str, outcome: str, context_end: str) -> Journey:
        """
        Complete journey and calculate final coherence.

        Returns complete Journey record with FLUME trajectory.
        """

        # Measure ending coherence
        coherence_metrics = await self.coherence_tracker.measure_system_coherence()

        # Encode ending context in FLUME space
        flume_state_end = self.vae.encode(context_end)

        # Convert numpy array to list for JSON serialization
        if isinstance(flume_state_end, np.ndarray):
            flume_state_end = flume_state_end.tolist()

        # Update journey record
        await self.db.query(
            """
            UPDATE platform_journeys
            SET
                completed_at = $timestamp,
                coherence_at_end = $coherence_end,
                flume_state_end = $flume_state_end,
                hiho_stable = $hiho_stable,
                outcome = $outcome,
                status = 'completed'
            WHERE journey_id = $journey_id;
        """,
            {
                "journey_id": journey_id,
                "timestamp": datetime.now().isoformat(),
                "coherence_end": coherence_metrics.coherence,
                "flume_state_end": flume_state_end,
                "hiho_stable": coherence_metrics.hiho_stable,
                "outcome": outcome,
            },
        )

        # Load complete journey
        result = await self.db.query(
            """
            SELECT * FROM platform_journeys
            WHERE journey_id = $journey_id;
        """,
            {"journey_id": journey_id},
        )

        journey_data = result[0]

        return Journey(
            journey_id=journey_data["journey_id"],
            journey_type=journey_data["journey_type"],
            timestamp=datetime.fromisoformat(journey_data["started_at"]),
            coherence_at_start=journey_data["coherence_at_start"],
            coherence_at_end=journey_data.get("coherence_at_end", 0.5),
            hiho_stable=journey_data.get("hiho_stable", False),
            flume_trajectory=journey_data.get("flume_state_end", []),
            decisions_made=[d["decision"] for d in journey_data.get("decisions_made", [])],
            learnings_extracted=[entry["learning"] for entry in journey_data.get("learnings_extracted", [])],
            outcome=journey_data.get("outcome", ""),
            metadata=journey_data.get("metadata", {}),
        )

    async def get_recent_journeys(self, journey_type: str | None = None, limit: int = 10) -> list[Journey]:
        """Get recent journeys, optionally filtered by type."""

        if journey_type:
            result = await self.db.query(
                """
                SELECT * FROM platform_journeys
                WHERE journey_type = $journey_type
                ORDER BY started_at DESC
                LIMIT $limit;
            """,
                {"journey_type": journey_type, "limit": limit},
            )
        else:
            result = await self.db.query(
                """
                SELECT * FROM platform_journeys
                ORDER BY started_at DESC
                LIMIT $limit;
            """,
                {"limit": limit},
            )

        journeys = []
        for j in result:
            journeys.append(
                Journey(
                    journey_id=j["journey_id"],
                    journey_type=j["journey_type"],
                    timestamp=datetime.fromisoformat(j["started_at"]),
                    coherence_at_start=j["coherence_at_start"],
                    coherence_at_end=j.get("coherence_at_end", 0.5),
                    hiho_stable=j.get("hiho_stable", False),
                    flume_trajectory=j.get("flume_state_end", []),
                    decisions_made=[d["decision"] for d in j.get("decisions_made", [])],
                    learnings_extracted=[entry["learning"] for entry in j.get("learnings_extracted", [])],
                    outcome=j.get("outcome", ""),
                    metadata=j.get("metadata", {}),
                )
            )
        return journeys


# Singleton accessor
_journey_logger = None


def get_journey_logger() -> JourneyLogger:
    """Get global journey logger instance."""
    global _journey_logger
    if _journey_logger is None:
        _journey_logger = JourneyLogger()
    return _journey_logger


def reset_journey_logger():
    """Reset global journey logger (for testing)."""
    global _journey_logger
    _journey_logger = None
