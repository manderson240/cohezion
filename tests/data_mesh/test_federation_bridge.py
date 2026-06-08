"""Federation bridge — register canonical DataProducts as federated domains."""

from __future__ import annotations

from cohezion.data_mesh.data_product import DataProduct, DataQualityTier
from cohezion.data_mesh.federation_bridge import register_data_products


class TestFederationBridge:
    def test_registers_all_product_domains(self):
        fed = register_data_products()
        assert set(fed.list_domains()) == {
            "bmad",
            "skills",
            "journey",
            "memory",
            "api",
            "physics",
        }

    def test_priority_driven_by_quality_tier(self):
        # DISCRIMINATING: a GOLD domain must outrank (lower number) a SILVER domain.
        # A constant-priority impl gives them equal priority → fails.
        fed = register_data_products()
        assert fed.endpoint("skills").priority < fed.endpoint("bmad").priority  # GOLD < SILVER

    def test_injected_products_only(self):
        prods = {
            "g": DataProduct(
                product_id="g",
                name="G",
                description="",
                owner_domain="alpha",
                quality_tier=DataQualityTier.GOLD,
            ),
            "b": DataProduct(
                product_id="b",
                name="B",
                description="",
                owner_domain="beta",
                quality_tier=DataQualityTier.BRONZE,
            ),
        }
        fed = register_data_products(products=prods)
        assert set(fed.list_domains()) == {"alpha", "beta"}
        assert fed.endpoint("alpha").priority == 1  # GOLD
        assert fed.endpoint("beta").priority == 3  # BRONZE
