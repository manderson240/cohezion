"""Cohezion Datamesh - Unified data layer for graph, embeddings, and events.

Charter: Idempotent operations, 0.5 coherence via CQRS, full lineage tracking.
"""

from __future__ import annotations

from cohezion.datamesh.bidirectional_linkage import (
    BidirectionalLink,
    BidirectionalLinkageManager,
    LinkDirection,
    LinkStatus,
)
from cohezion.datamesh.federation import FederationLayer
from cohezion.datamesh.ingestion import DatameshIngestion
from cohezion.datamesh.knowledge_graph_layer import (
    KnowledgeEdge,
    KnowledgeGraphLayer,
    KnowledgeNode,
)
from cohezion.datamesh.knowledge_graph_layer import (
    RelationType as KGRelationType,
)
from cohezion.datamesh.query import DatameshQuery, DatameshResult
from cohezion.datamesh.schema import (
    DataLineage,
    RecordType,
    RelationType,
    UnifiedRecord,
)


__all__ = [
    "BidirectionalLink",
    "BidirectionalLinkageManager",
    "DataLineage",
    "DatameshIngestion",
    "DatameshQuery",
    "DatameshResult",
    "FederationLayer",
    "KGRelationType",
    "KnowledgeEdge",
    "KnowledgeGraphLayer",
    "KnowledgeNode",
    "LinkDirection",
    "LinkStatus",
    "RecordType",
    "RelationType",
    "UnifiedRecord",
]
