"""Cohezion Datamesh - Unified data layer for graph, embeddings, and events.

Charter: Idempotent operations, 0.5 coherence via CQRS, full lineage tracking.
"""

from __future__ import annotations

from cohezion.datamesh.schema import (
    UnifiedRecord,
    RecordType,
    RelationType,
    DataLineage,
)
from cohezion.datamesh.query import DatameshQuery, DatameshResult
from cohezion.datamesh.ingestion import DatameshIngestion
from cohezion.datamesh.federation import FederationLayer

__all__ = [
    "UnifiedRecord",
    "RecordType",
    "RelationType",
    "DataLineage",
    "DatameshQuery",
    "DatameshResult",
    "DatameshIngestion",
    "FederationLayer",
]
