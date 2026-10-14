"""Canonical Evidence Algebra and Unknown Ledger for Reverse Engineering.
========================================================================
Reference: morluto/rea (Reverse Engineer Anything).

Core Architectural Invariants:
1. Canonical Evidence Records:
   Every inspection produces an immutable, content-addressed Evidence record.
2. Facet Availability:
   Distinguishes observed absence from unsupported provider capability.
3. Provenance Guardrails:
   Tags untrusted target content (disassembly, extracted strings, page text)
   with provenance markers to protect agents from indirect prompt injection.
4. Unknown Ledger:
   Models reverse engineering as progressive resolution of questions and hypotheses.
"""

from __future__ import annotations

import enum
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FacetAvailability:
    """Explicit declaration of facet observation coverage."""

    available: bool
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"available": self.available}
        if self.reason:
            d["reason"] = self.reason
        return d


@dataclass
class ProvenanceMarker:
    """Security provenance metadata guarding against indirect prompt injection."""

    untrusted_content: bool = True
    source: str = "analysis_target"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "untrusted_content": self.untrusted_content,
            "source": self.source,
        }


class UnknownStatus(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    INCONCLUSIVE = "inconclusive"


@dataclass
class UnknownItem:
    """A tracked hypothesis or unanswered question in the reverse engineering ledger."""

    unknown_id: str
    domain: str
    question: str
    status: UnknownStatus = UnknownStatus.OPEN
    resolution: Optional[str] = None
    evidence_links: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unknown_id": self.unknown_id,
            "domain": self.domain,
            "question": self.question,
            "status": self.status.value,
            "resolution": self.resolution,
            "evidence_links": self.evidence_links,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class UnknownLedger:
    """Progressive question and hypothesis manager for reverse engineering."""

    def __init__(self) -> None:
        self.items: Dict[str, UnknownItem] = {}

    def record_unknown(self, domain: str, question: str, evidence_id: Optional[str] = None) -> UnknownItem:
        """Record a new unknown question into the ledger."""
        u_hash = hashlib.sha256(f"{domain}:{question}".encode("utf-8")).hexdigest()[:12]
        links = [evidence_id] if evidence_id else []
        item = UnknownItem(
            unknown_id=f"unk_{u_hash}",
            domain=domain,
            question=question,
            status=UnknownStatus.OPEN,
            evidence_links=links,
        )
        self.items[item.unknown_id] = item
        return item

    def resolve_unknown(self, unknown_id: str, resolution: str, evidence_id: Optional[str] = None) -> Optional[UnknownItem]:
        """Resolve a tracked unknown with empirical evidence."""
        item = self.items.get(unknown_id)
        if not item:
            return None
        item.status = UnknownStatus.RESOLVED
        item.resolution = resolution
        if evidence_id and evidence_id not in item.evidence_links:
            item.evidence_links.append(evidence_id)
        item.updated_at = time.time()
        return item

    def list_unknowns(self, status: Optional[UnknownStatus] = None) -> List[UnknownItem]:
        """List tracked unknowns filtered by status."""
        if status:
            return [it for it in self.items.values() if it.status == status]
        return list(self.items.values())

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.to_dict() for k, v in self.items.items()}


@dataclass
class EvidenceRecord:
    """Canonical Evidence Record per REA specification."""

    evidence_id: str
    target_path: str
    target_sha256: str
    operation: str
    normalized_result: Dict[str, Any]
    raw_result: Optional[Dict[str, Any]] = None
    facet_availability: Dict[str, FacetAvailability] = field(default_factory=dict)
    provenance: ProvenanceMarker = field(default_factory=ProvenanceMarker)
    limitations: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        target_path: str | Path,
        operation: str,
        normalized_result: Dict[str, Any],
        raw_result: Optional[Dict[str, Any]] = None,
        facet_availability: Optional[Dict[str, FacetAvailability]] = None,
        limitations: Optional[List[str]] = None,
    ) -> EvidenceRecord:
        """Create and content-address an immutable Evidence Record."""
        path_str = str(Path(target_path).resolve())
        target_bytes = Path(target_path).read_bytes() if Path(target_path).is_file() else path_str.encode("utf-8")
        target_sha = hashlib.sha256(target_bytes).hexdigest()

        # Compute content-addressed evidence_id
        identity_payload = {
            "target_sha256": target_sha,
            "operation": operation,
            "normalized_result": normalized_result,
        }
        evidence_id = "ev_" + hashlib.sha256(
            json.dumps(identity_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]

        return cls(
            evidence_id=evidence_id,
            target_path=path_str,
            target_sha256=target_sha,
            operation=operation,
            normalized_result=normalized_result,
            raw_result=raw_result,
            facet_availability=facet_availability or {},
            provenance=ProvenanceMarker(untrusted_content=True, source="analysis_target"),
            limitations=limitations or [],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "target_path": self.target_path,
            "target_sha256": self.target_sha256,
            "operation": self.operation,
            "normalized_result": self.normalized_result,
            "raw_result": self.raw_result,
            "facet_availability": {k: v.to_dict() for k, v in self.facet_availability.items()},
            "provenance": self.provenance.to_dict(),
            "limitations": self.limitations,
            "created_at": self.created_at,
        }
