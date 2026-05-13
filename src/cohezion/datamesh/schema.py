"""Unified schema for Cohezion datamesh.

Unifies data models across:
- Wiki (Karpathy pattern)
- FLUME (256D embeddings)
- SurrealDB (12D physics)
- MIRIX (6 memory types)
- Ouroboros (exhaust/rewrite events)

Charter: Single source of truth with full lineage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any
from uuid import UUID, uuid4

import torch


class RecordType(Enum):
    """Unified record types across all domains."""

    # Wiki types
    WIKI_PAGE = auto()
    RAW_SOURCE = auto()
    CONCEPT = auto()
    ENTITY = auto()
    SYNTHESIS = auto()

    # FLUME types
    EMBEDDING = auto()
    TRAJECTORY = auto()
    MANIFOLD_POINT = auto()

    # SurrealDB types
    UNIVERSE_NODE = auto()
    PHYSICS_STATE = auto()
    AGENT_STATE = auto()

    # MIRIX types
    EPISODIC_MEMORY = auto()
    SEMANTIC_MEMORY = auto()
    CORE_MEMORY = auto()
    KNOWLEDGE_VAULT = auto()

    # Ouroboros types
    EXHAUST = auto()
    REWRITE = auto()
    PATTERN = auto()
    IMPROVEMENT = auto()


class RelationType(Enum):
    """Unified relation types for graph connections."""

    DERIVES_FROM = auto()
    RELATES_TO = auto()
    CONTRADICTS = auto()
    SUPPORTS = auto()
    PRECEDES = auto()
    TRANSFORMS = auto()
    AUTHORED_BY = auto()
    EXECUTES_IN = auto()
    LEARNS_FROM = auto()
    IMPROVES = auto()
    REFERENCES = auto()
    INCLUDES = auto()


@dataclass(frozen=True)
class Physics12D:
    """12D physics state (3 spatial + time + 8 brane).

    HIHO (0.5) is the attractor state where all dimensions align.
    """

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    time: float = 0.0
    physics: float = 0.0  # Energy/mass
    biology: float = 0.0  # Organic signatures
    logic: float = 0.0  # Semantic structure
    quantum: float = 0.0  # Uncertainty
    field: float = 0.0  # Influence weight
    control: float = 0.0  # Governance
    novelty: float = 0.0  # Innovation
    precipitation: float = 0.0  # Commence/value

    @property
    def coherence(self) -> float:
        """Calculate HIHO coherence (0.5 is equilibrium)."""
        import math

        r = math.sqrt(self.x**2 + self.y**2 + self.z**2)
        t = abs(self.time) / 1000.0  # Normalize
        b = (
            sum(
                [
                    self.physics,
                    self.biology,
                    self.logic,
                    self.quantum,
                    self.field,
                    self.control,
                    self.novelty,
                    self.precipitation,
                ]
            )
            / 8.0
        )
        return 0.5 + (r * 0.25) + (t * 0.25) - (b * 0.25)


@dataclass(frozen=True)
class Embedding256D:
    """256D FLUME latent vector."""

    vector: torch.Tensor
    model: str = "flume_v1"

    def __post_init__(self):
        if self.vector.shape[0] != 256:
            raise ValueError(f"Expected 256D, got {self.vector.shape}")

    def similarity(self, other: Embedding256D) -> float:
        """Cosine similarity in latent space."""
        return torch.nn.functional.cosine_similarity(self.vector.unsqueeze(0), other.vector.unsqueeze(0)).item()


@dataclass
class DataLineage:
    """Complete provenance for data records."""

    record_id: UUID
    origin: str  # Source system: "wiki", "flume", "surreal", "mirix", "ouroboros"
    created_at: datetime
    checksum: str  # Content hash

    # Transformations
    transformations: list[dict[str, Any]] = field(default_factory=list)

    # Graph relationships
    upstream: list[UUID] = field(default_factory=list)  # Parents
    downstream: list[UUID] = field(default_factory=list)  # Children

    # Context
    session_id: str | None = None
    agent_id: str | None = None
    task_id: str | None = None

    def add_parent(self, parent_id: UUID) -> None:
        """Link to upstream record."""
        if parent_id not in self.upstream:
            self.upstream.append(parent_id)

    def add_child(self, child_id: UUID) -> None:
        """Link to downstream record."""
        if child_id not in self.downstream:
            self.downstream.append(child_id)


@dataclass
class UnifiedRecord:
    """Universal record container for datamesh.

    All domain-specific records are normalized to this format
    for cross-domain queries and lineage tracking.
    """

    id: UUID = field(default_factory=uuid4)
    type: RecordType = RecordType.WIKI_PAGE

    # Core content
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # Domain-specific extensions
    physics_12d: Physics12D | None = None
    embedding_256d: Embedding256D | None = None

    # Graph relations
    relations: list[tuple[RelationType, UUID]] = field(default_factory=list)

    # Lineage
    lineage: DataLineage = field(
        default_factory=lambda: DataLineage(record_id=uuid4(), origin="unknown", created_at=datetime.now(), checksum="")
    )

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def compute_checksum(self) -> str:
        """Compute content hash for integrity."""
        import hashlib

        data = f"{self.type.name}:{self.content}:{self.metadata}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def to_surreal(self) -> dict[str, Any]:
        """Serialize to SurrealDB format."""
        return {
            "id": f"unified:{self.id}",
            "type": self.type.name,
            "content": self.content,
            "metadata": self.metadata,
            "physics": self.physics_12d.__dict__ if self.physics_12d else None,
            "created_at": self.created_at.isoformat(),
        }

    def to_wiki(self) -> dict[str, Any]:
        """Serialize to Wiki page format."""
        return {
            "title": self.metadata.get("title", "Untitled"),
            "content": self.content,
            "category": self.metadata.get("category", "unknown"),
            "tags": self.metadata.get("tags", []),
            "path": self.metadata.get("path", f"pages/{self.id}.md"),
        }


# Domain-specific record builders


@dataclass
class WikiRecordBuilder:
    """Build UnifiedRecord from wiki page."""

    @staticmethod
    def from_page(page, source: str = "wiki") -> UnifiedRecord:
        """Convert ObsidianWiki page to UnifiedRecord."""
        record = UnifiedRecord(
            type=RecordType.WIKI_PAGE,
            content=page.content,
            metadata={
                "title": page.title,
                "category": page.category,
                "tags": page.tags,
                "backlinks": page.backlinks,
                "path": str(page.path),
            },
            lineage=DataLineage(record_id=uuid4(), origin=source, created_at=page.created_at, checksum=""),
        )
        record.lineage.checksum = record.compute_checksum()
        return record


@dataclass
class FlumeRecordBuilder:
    """Build UnifiedRecord from FLUME embedding."""

    @staticmethod
    def from_embedding(embedding: torch.Tensor, source_text: str, model: str = "flume_v1") -> UnifiedRecord:
        """Convert FLUME embedding to UnifiedRecord."""
        return UnifiedRecord(
            type=RecordType.EMBEDDING,
            content=source_text,
            metadata={"model": model, "dim": embedding.shape[0]},
            embedding_256d=Embedding256D(vector=embedding, model=model),
            lineage=DataLineage(record_id=uuid4(), origin="flume", created_at=datetime.now(), checksum=""),
        )


@dataclass
class OuroborosRecordBuilder:
    """Build UnifiedRecord from execution exhaust."""

    @staticmethod
    def from_exhaust(exhaust, source: str = "ouroboros") -> UnifiedRecord:
        """Convert ExecutionExhaust to UnifiedRecord."""

        record = UnifiedRecord(
            type=RecordType.EXHAUST,
            content=f"Error: {exhaust.error_message}",
            metadata={
                "task_id": exhaust.task_id,
                "coherence_drop": exhaust.coherence_drop,
                "token_usage": exhaust.token_usage,
                "diagnostics": exhaust.diagnostics,
            },
            physics_12d=Physics12D(
                coherence=0.5 - exhaust.coherence_drop,
            ),
            lineage=DataLineage(record_id=uuid4(), origin=source, created_at=datetime.now(), checksum=""),
        )
        record.lineage.checksum = record.compute_checksum()
        return record
