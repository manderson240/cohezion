"""Analysis Session & Budget-Bounded Paged Projections.
======================================================
Reference: morluto/rea (Reverse Engineer Anything).

Provides:
1. Retained session storage for canonical Evidence records.
2. `inspect_analysis_view`: projects paged, budget-bounded views
   over large symbol tables, files, basic blocks, or disassembly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from cohezion.reverse_engineering.evidence import (
    EvidenceRecord,
    UnknownLedger,
)

logger = logging.getLogger(__name__)


@dataclass
class PagedViewResult:
    """Budget-bounded paged projection over a retained Evidence facet."""

    evidence_id: str
    facet: str
    offset: int
    limit: int
    total_items: int
    items: List[Any]
    next_offset: Optional[int]
    is_truncated: bool


class AnalysisSession:
    """Manages active reverse engineering session, retained evidence, and unknowns."""

    def __init__(self, session_id: str = "default_session") -> None:
        self.session_id = session_id
        self.records: Dict[str, EvidenceRecord] = {}
        self.unknown_ledger = UnknownLedger()

    def record_evidence(self, evidence: EvidenceRecord) -> str:
        """Store EvidenceRecord in the session bundle."""
        self.records[evidence.evidence_id] = evidence
        return evidence.evidence_id

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceRecord]:
        """Retrieve EvidenceRecord by content-addressed ID."""
        return self.records.get(evidence_id)

    def inspect_analysis_view(
        self,
        evidence_id: str,
        facet: str,
        offset: int = 0,
        limit: int = 64,
    ) -> PagedViewResult:
        """Project a budget-bounded, paged view over an Evidence facet."""
        record = self.records.get(evidence_id)
        if not record:
            raise KeyError(f"Evidence ID '{evidence_id}' not found in active session bundle.")

        norm = record.normalized_result
        target_list = norm.get(facet, [])

        if not isinstance(target_list, list):
            # If facet is a string or dictionary, wrap it or return single slice
            if isinstance(target_list, str):
                text_slice = target_list[offset : offset + limit]
                tot = len(target_list)
                next_off = offset + limit if (offset + limit) < tot else None
                return PagedViewResult(
                    evidence_id=evidence_id,
                    facet=facet,
                    offset=offset,
                    limit=limit,
                    total_items=tot,
                    items=[text_slice],
                    next_offset=next_off,
                    is_truncated=next_off is not None,
                )
            target_list = [target_list] if target_list else []

        total_items = len(target_list)
        sliced_items = target_list[offset : offset + limit]
        next_offset = offset + limit if (offset + limit) < total_items else None

        return PagedViewResult(
            evidence_id=evidence_id,
            facet=facet,
            offset=offset,
            limit=limit,
            total_items=total_items,
            items=sliced_items,
            next_offset=next_offset,
            is_truncated=next_offset is not None,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "evidence_count": len(self.records),
            "evidence_ids": list(self.records.keys()),
            "unknowns": self.unknown_ledger.to_dict(),
        }
