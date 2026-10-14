"""Cohezion Reverse Engineering & Artifact Inspection Module (REA).
================================================================
Reference: morluto/rea (Reverse Engineer Anything).
"""

from __future__ import annotations

from cohezion.reverse_engineering.artifact_inspector import ArtifactInspector
from cohezion.reverse_engineering.evidence import (
    EvidenceRecord,
    FacetAvailability,
    ProvenanceMarker,
    UnknownItem,
    UnknownLedger,
    UnknownStatus,
)
from cohezion.reverse_engineering.session import (
    AnalysisSession,
    PagedViewResult,
)

__all__ = [
    "AnalysisSession",
    "ArtifactInspector",
    "EvidenceRecord",
    "FacetAvailability",
    "PagedViewResult",
    "ProvenanceMarker",
    "UnknownItem",
    "UnknownLedger",
    "UnknownStatus",
]
