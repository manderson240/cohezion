"""Federation bridge — register canonical DataProducts as federated domains."""

from __future__ import annotations

from cohezion.data_mesh.data_product import DataProduct, DataQualityTier
from cohezion.data_mesh.federation_bridge import (
    federation_routing_order,
    register_data_products,
)


def _prod(pid: str, domain: str, tier: DataQualityTier) -> DataProduct:
    return DataProduct(
        product_id=pid, name=pid, description="", owner_domain=domain, quality_tier=tier
    )


# alpha mixes BRONZE+GOLD (BRONZE inserted FIRST) -> best-tier-wins priority 1;
# mid is SILVER (2); zdomain is GOLD (1). Insertion order is z, a, a, m.
_MIXED = {
    "z1": _prod("z1", "zdomain", DataQualityTier.GOLD),
    "a1": _prod("a1", "alpha", DataQualityTier.BRONZE),
    "a2": _prod("a2", "alpha", DataQualityTier.GOLD),
    "m1": _prod("m1", "mid", DataQualityTier.SILVER),
}


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


class TestFederationRoutingOrder:
    """Report-only failover/routing order over the federation (item: dormant-module consumer)."""

    def test_best_tier_wins_and_priority_sorted(self):
        # DISCRIMINATING (kills four wrong impls at once):
        #  - worst-tier (max): alpha -> 3, would rank LAST (not first)
        #  - first-product tier: alpha's first product is BRONZE -> 3, would rank last
        #  - no sort / insertion order: register sorts domains [alpha, mid, zdomain],
        #    so unsorted read-back puts mid (2) BEFORE zdomain (1)
        #  - descending sort: order reversed
        order = federation_routing_order(products=_MIXED)
        assert order == [("alpha", 1), ("zdomain", 1), ("mid", 2)]

    def test_domain_priority_is_best_not_worst_tier(self):
        # Pinpoint the best-tier-wins semantic: alpha (BRONZE+GOLD) must route at GOLD (1).
        order = dict(federation_routing_order(products=_MIXED))
        assert order["alpha"] == 1

    def test_default_products_sorted_nonempty(self):
        # Live composition over the real canonical products: non-empty and priority-sorted.
        order = federation_routing_order()
        assert order
        assert order == sorted(order, key=lambda row: (row[1], row[0]))
        assert all(isinstance(d, str) and isinstance(p, int) for d, p in order)
