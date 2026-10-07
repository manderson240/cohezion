"""Every router in cohezion.api.SERVICE_ROUTERS must be SERVED by the assembled app.

#267 deleted the inline endpoints and router mounts from api/__init__.py: 130 of 169 routes
returned 404 on main while every router module still existed and its own unit tests (which build
standalone apps) passed. Existence of a router proves nothing; this asserts the app serves it.
"""

from __future__ import annotations

import warnings

import pytest

from cohezion.api import SERVICE_ROUTERS, app


# One representative (method, path) per SERVICE_ROUTERS entry, as served by the app.
REPRESENTATIVE = {
    "cohezion.api.routes.compound": ("POST", "/compound/execute"),
    "cohezion.api.routes.flume_inline": ("POST", "/flume/latent-space"),
    "cohezion.api.routes.journeys_legacy": ("GET", "/journeys"),
    "cohezion.api.routes.knowledge": ("POST", "/knowledge/query"),
    "cohezion.api.routes.metrics": ("GET", "/metrics/system"),
    "cohezion.api.routes.rl": ("POST", "/rl/step"),
    "cohezion.api.routes.skills": ("GET", "/skills/list"),
    "cohezion.api.routes.swarm": ("POST", "/swarm/execute"),
    "cohezion.api.routes.templates": ("POST", "/templates/parse"),
    "cohezion.api.research_endpoints": ("GET", "/research/status/{session_id}"),
    "cohezion.api.services.universe": ("GET", "/api/universe/state"),
    "cohezion.api.routes.journey_nexus": ("GET", "/api/journey-nexus/frame"),
    "cohezion.api.services.genesis": ("GET", "/api/genesis/spinor/sweep"),
    "cohezion.api.services.world_model": ("GET", "/api/world-model/status"),
    "cohezion.api.services.physics_extended": ("GET", "/api/physics/bioelectric"),
    "cohezion.api.services.worldviews": ("GET", "/api/worldviews/traditions"),
    "cohezion.api.journeys": ("POST", "/api/journeys/journeys/analyze"),
    "cohezion.api.services.ouroboros_api": ("GET", "/api/ouroboros/health"),
    "cohezion.api.services.mycelium_api": ("GET", "/api/mycelium/network"),
    "cohezion.api.services.modules_api": ("GET", "/api/modules/hiho-bridge"),
}


def _openapi() -> tuple[dict, list[str]]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        app.openapi_schema = None
        paths = app.openapi()["paths"]
    return paths, [str(w.message) for w in caught]


def _served() -> list[tuple[str, str]]:
    return [(m.upper(), p) for p, ops in _openapi()[0].items() for m in ops]


def test_every_entry_has_a_representative() -> None:
    assert {m for m, _, _ in SERVICE_ROUTERS} == set(REPRESENTATIVE)


@pytest.mark.parametrize("module", sorted(REPRESENTATIVE))
def test_router_is_served_by_the_app(module: str) -> None:
    assert REPRESENTATIVE[module] in set(_served()), f"{module} is not mounted"


def test_no_route_is_registered_twice() -> None:
    # The paths dict merges a duplicated route into one key, so count FastAPI's own warning:
    # physics_extended.py once registered seven endpoints three times each.
    dups = [m for m in _openapi()[1] if "Duplicate Operation ID" in m]
    assert not dups, dups[:3]


def test_route_table_did_not_shrink_below_the_pre_267_count() -> None:
    # 169 routes before #267 plus 11 added since, measured 2026-10-06 by diffing the OpenAPI
    # route tables of 8f712a8bd^ and this revision (0 of the 169 missing).
    assert len(set(_served())) >= 180
