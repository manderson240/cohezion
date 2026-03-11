"""Immutable Provenance Hashing (Story 4.7, FR5).

Cryptographic proof of origin for every pattern and skill.
Each artifact gets a SHA-256 provenance hash that chains to its
source, creating an immutable audit trail.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class ProvenanceRecord:
    """An immutable provenance record for an artifact."""

    artifact_id: str
    artifact_type: str  # "pattern" | "skill" | "discovery"
    content_hash: str  # SHA-256 of content
    source: str  # Origin (e.g., "arxiv:2401.12345", "vault:decision-42")
    parent_hash: str | None = None  # Chain to previous version
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    @property
    def provenance_hash(self) -> str:
        """Compute the provenance hash chaining content to source."""
        payload = json.dumps(
            {
                "artifact_id": self.artifact_id,
                "content_hash": self.content_hash,
                "source": self.source,
                "parent_hash": self.parent_hash,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "content_hash": self.content_hash,
            "source": self.source,
            "parent_hash": self.parent_hash,
            "provenance_hash": self.provenance_hash,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class ProvenanceRegistry:
    """Registry of provenance records with chain verification."""

    def __init__(self) -> None:
        self._records: dict[str, ProvenanceRecord] = {}

    def register(
        self,
        artifact_id: str,
        artifact_type: str,
        content: str,
        source: str,
        parent_hash: str | None = None,
        metadata: dict | None = None,
    ) -> ProvenanceRecord:
        """Register an artifact with provenance tracking."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        record = ProvenanceRecord(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            content_hash=content_hash,
            source=source,
            parent_hash=parent_hash,
            metadata=metadata or {},
        )

        self._records[record.provenance_hash] = record
        logger.info(
            "Provenance registered: %s (%s) -> %s",
            artifact_id,
            artifact_type,
            record.provenance_hash[:16],
        )
        return record

    def verify(self, provenance_hash: str) -> bool:
        """Verify a provenance hash exists in the registry."""
        return provenance_hash in self._records

    def get_chain(self, provenance_hash: str) -> list[ProvenanceRecord]:
        """Walk the provenance chain back to the root."""
        chain: list[ProvenanceRecord] = []
        current = self._records.get(provenance_hash)
        while current is not None:
            chain.append(current)
            current = self._records.get(current.parent_hash) if current.parent_hash else None
        return chain

    def get_all(self) -> list[dict]:
        """Export all provenance records."""
        return [r.to_dict() for r in self._records.values()]
