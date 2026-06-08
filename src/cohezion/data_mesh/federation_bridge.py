"""Federation bridge — register canonical DataProducts as federated domains.

Leverages the (previously dormant) datamesh ``FederationLayer`` by giving it its
first real consumer: the canonical :func:`get_cohezion_data_products`. Each distinct
``owner_domain`` becomes a ``DomainEndpoint`` whose federation PRIORITY is driven by
that domain's best data-product quality tier (GOLD routes ahead of SILVER ahead of
BRONZE) — so the federation's failover/routing honors real product quality instead of
a flat default.

Additive + non-destructive: this lives in the *canonical* ``data_mesh/`` and imports
the *orphan* ``datamesh.federation`` — the integrate-first step of the documented
``datamesh -> data_mesh`` consolidation (Wire-at-Creation; non-destructive-wiring
policy). Nothing is deleted; the dormant federation gains a consumer.

Owner agent: ``surreal-dba`` (its card's ``canonical_modules`` include
``cohezion.datamesh.schema``).
"""

from __future__ import annotations

from collections.abc import Callable

from cohezion.data_mesh.data_product import (
    DataProduct,
    DataQualityTier,
    get_cohezion_data_products,
)
from cohezion.datamesh.federation import DomainEndpoint, FederationLayer
from cohezion.datamesh.query import DatameshQuery


# Lower number = higher federation priority (matches FederationLayer semantics).
_TIER_PRIORITY: dict[DataQualityTier, int] = {
    DataQualityTier.GOLD: 1,
    DataQualityTier.SILVER: 2,
    DataQualityTier.BRONZE: 3,
}


def _domain_priority(products: list[DataProduct]) -> int:
    """Best (lowest) priority across a domain's products — GOLD wins."""
    return min(_TIER_PRIORITY.get(p.quality_tier, 3) for p in products)


def register_data_products(
    federation: FederationLayer | None = None,
    products: dict[str, DataProduct] | None = None,
    *,
    query_factory: Callable[[str], DatameshQuery] | None = None,
) -> FederationLayer:
    """Register each DataProduct ``owner_domain`` as a federated ``DomainEndpoint``.

    Priority is derived from the domain's best quality tier, so the federation's
    failover/routing honors data-product quality. Each domain is also given a
    ``DatameshQuery`` interface so the federation can route unified queries to it
    (``federation.get_query(domain)``) — wiring the dormant query layer to the
    canonical products. The default query is backendless ($0, returns empty until
    backends are injected); pass ``query_factory`` to supply backend-wired queries.

    Parameters
    ----------
    federation:
        Target layer (a fresh :class:`FederationLayer` if omitted).
    products:
        Products to federate (the live :func:`get_cohezion_data_products` if omitted).
    query_factory:
        Optional ``domain -> DatameshQuery`` builder for backend-wired queries.

    Returns
    -------
    FederationLayer
        The populated layer, for chaining.
    """
    federation = federation or FederationLayer()
    products = products if products is not None else get_cohezion_data_products()

    by_domain: dict[str, list[DataProduct]] = {}
    for product in products.values():
        by_domain.setdefault(product.owner_domain, []).append(product)

    for domain, prods in sorted(by_domain.items()):
        query = query_factory(domain) if query_factory else DatameshQuery()
        federation.register_domain(
            DomainEndpoint(name=domain, priority=_domain_priority(prods), query=query)
        )
    return federation
