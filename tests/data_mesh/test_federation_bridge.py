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

    def test_each_domain_has_a_query_interface(self):
        # Every federated domain is routable for unified queries (dormant query layer wired).
        fed = register_data_products()
        for domain in fed.list_domains():
            assert fed.get_query(domain) is not None

    def test_query_factory_is_used(self):
        # DISCRIMINATING: an impl ignoring query_factory would attach a default query,
        # not the injected sentinel.
        from cohezion.datamesh.query import DatameshQuery

        seen = []

        def factory(domain):
            seen.append(domain)
            q = DatameshQuery()
            q._injected_for = domain  # tag so we can assert the SAME object was attached
            return q

        fed = register_data_products(query_factory=factory)
        domains = fed.list_domains()
        assert set(seen) == set(domains)  # factory called once per domain
        for domain in domains:
            assert getattr(fed.get_query(domain), "_injected_for", None) == domain
