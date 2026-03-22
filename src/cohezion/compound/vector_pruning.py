"""Vector Pruning & Compaction Engine (Story 3.6, FR8, NFR-3).

Manages vector density in the semantic space by applying decay
to low-relevance experiences. Keeps HNSW index performance constant
across long research horizons by archiving stale vectors.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)

DEFAULT_DECAY_RATE = 0.01  # Relevance decays by 1% per cycle
DEFAULT_PRUNE_THRESHOLD = 0.1  # Archive vectors below this relevance
DEFAULT_COMPACTION_TRIGGER = 50  # Trigger compaction after N cycles


@dataclass
class SemanticVector:
    """A vector in the semantic space with relevance tracking."""

    vector_id: str
    relevance: float  # 0.0-1.0, decays over time
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    archived: bool = False

    def decay(self, rate: float) -> None:
        """Apply time-based relevance decay."""
        self.relevance = max(0.0, self.relevance - rate)


@dataclass
class PruningReport:
    """Result of a pruning/compaction cycle."""

    vectors_pruned: int
    vectors_remaining: int
    avg_relevance: float
    timestamp: float = field(default_factory=time.time)


class VectorPruningEngine:
    """Manages semantic vector density through decay and compaction."""

    def __init__(
        self,
        decay_rate: float = DEFAULT_DECAY_RATE,
        prune_threshold: float = DEFAULT_PRUNE_THRESHOLD,
        compaction_trigger: int = DEFAULT_COMPACTION_TRIGGER,
    ) -> None:
        self._decay_rate = decay_rate
        self._prune_threshold = prune_threshold
        self._compaction_trigger = compaction_trigger
        self._vectors: dict[str, SemanticVector] = {}
        self._cycle_count = 0
        self._archive: list[SemanticVector] = []

    @property
    def active_count(self) -> int:
        return sum(1 for v in self._vectors.values() if not v.archived)

    @property
    def archived_count(self) -> int:
        return len(self._archive)

    def add_vector(self, vector_id: str, relevance: float = 1.0) -> SemanticVector:
        """Add a new vector to the space."""
        vec = SemanticVector(vector_id=vector_id, relevance=relevance)
        self._vectors[vector_id] = vec
        return vec

    def access(self, vector_id: str) -> None:
        """Record an access to a vector (refreshes relevance)."""
        vec = self._vectors.get(vector_id)
        if vec and not vec.archived:
            vec.access_count += 1
            vec.last_accessed = time.time()
            vec.relevance = min(1.0, vec.relevance + 0.05)

    def run_cycle(self) -> PruningReport:
        """Run one decay + pruning cycle."""
        self._cycle_count += 1

        # Apply decay to all active vectors
        for vec in self._vectors.values():
            if not vec.archived:
                vec.decay(self._decay_rate)

        # Prune low-relevance vectors
        pruned = 0
        for vec in self._vectors.values():
            if not vec.archived and vec.relevance < self._prune_threshold:
                vec.archived = True
                self._archive.append(vec)
                pruned += 1

        active = [v for v in self._vectors.values() if not v.archived]
        avg_rel = sum(v.relevance for v in active) / len(active) if active else 0.0

        report = PruningReport(
            vectors_pruned=pruned,
            vectors_remaining=len(active),
            avg_relevance=avg_rel,
        )

        if pruned > 0:
            logger.info(
                "Pruning cycle %d: %d vectors archived, %d remaining (avg=%.3f)",
                self._cycle_count,
                pruned,
                len(active),
                avg_rel,
            )

        return report

    def should_compact(self) -> bool:
        """Check if compaction should trigger."""
        return self._cycle_count >= self._compaction_trigger
