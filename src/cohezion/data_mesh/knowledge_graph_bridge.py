"""Knowledge-graph bridge — canonical DataProducts as a KnowledgeGraphLayer.

Gives the dormant datamesh ``KnowledgeGraphLayer`` its first real consumer: each
DataProduct becomes a ``KnowledgeNode``, and products sharing a quality tier are linked by
a ``SEMANTIC_ASSOCIATION`` edge (an attribute-derived PEER relation — the evidence records
the shared tier; richer lineage edges, e.g. DERIVED_FROM/FLOWS_INTO, are future work once
real inter-product lineage exists). The graph is in-memory and $0 (no surreal/flume
backend), and makes ``calculate_centrality`` / ``query_subgraph`` /
``find_hiho_stable_neighbors`` available over the product catalog.

Additive + non-destructive: lives in canonical ``data_mesh/`` and consumes the orphan
``datamesh.knowledge_graph_layer`` — the integrate-first ``datamesh -> data_mesh`` step.
Owner agent: ``surreal-dba`` (graph + datamesh schema).
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from cohezion.data_mesh.data_product import DataProduct, get_cohezion_data_products
from cohezion.datamesh.knowledge_graph_layer import KnowledgeGraphLayer, RelationType


async def _build(products: dict[str, DataProduct]) -> KnowledgeGraphLayer:
    kg = KnowledgeGraphLayer(datamesh=None)  # in-memory, no backend ($0)
    node_id_of: dict[str, str] = {}
    by_tier: dict[Any, list[str]] = {}

    for pid, product in products.items():
        node = await kg.create_node(
            entity_id=uuid.uuid5(uuid.NAMESPACE_URL, product.product_id),
            label=product.name,
            entity_type="data_product",
            content=product.description or product.name,
        )
        node_id_of[pid] = node.node_id
        by_tier.setdefault(product.quality_tier, []).append(pid)

    for tier, pids in by_tier.items():
        for i in range(len(pids)):
            for j in range(i + 1, len(pids)):
                await kg.create_edge(
                    source_node_id=node_id_of[pids[i]],
                    target_node_id=node_id_of[pids[j]],
                    relation=RelationType.SEMANTIC_ASSOCIATION,
                    evidence=[f"shared quality_tier: {tier.name}"],
                )
    return kg


def build_product_graph(products: dict[str, DataProduct] | None = None) -> KnowledgeGraphLayer:
    """Build an in-memory knowledge graph of the canonical DataProducts ($0).

    Nodes = products; edges = shared-quality-tier peer associations. Returns the populated
    :class:`KnowledgeGraphLayer` for centrality/subgraph analysis over the catalog.
    """
    products = products if products is not None else get_cohezion_data_products()
    return asyncio.run(_build(products))
