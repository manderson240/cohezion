"""JourneyNexus service — orchestration façade for FLUME/Quadrature/Omni (stub).

Exports consumed by:
  - tests/api/test_journey_nexus.py
  - tests/api/test_journey_nexus_router.py
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EVOEvent:
    """A single event in an EVO stream."""

    id: str
    timestamp: float
    z_256: list[float]
    state_12d: list[float]
    kind: str
    voice: str
    score: float
    journey_id: str


@dataclass
class QuadratureOutcome:
    """Result of a Quadrature Nexus consensus vote."""

    approved: bool
    consensus_score: float
    alignment_score: float
    voice_responses: list[Any] = field(default_factory=list)
    rejection_reason: str | None = None


@dataclass
class OmniChatOutcome:
    """Result of an Omni chat completion."""

    text: str
    model: str = ""
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    tool_calls: list[Any] = field(default_factory=list)
    images_b64: list[str] = field(default_factory=list)
    audio_b64: str = ""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class NarrateResult:
    """Result of a journey narration (text + audio + optional image)."""

    journey_id: str
    text: str
    audio_b64: str
    coherence: float
    image_b64: str | None = None


class JourneyNexus:
    """Orchestration façade for FLUME VAE, Quadrature Nexus, and Omni Tier."""

    def __init__(self) -> None:
        self._events: list[EVOEvent] = []

    def add_event(self, event: EVOEvent) -> None:
        """Append *event* to the in-memory EVO stream."""
        self._events.append(event)

    async def subscribe(
        self,
        *,
        journey_id: str | None = None,
    ) -> AsyncIterator[EVOEvent]:
        """Yield events, optionally filtered by *journey_id*."""
        for e in self._events:
            if journey_id is None or e.journey_id == journey_id:
                yield e

    async def narrate(self, journey_id: str) -> NarrateResult:
        """Generate a narration for *journey_id*."""
        raise NotImplementedError

    async def chat(self, message: str, *, journey_id: str | None = None) -> OmniChatOutcome:
        """Route *message* through the Omni Tier."""
        raise NotImplementedError

    async def quadrature_vote(
        self,
        proposal: Any,
        *,
        journey_id: str | None = None,
    ) -> QuadratureOutcome:
        """Run a Quadrature Nexus consensus vote on *proposal*."""
        raise NotImplementedError
