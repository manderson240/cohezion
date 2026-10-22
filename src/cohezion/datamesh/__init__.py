"""Deprecated alias for :mod:`cohezion.data_mesh` (coherence tranche 4, 2026-10-22).

The ``datamesh`` package duplicated the canonical ``data_mesh`` package under a second
spelling. Its six unique modules (schema, query, ingestion, federation,
bidirectional_linkage, knowledge_graph_layer) now live in ``cohezion.data_mesh``; its
``kanban_bridge`` was a stale prefix copy of ``cohezion.data_mesh.kanban_bridge``.

This shim keeps every public name importable from the old path for one release and warns
on import. Scheduled for removal in 1.29.0 — import from ``cohezion.data_mesh`` instead.
"""

from __future__ import annotations

import warnings

from cohezion.data_mesh.bidirectional_linkage import BidirectionalLink as BidirectionalLink
from cohezion.data_mesh.bidirectional_linkage import (
    BidirectionalLinkageManager as BidirectionalLinkageManager,
)
from cohezion.data_mesh.bidirectional_linkage import LinkDirection as LinkDirection
from cohezion.data_mesh.bidirectional_linkage import LinkStatus as LinkStatus
from cohezion.data_mesh.federation import FederationLayer as FederationLayer
from cohezion.data_mesh.ingestion import DatameshIngestion as DatameshIngestion
from cohezion.data_mesh.knowledge_graph_layer import KnowledgeEdge as KnowledgeEdge
from cohezion.data_mesh.knowledge_graph_layer import KnowledgeGraphLayer as KnowledgeGraphLayer
from cohezion.data_mesh.knowledge_graph_layer import KnowledgeNode as KnowledgeNode
from cohezion.data_mesh.knowledge_graph_layer import RelationType as KGRelationType
from cohezion.data_mesh.query import DatameshQuery as DatameshQuery
from cohezion.data_mesh.query import DatameshResult as DatameshResult
from cohezion.data_mesh.schema import DataLineage as DataLineage
from cohezion.data_mesh.schema import RecordType as RecordType
from cohezion.data_mesh.schema import RelationType as RelationType
from cohezion.data_mesh.schema import UnifiedRecord as UnifiedRecord


warnings.warn(
    "cohezion.datamesh is deprecated and will be removed in 1.29.0; "
    "import from cohezion.data_mesh instead",
    DeprecationWarning,
    stacklevel=2,
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
