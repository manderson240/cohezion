"""
Training Data Capture System
============================
Captures every prompt/response interaction for training data generation.
Logs semantic analysis and agentic performance rankings.

Integrates with overnight_driver.py for continuous data collection.
"""

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class InteractionRecord:
    """Single prompt/response interaction."""

    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # Prompt details
    prompt: str = ""
    prompt_tokens: int = 0
    prompt_embedding: list[float] = field(default_factory=list)

    # Response details
    response: str = ""
    response_tokens: int = 0
    response_embedding: list[float] = field(default_factory=list)

    # Context
    model: str = ""
    agent_id: str = ""
    stream: str = ""
    step: int = 0

    # Quality metrics
    coherence: float = 0.0
    relevance: float = 0.0
    creativity: float = 0.0
    accuracy: float = 0.0

    # Performance
    latency_ms: int = 0
    success: bool = True
    error: str | None = None


@dataclass
class JourneyRecord:
    """Complete agent journey across multiple interactions."""

    id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: str = ""
    stream: str = ""
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ended_at: str | None = None

    # Interactions in this journey
    interaction_ids: list[str] = field(default_factory=list)

    # Journey metrics
    total_steps: int = 0
    avg_coherence: float = 0.0
    avg_latency_ms: float = 0.0
    success_rate: float = 0.0

    # Final outcome
    status: str = "in_progress"  # in_progress, completed, failed
    final_score: float = 0.0
    rank: int = 0  # Performance rank among all journeys


class TrainingDataCapture:
    """
    Captures and logs all interactions for training data generation.

    Outputs:
    - interactions.jsonl: Every prompt/response pair
    - journeys.jsonl: Agent journey summaries
    - rankings.json: Performance rankings
    """

    def __init__(self, output_dir: Path = Path("training_data")):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.interactions_path = output_dir / "interactions.jsonl"
        self.journeys_path = output_dir / "journeys.jsonl"
        self.rankings_path = output_dir / "rankings.json"

        self.active_journeys: dict[str, JourneyRecord] = {}
        self.all_journeys: list[JourneyRecord] = []

        logger.info(f"Training data capture initialized: {output_dir}")

    async def log_interaction(self, interaction: InteractionRecord) -> None:
        """Log a single interaction to the training data."""

        # Append to interactions file
        with open(self.interactions_path, "a") as f:
            f.write(json.dumps(asdict(interaction)) + "\n")

        # Update active journey
        journey_key = f"{interaction.agent_id}:{interaction.stream}"
        if journey_key in self.active_journeys:
            journey = self.active_journeys[journey_key]
            journey.interaction_ids.append(interaction.id)
            journey.total_steps += 1

        logger.debug(f"Logged interaction {interaction.id}")

    def start_journey(self, agent_id: str, stream: str) -> str:
        """Start tracking a new agent journey."""
        journey = JourneyRecord(agent_id=agent_id, stream=stream)
        journey_key = f"{agent_id}:{stream}"
        self.active_journeys[journey_key] = journey

        logger.info(f"Started journey {journey.id} for agent {agent_id}")
        return journey.id

    def end_journey(
        self,
        agent_id: str,
        stream: str,
        status: str = "completed",
        final_score: float = 0.0,
    ) -> JourneyRecord | None:
        """End and save a journey."""
        journey_key = f"{agent_id}:{stream}"

        if journey_key not in self.active_journeys:
            logger.warning(f"No active journey for {journey_key}")
            return None

        journey = self.active_journeys.pop(journey_key)
        journey.ended_at = datetime.now().isoformat()
        journey.status = status
        journey.final_score = final_score

        self.all_journeys.append(journey)

        # Save journey
        with open(self.journeys_path, "a") as f:
            f.write(json.dumps(asdict(journey)) + "\n")

        logger.info(f"Ended journey {journey.id} with status {status}")
        return journey

    def compute_rankings(self) -> list[dict]:
        """Compute performance rankings across all journeys."""

        # Sort by final score
        sorted_journeys = sorted(
            self.all_journeys, key=lambda j: j.final_score, reverse=True
        )

        rankings = []
        for rank, journey in enumerate(sorted_journeys, 1):
            journey.rank = rank
            rankings.append(
                {
                    "rank": rank,
                    "journey_id": journey.id,
                    "agent_id": journey.agent_id,
                    "stream": journey.stream,
                    "score": journey.final_score,
                    "steps": journey.total_steps,
                    "status": journey.status,
                }
            )

        # Save rankings
        with open(self.rankings_path, "w") as f:
            json.dump(rankings, f, indent=2)

        logger.info(f"Computed rankings for {len(rankings)} journeys")
        return rankings

    def get_stats(self) -> dict:
        """Get capture statistics."""
        interaction_count = 0
        if self.interactions_path.exists():
            with open(self.interactions_path) as f:
                interaction_count = sum(1 for _ in f)

        journey_count = 0
        if self.journeys_path.exists():
            with open(self.journeys_path) as f:
                journey_count = sum(1 for _ in f)

        return {
            "interactions": interaction_count,
            "journeys": journey_count,
            "active_journeys": len(self.active_journeys),
        }


class OvernightTrainingIntegration:
    """
    Integration with overnight_driver.py for continuous training data capture.
    """

    def __init__(self, capture: TrainingDataCapture):
        self.capture = capture
        self.embedder = None  # Optionally add embedding model

    async def wrap_llm_call(
        self, model: str, prompt: str, agent_id: str, stream: str, step: int, call_fn
    ) -> tuple[str, InteractionRecord]:
        """Wrap an LLM call to capture interaction data."""

        start_time = time.time()

        interaction = InteractionRecord(
            prompt=prompt, model=model, agent_id=agent_id, stream=stream, step=step
        )

        try:
            response = await call_fn(prompt)
            interaction.response = response
            interaction.success = True

            # Compute quality metrics (simplified)
            interaction.coherence = self._estimate_coherence(response)
            interaction.relevance = self._estimate_relevance(prompt, response)

        except Exception as e:
            interaction.success = False
            interaction.error = str(e)
            response = ""

        interaction.latency_ms = int((time.time() - start_time) * 1000)

        await self.capture.log_interaction(interaction)

        return response, interaction

    def _estimate_coherence(self, text: str) -> float:
        """Simple coherence estimate based on structure."""
        if not text:
            return 0.0

        # Simple heuristics
        score = 0.5
        if len(text) > 100:
            score += 0.1
        if "." in text:
            score += 0.1
        if "\n" in text:
            score += 0.1
        if any(word in text.lower() for word in ["because", "therefore", "thus"]):
            score += 0.1

        return min(1.0, score)

    def _estimate_relevance(self, prompt: str, response: str) -> float:
        """Simple relevance estimate based on keyword overlap."""
        if not prompt or not response:
            return 0.0

        prompt_words = set(prompt.lower().split())
        response_words = set(response.lower().split())

        overlap = len(prompt_words & response_words)
        total = len(prompt_words | response_words)

        return overlap / total if total > 0 else 0.0


# Example usage in overnight_driver.py:
"""
from training_data_capture import TrainingDataCapture, OvernightTrainingIntegration

capture = TrainingDataCapture(Path("training_data"))
integration = OvernightTrainingIntegration(capture)

# Start journey
capture.start_journey(agent_id="architect_001", stream="architect")

# Wrap LLM calls
response, record = await integration.wrap_llm_call(
    model="gemini-2.0-flash",
    prompt="Design a universe with quantum entanglement",
    agent_id="architect_001",
    stream="architect",
    step=1,
    call_fn=my_llm_call
)

# End journey
capture.end_journey("architect_001", "architect", status="completed", final_score=0.85)

# Get rankings
rankings = capture.compute_rankings()
"""
