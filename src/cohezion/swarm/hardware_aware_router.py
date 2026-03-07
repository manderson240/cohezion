"""Hardware-aware intelligent model routing system.

Provides core routing decision types and adapters for adaptive model selection
based on real-time hardware metrics, thermal management, and model profiles.

This module defines the data structures used by routing adapters and profiles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Priority(Enum):
    """Request priority levels for routing decisions.

    Priorities affect model selection and resource allocation, with HIGH priority
    requests being routed to faster models or getting priority queue positions.
    """

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RoutingRequest:
    """Input request for hardware-aware routing decisions.

    Attributes
    ----------
    request_id : str
        Unique identifier for this routing request
    prompt : str
        The actual prompt text being processed
    system : str | None
        Optional system prompt
    task_type : str
        Category of task (coding, analysis, creative, etc.)
    prompt_tokens : int
        Token count for the prompt
    expected_output_tokens : int
        Estimated output tokens needed
    target_latency_ms : float | None
        Desired response latency (None = no constraint)
    """

    request_id: str
    prompt: str
    system: str | None
    task_type: str
    prompt_tokens: int
    expected_output_tokens: int
    target_latency_ms: float | None = None


@dataclass
class RoutingDecision:
    """Decision output from hardware-aware routing logic.

    Represents the routing decision for a single request, including the
    primary model choice, fallback chain, and metadata about the decision.

    Attributes
    ----------
    request_id : str
        Unique identifier for this routing decision
    primary_model : str
        Selected model name (must be registered with Ollama)
    fallback_chain : list[str]
        Ordered list of fallback models if primary fails
    confidence : float
        Decision confidence (0.0-1.0), used for logging and observability
    predicted_tps : float
        Predicted tokens-per-second for primary model under current conditions
    predicted_latency_ms : float
        Predicted response latency in milliseconds
    reasoning : str
        Human-readable explanation of why this model was selected
    """

    request_id: str
    primary_model: str
    fallback_chain: list[str] = field(default_factory=list)
    confidence: float = 1.0
    predicted_tps: float = 0.0
    predicted_latency_ms: float = 0.0
    reasoning: str = ""

    @property
    def name(self) -> str:
        """Alias for primary_model to match expected interface.

        TokenEfficientClient and other routing interfaces expect a `.name`
        attribute on routing decisions. This property provides compatibility.
        """
        return self.primary_model

    def to_dict(self) -> dict[str, Any]:
        """Export decision to dictionary for logging and persistence.

        Returns
        -------
        dict[str, Any]
            Dictionary representation with all decision fields
        """
        return {
            "request_id": self.request_id,
            "primary_model": self.primary_model,
            "fallback_chain": self.fallback_chain,
            "confidence": self.confidence,
            "predicted_tps": self.predicted_tps,
            "predicted_latency_ms": self.predicted_latency_ms,
            "reasoning": self.reasoning,
        }


__all__ = [
    "Priority",
    "RoutingDecision",
    "RoutingRequest",
]
