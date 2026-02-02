"""
Journey Repository - Abstract and Dataclass definitions for agentic journeys.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional
from abc import ABC, abstractmethod


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
class AgentJourney:
    """A trace of an agent's reasoning and action path."""
    journey_id: str
    query: str
    started_at: str
    final_response: Optional[str] = None
    final_confidence: float = 0.0
    total_duration_ms: float = 0.0
    aggregate_metrics: JourneyMetrics = field(default_factory=JourneyMetrics)
    steps: List[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class JourneyRepository(ABC):
    """Abstract base class for journey persistence."""

    @abstractmethod
    async def add(self, journey: AgentJourney) -> str:
        """Add a new journey to persistence."""
        pass

    @abstractmethod
    async def get(self, journey_id: str) -> Optional[AgentJourney]:
        """Retrieve a journey by ID."""
        pass

    @abstractmethod
    async def get_recent(self, hours: int = 24, limit: int = 20) -> List[AgentJourney]:
        """Retrieve recent journeys."""
        pass
