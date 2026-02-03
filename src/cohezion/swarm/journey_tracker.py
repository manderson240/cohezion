"""
Agent Journey Tracker - Record agent thought trajectories in 12D physics space.

Tracks:
- Agent activations (analyst, critic, synthesizer)
- Thought vectors at each step
- Physics state evolution
- Critique/resolution events
"""

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from cohezion.db.surreal_client import PhysicsState, SurrealClient, UniverseNode


@dataclass
class JourneyMetrics:
    """Anthropic-style capability and performance metrics."""

    context_utilization: float = 0.0  # 0.0 to 1.0
    latent_coherence: float = 0.0  # 0.0 to 1.0
    capability_delta: float = 0.0  # Improvement in understanding
    latency_per_token_ms: float = 0.0
    safety_alignment_score: float = 0.0
    computational_relativity_factor: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgentType(Enum):
    ANALYST = "analyst"
    CRITIC = "critic"
    SYNTHESIZER = "synthesizer"


@dataclass
class JourneyStep:
    """A single step in an agent's journey."""

    timestamp: str
    agent_type: str
    agent_name: str
    perspective: str | None
    input_summary: str
    output_summary: str
    physics_state: dict[str, float]
    duration_ms: float
    confidence: float
    metrics: JourneyMetrics = field(default_factory=JourneyMetrics)
    historical_context: str | None = None  # Link to previous SNAPSHOT or JOURNEY

    def to_dict(self) -> dict:
        d = asdict(self)
        d["metrics"] = self.metrics.to_dict()
        return d


@dataclass
class AgentJourney:
    """Complete journey of a debate/query through the agent swarm."""

    journey_id: str
    query: str
    started_at: str
    steps: list[JourneyStep] = field(default_factory=list)
    final_response: str | None = None
    total_duration_ms: float = 0.0
    final_confidence: float = 0.0
    aggregate_metrics: JourneyMetrics = field(default_factory=JourneyMetrics)
    previous_snapshot_id: str | None = None

    def add_step(self, step: JourneyStep) -> None:
        self.steps.append(step)
        self.total_duration_ms += step.duration_ms

    def to_dict(self) -> dict:
        return {
            "journey_id": self.journey_id,
            "query": self.query,
            "started_at": self.started_at,
            "steps": [s.to_dict() for s in self.steps],
            "final_response": self.final_response,
            "total_duration_ms": self.total_duration_ms,
            "final_confidence": self.final_confidence,
            "aggregate_metrics": self.aggregate_metrics.to_dict(),
            "step_count": len(self.steps),
        }


class JourneyTracker:
    """
    Tracks agent journeys through the swarm.

    Records:
    - Step-by-step agent activations
    - Physics state at each step
    - Saves to universe_nodes for visualization
    """

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or Path(
            "src/cohezion/knowledge_graph/universe_nodes/journeys"
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._current_journey: AgentJourney | None = None
        self._journeys: list[AgentJourney] = []

    def start_journey(self, query: str) -> str:
        """Start tracking a new journey."""
        journey_id = f"journey_{int(time.time() * 1000)}"
        self._current_journey = AgentJourney(
            journey_id=journey_id,
            query=query,
            started_at=datetime.now(UTC).isoformat(),
        )
        return journey_id

    def record_step(
        self,
        agent_type: AgentType,
        agent_name: str,
        perspective: str | None,
        input_text: str,
        output_text: str,
        physics_state: dict[str, float],
        duration_ms: float,
        confidence: float = 0.0,
        metrics: JourneyMetrics | None = None,
    ) -> None:
        """Record a step in the current journey."""
        if not self._current_journey:
            return

        step = JourneyStep(
            timestamp=datetime.now(UTC).isoformat(),
            agent_type=agent_type.value,
            agent_name=agent_name,
            perspective=perspective,
            input_summary=input_text[:200] + "..."
            if len(input_text) > 200
            else input_text,
            output_summary=output_text[:200] + "..."
            if len(output_text) > 200
            else output_text,
            physics_state=physics_state,
            duration_ms=duration_ms,
            confidence=confidence,
            metrics=metrics or JourneyMetrics(),
        )
        self._current_journey.add_step(step)

    async def end_journey(
        self,
        final_response: str,
        final_confidence: float,
        aggregate_metrics: JourneyMetrics | None = None,
    ) -> AgentJourney:
        """Complete the current journey and save it."""
        if not self._current_journey:
            raise ValueError("No active journey")

        self._current_journey.final_response = final_response
        self._current_journey.final_confidence = final_confidence
        if aggregate_metrics:
            self._current_journey.aggregate_metrics = aggregate_metrics

        # Save to file
        journey_file = self.output_dir / f"{self._current_journey.journey_id}.json"
        with open(journey_file, "w") as f:
            json.dump(self._current_journey.to_dict(), f, indent=2)

        self._journeys.append(self._current_journey)
        completed = self._current_journey
        self._current_journey = None

        # Offload to SurrealDB
        try:
            db = SurrealClient()
            await self._offload_to_db(completed, db)
        except Exception as e:
            print(f"Failed to offload journey to SurrealDB: {e}")

        return completed

    async def _offload_to_db(self, journey: AgentJourney, db: SurrealClient):
        await db.connect()
        node = UniverseNode(
            id=journey.journey_id,
            content=f"Journey for query: {journey.query}\nFinal Response: {journey.final_response}",
            node_type="journey",
            physics_state=PhysicsState(
                control=journey.final_confidence,
                time=journey.total_duration_ms / 1000.0,
                logic=float(len(journey.steps)) / 10.0,
            ),
            metadata=journey.to_dict(),
        )
        await db.store_node(node)
        await db.close()

    def get_recent_journeys(self, limit: int = 10) -> list[dict]:
        """Get recent journeys for visualization."""
        journey_files = sorted(self.output_dir.glob("*.json"), reverse=True)[:limit]
        journeys = []
        for f in journey_files:
            try:
                journeys.append(json.loads(f.read_text()))
            except Exception:
                pass
        return journeys

    def get_journey_trajectory(self, journey_id: str) -> list[dict]:
        """Get physics trajectory for a specific journey."""
        journey_file = self.output_dir / f"{journey_id}.json"
        if not journey_file.exists():
            return []

        journey = json.loads(journey_file.read_text())
        return [
            {
                "step": i,
                "agent": step["agent_name"],
                "physics": step["physics_state"],
            }
            for i, step in enumerate(journey.get("steps", []))
        ]


# Singleton
_tracker: JourneyTracker | None = None


def get_journey_tracker() -> JourneyTracker:
    global _tracker
    if _tracker is None:
        _tracker = JourneyTracker()
    return _tracker
