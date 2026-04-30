"""
SurrealDB Journey Repository - Concrete implementation using SurrealDB.
"""

import logging
from datetime import datetime, timedelta

from cohezion.core.persistence.repositories.journey_repository import (
    AgentJourney,
    JourneyMetrics,
    JourneyRepository,
)
from cohezion.core.persistence.surreal_client import SurrealClient


logger = logging.getLogger(__name__)


class SurrealJourneyRepository(JourneyRepository):
    """Concrete implementation of JourneyRepository for SurrealDB."""

    def __init__(self, client: SurrealClient):
        self._client = client
        self._table = "agent_journeys"

    async def add(self, journey: AgentJourney) -> str:
        """Add a new journey to SurrealDB."""
        try:
            # Convert to dict for SurrealDB
            data = {
                "id": f"{self._table}:{journey.journey_id}",
                "journey_id": journey.journey_id,
                "query": journey.query,
                "started_at": journey.started_at,
                "final_response": journey.final_response,
                "final_confidence": journey.final_confidence,
                "total_duration_ms": journey.total_duration_ms,
                "metrics": {
                    "context_utilization": journey.aggregate_metrics.context_utilization,
                    "latent_coherence": journey.aggregate_metrics.latent_coherence,
                    "capability_delta": journey.aggregate_metrics.capability_delta,
                    "latency_per_token_ms": journey.aggregate_metrics.latency_per_token_ms,
                    "safety_alignment_score": journey.aggregate_metrics.safety_alignment_score,
                    "computational_relativity_factor": (
                        journey.aggregate_metrics.computational_relativity_factor
                    ),
                },
                "steps": journey.steps,
                "metadata": journey.metadata,
                "created_at": datetime.now().isoformat(),
            }

            query = f"CREATE {self._table} CONTENT $data"
            logger.info(f"💾 Repository: Executing {query} (ID in data)")
            await self._client.query(query, {"data": data})
            return journey.journey_id

        except Exception as e:
            logger.error(f"Failed to add journey to SurrealDB: {e}")
            raise

    async def get(self, journey_id: str) -> AgentJourney | None:
        """Retrieve a journey by ID."""
        try:
            # Proper SurrealDB ID selection using backticks if needed, or direct access
            query = f"SELECT * FROM `{self._table}:{journey_id}`"
            result = await self._client.query(query)

            if not result or not result[0].get("result"):
                return None

            data = result[0]["result"][0]
            return self._dict_to_journey(data)

        except Exception as e:
            logger.error(f"Failed to get journey from SurrealDB: {e}")
            return None

    async def get_recent(self, hours: int = 24, limit: int = 20) -> list[AgentJourney]:
        """Retrieve recent journeys."""
        try:
            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            query = (
                f"SELECT * FROM {self._table} WHERE created_at > $cutoff ORDER BY created_at DESC "
                f"LIMIT {limit}"
            )
            result = await self._client.query(query, {"cutoff": cutoff})

            if not result or not result[0].get("result"):
                return []

            return [self._dict_to_journey(d) for d in result[0]["result"]]

        except Exception as e:
            logger.error(f"Failed to get recent journeys from SurrealDB: {e}")
            return []

    def _dict_to_journey(self, data: dict) -> AgentJourney:
        """Helper to convert SurrealDB dict to AgentJourney."""
        metrics_data = data.get("metrics", {})
        metrics = JourneyMetrics(
            context_utilization=metrics_data.get("context_utilization", 0.0),
            latent_coherence=metrics_data.get("latent_coherence", 0.0),
            capability_delta=metrics_data.get("capability_delta", 0.0),
            latency_per_token_ms=metrics_data.get("latency_per_token_ms", 0.0),
            safety_alignment_score=metrics_data.get("safety_alignment_score", 0.0),
            computational_relativity_factor=metrics_data.get(
                "computational_relativity_factor", 1.0
            ),
        )

        return AgentJourney(
            journey_id=data.get("id", "").split(":")[-1],
            query=data.get("query", ""),
            started_at=data.get("started_at", ""),
            final_response=data.get("final_response"),
            final_confidence=data.get("final_confidence", 0.0),
            total_duration_ms=data.get("total_duration_ms", 0.0),
            aggregate_metrics=metrics,
            steps=data.get("steps", []),
            metadata=data.get("metadata", {}),
        )
