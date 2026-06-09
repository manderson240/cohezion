"""Core types for the Swarm system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Perspective(Enum):
    """Analyst perspective types for multi-view analysis."""

    TECHNICAL = "technical"
    ETHICAL = "ethical"
    HISTORICAL = "historical"
    EMPIRICAL = "empirical"
    METAPHYSICAL = "metaphysical"


@dataclass
class ThoughtVector:
    """
    A compressed representation of an analyst's reasoning.

    In CALM terms, this is the continuous vector z that represents
    a paragraph of thought, enabling fluid cognitive motion.
    """

    perspective: Perspective
    content: str
    embedding: list[float] | None = None
    phi_score: float = 0.0
    confidence: float = 0.0
    frequency_count: int = 1
    persistence_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "perspective": self.perspective.value,
            "content": self.content,
            "embedding": self.embedding,
            "phi_score": self.phi_score,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class Contradiction:
    """A detected contradiction between analyst outputs."""

    source_perspectives: tuple[Perspective, Perspective]
    description: str
    severity: float  # 0.0 to 1.0
    suggested_resolution: str | None = None


@dataclass
class CritiqueResult:
    """
    The output from the Critic agent's review of analyst outputs.

    Contains detected contradictions and logical issues.
    """

    analyst_outputs: list[ThoughtVector]
    contradictions: list[Contradiction] = field(default_factory=list)
    logical_issues: list[str] = field(default_factory=list)
    overall_coherence: float = 0.0  # 0.0 to 1.0
    recommendation: str = ""

    @property
    def has_issues(self) -> bool:
        return len(self.contradictions) > 0 or len(self.logical_issues) > 0


@dataclass
class SynthesizedResponse:
    """
    The final synthesized output from the Swarm.

    Resolves contradictions and produces a coherent response.
    """

    content: str
    source_critique: CritiqueResult
    resolution_notes: list[str] = field(default_factory=list)
    confidence: float = 0.0
    processing_time_ms: float = 0.0
    frequency_count: int = 1
    persistence_id: str | None = None
    model_chain: list[str] = field(default_factory=list)  # Models used in order

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "confidence": self.confidence,
            "processing_time_ms": self.processing_time_ms,
            "model_chain": self.model_chain,
            "resolution_notes": self.resolution_notes,
            "had_contradictions": self.source_critique.has_issues,
        }


@dataclass
class SwarmConfig:
    """Configuration for the SLM Swarm."""

    analyst_model: str = "phi4"
    critic_model: str = "deepseek-r1:7b"
    synthesizer_model: str = "qwen2.5-coder:7b"
    architect_model: str = "deepseek-r1:7b"

    # Parallel execution settings
    max_concurrent_analysts: int = 3
    analyst_timeout_seconds: float = 30.0
    critic_timeout_seconds: float = 20.0
    synthesizer_timeout_seconds: float = 45.0

    # Memory settings
    max_ram_gb: float = 120.0  # Reserve 8GB for OS
    cache_ttl_seconds: int = 3600

    # Lemonade router connection (canonical: :13305)
    lemonade_router_url: str = "http://localhost:13305"

    # Deprecated: kept for backward-compat; prefer lemonade_router_url.
    # Phase 4 retirement target per docs/plans/2026-06-09-lemonade-13305-consolidation.md
    ollama_base_url: str = "http://localhost:11434"  # allow-direct-port: deprecated alias — callers migrate via lemonade_router_url (R6)

    # Phase # Security
    strict_security: bool = False

    # MRP Settings
    mrp_sync: bool = True
    mrp_pulse_interval_minutes: int = 30

    # Degradation
    degraded_mode: bool = False

    # Autonomic Refinement
    max_refinement_rounds: int = 3
    min_phi_threshold: float = 0.75  # The Stability Well barrier
    semantic_cache_threshold: float = 0.95

    # Resource Priority (1=Critical, 4=Low)
    priority: int = 3
