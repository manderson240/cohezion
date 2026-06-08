"""KG bridge: canonical DataProducts as a knowledge graph (KnowledgeGraphLayer consumer)."""

from __future__ import annotations

from cohezion.data_mesh.data_product import DataProduct, DataQualityTier, get_cohezion_data_products
from cohezion.data_mesh.knowledge_graph_bridge import build_product_graph


class TestKnowledgeGraphBridge:
    def test_node_per_product(self):
        kg = build_product_graph()
        assert len(kg.nodes) == len(get_cohezion_data_products())

    def test_same_tier_linked_not_cross_tier(self):
        # DISCRIMINATING: 2 GOLD + 1 SILVER -> exactly 1 edge (the GOLD pair).
        # A connect-all impl gives 3; a same-domain impl gives 0 (distinct domains).
        prods = {
            "a": DataProduct(
                product_id="a",
                name="A",
                description="",
                owner_domain="x",
                quality_tier=DataQualityTier.GOLD,
            ),
            "b": DataProduct(
                product_id="b",
                name="B",
                description="",
                owner_domain="y",
                quality_tier=DataQualityTier.GOLD,
            ),
            "c": DataProduct(
                product_id="c",
                name="C",
                description="",
                owner_domain="z",
                quality_tier=DataQualityTier.SILVER,
            ),
        }
        kg = build_product_graph(prods)
        assert len(kg.nodes) == 3
        assert len(kg.edges) == 1
