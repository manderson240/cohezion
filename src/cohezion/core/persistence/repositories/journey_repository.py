"""
Journey Repository - Abstract and Dataclass definitions for agentic journeys.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class JourneyMetrics:
    """Quantitative metrics for a single journey."""

    context_utilization: float = 0.0
    latent_coherence: float = 0.0
    capability_delta: float = 0.0
    latency_per_token_ms: float = 0.0
    safety_alignment_score: float = 0.0
    computational_relativity_factor: float = 1.0


@dataclass
class JourneyStep:
    """A single step in an agent's journey."""

    timestamp: str
    agent_type: str
    agent_name: str
    perspective: str | None
    input_summary: str
    output_summary: str
    physics_state: dict
    duration_ms: float
    confidence: float
    metrics: JourneyMetrics = field(default_factory=JourneyMetrics)
    historical_context: str | None = None


@dataclass
class AgentJourney:
    """A trace of an agent's reasoning and action path."""

    journey_id: str
    query: str
    started_at: str
    final_response: str | None = None
    final_confidence: float = 0.0
    total_duration_ms: float = 0.0
    aggregate_metrics: JourneyMetrics = field(default_factory=JourneyMetrics)
    steps: list[JourneyStep] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def add_step(self, step: JourneyStep) -> None:
        """Add a step to the journey."""
        self.steps.append(step)


class JourneyRepository(ABC):
    """Abstract base class for journey persistence."""

    @abstractmethod
    async def add(self, journey: AgentJourney) -> str:
        """Add a new journey to persistence."""
        pass

    @abstractmethod
    async def get(self, journey_id: str) -> AgentJourney | None:
        """Retrieve a journey by ID."""
        pass

    @abstractmethod
    async def get_recent(self, hours: int = 24, limit: int = 20) -> list[AgentJourney]:
        """Retrieve recent journeys."""
        pass
