"""Cohezion Datamesh - Unified data layer for graph, embeddings, and events.

Charter: Idempotent operations, 0.5 coherence via CQRS, full lineage tracking.
"""

from __future__ import annotations

import contextlib

with contextlib.suppress(Exception):
    from cohezion.datamesh.bidirectional_linkage import BidirectionalLink as BidirectionalLink
    from cohezion.datamesh.bidirectional_linkage import (
        BidirectionalLinkageManager as BidirectionalLinkageManager,
    )
    from cohezion.datamesh.bidirectional_linkage import LinkDirection as LinkDirection
    from cohezion.datamesh.bidirectional_linkage import LinkStatus as LinkStatus

with contextlib.suppress(Exception):
    from cohezion.datamesh.federation import FederationLayer as FederationLayer

with contextlib.suppress(Exception):
    from cohezion.datamesh.ingestion import DatameshIngestion as DatameshIngestion

with contextlib.suppress(Exception):
    from cohezion.datamesh.knowledge_graph_layer import KnowledgeEdge as KnowledgeEdge
    from cohezion.datamesh.knowledge_graph_layer import KnowledgeGraphLayer as KnowledgeGraphLayer
    from cohezion.datamesh.knowledge_graph_layer import KnowledgeNode as KnowledgeNode
    from cohezion.datamesh.knowledge_graph_layer import RelationType as KGRelationType

with contextlib.suppress(Exception):
    from cohezion.datamesh.query import DatameshQuery as DatameshQuery
    from cohezion.datamesh.query import DatameshResult as DatameshResult

with contextlib.suppress(Exception):
    from cohezion.datamesh.schema import DataLineage as DataLineage
    from cohezion.datamesh.schema import RecordType as RecordType
    from cohezion.datamesh.schema import RelationType as RelationType
    from cohezion.datamesh.schema import UnifiedRecord as UnifiedRecord


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
