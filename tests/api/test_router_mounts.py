"""Every service router the API ships must be MOUNTED on ``cohezion.api.app``.

Regression guard: the #267 refactor (8f712a8bd, "extract route handlers from __init__.py")
dropped 11 ``app.include_router`` calls. All 11 routers still imported cleanly and defined
110 routes, so nothing errored; every request to them just returned 404. That left ~150 API
tests failing on main. A router that is defined but not mounted is dormant, and only a
consumption check (is the route reachable on the assembled app?) can see it.
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.routing import APIRoute

from cohezion.api import app


# (module, router attribute, include prefix) -- as mounted before 8f712a8bd.
EXPECTED_MOUNTS = [
    ("cohezion.api.research_endpoints", "router", ""),
    ("cohezion.api.services.universe", "universe_router", "/api/universe"),
    ("cohezion.api.routes.journey_nexus", "router", "/api"),
    ("cohezion.api.services.genesis", "genesis_router", "/api"),
    ("cohezion.api.services.world_model", "world_model_router", "/api"),
    ("cohezion.api.services.physics_extended", "physics_ext_router", "/api"),
    ("cohezion.api.services.worldviews", "worldviews_router", "/api"),
    ("cohezion.api.journeys", "router", "/api/journeys"),
    ("cohezion.api.services.ouroboros_api", "ouroboros_router", "/api"),
    ("cohezion.api.services.mycelium_api", "mycelium_router", "/api"),
    ("cohezion.api.services.modules_api", "modules_router", "/api"),
]


@pytest.fixture(scope="module")
def mounted_paths() -> set[str]:
    return set(app.openapi()["paths"])


@pytest.mark.parametrize(
    ("module", "attr", "prefix"), EXPECTED_MOUNTS, ids=[m[0] for m in EXPECTED_MOUNTS]
)
def test_router_is_mounted(module: str, attr: str, prefix: str, mounted_paths: set[str]) -> None:
    router = getattr(importlib.import_module(module), attr)
    expected = {
        prefix + r.path for r in router.routes if isinstance(r, APIRoute) and r.include_in_schema
    }
    assert expected, f"{module}.{attr} defines no schema routes; test premise broken"
    missing = sorted(expected - mounted_paths)
    assert not missing, (
        f"{module}.{attr} not mounted on cohezion.api.app; unreachable: {missing[:5]}"
    )
