"""Every router the API ships must be MOUNTED on ``cohezion.api.app`` (or explicitly excused).

Regression guard: the #267 refactor (8f712a8bd, "extract route handlers from __init__.py")
dropped 11 ``app.include_router`` calls AND deleted 33 inline routes whose extracted
replacements in ``api/routes/`` were only re-exported (``routes/__init__.py``), never mounted.
Every module still imported cleanly, so nothing errored: each request just returned 404, and
~190 API/physics tests failed on main. A re-export is a DECLARATION; only a reachable route on
the assembled app is CONSUMPTION, so that is what these tests check.
"""

from __future__ import annotations

import importlib
import pkgutil

import pytest
from fastapi import APIRouter
from fastapi.routing import APIRoute

import cohezion.api.routes as api_routes
import cohezion.api.services as api_services
from cohezion.api import app


# (module, router attribute, include prefix): what the app served before 8f712a8bd.
EXPECTED_MOUNTS = [
    # service routers (were app.include_router calls)
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
    # extracted replacements for the deleted inline routes
    ("cohezion.api.routes.flume_inline", "flume_inline_router", ""),
    ("cohezion.api.routes.templates", "templates_router", ""),
    ("cohezion.api.routes.rl", "rl_router", ""),
    ("cohezion.api.routes.journeys_legacy", "journeys_legacy_router", ""),
    ("cohezion.api.routes.skills", "skills_router", ""),
    ("cohezion.api.routes.metrics", "metrics_router", ""),
    ("cohezion.api.routes.knowledge", "knowledge_router", ""),
    ("cohezion.api.routes.swarm", "swarm_router", ""),
    ("cohezion.api.routes.compound", "compound_router", ""),
]

# Routers deliberately NOT mounted. Each needs a reason; mounting one is a behaviour change
# (new public surface), not a restoration, so it is a maintainer decision.
UNMOUNTED = {
    "cohezion.api.routes.flume.flume_router": "rival of flume_inline with a private _get_vae copy",
    "cohezion.api.routes.fleet.router": "never mounted (pre-#267 either); exposes fleet control",
    "cohezion.api.services.brand.brand_router": "never mounted (pre-#267 either)",
    "cohezion.api.services.forge.forge_router": "never mounted (pre-#267 either)",
}


def _schema_ops(router: APIRouter, prefix: str = "") -> set[tuple[str, str]]:
    return {
        (method.lower(), prefix + r.path)
        for r in router.routes
        if isinstance(r, APIRoute) and r.include_in_schema
        for method in r.methods
    }


@pytest.fixture(scope="module")
def served_ops() -> set[tuple[str, str]]:
    return {(m, p) for p, ops in app.openapi()["paths"].items() for m in ops}


@pytest.mark.parametrize(
    ("module", "attr", "prefix"), EXPECTED_MOUNTS, ids=[f"{m[0]}.{m[1]}" for m in EXPECTED_MOUNTS]
)
def test_router_is_mounted(
    module: str, attr: str, prefix: str, served_ops: set[tuple[str, str]]
) -> None:
    router = getattr(importlib.import_module(module), attr)
    expected = _schema_ops(router, prefix)
    assert expected, f"{module}.{attr} defines no schema routes; test premise broken"
    missing = sorted(expected - served_ops)
    assert not missing, f"{module}.{attr} not mounted; unreachable: {missing[:5]}"


def _all_package_routers() -> list[tuple[str, APIRouter]]:
    found = []
    for pkg in (api_routes, api_services):
        for info in pkgutil.iter_modules(pkg.__path__):
            mod = importlib.import_module(f"{pkg.__name__}.{info.name}")
            for name, value in vars(mod).items():
                if isinstance(value, APIRouter) and _schema_ops(value):
                    found.append((f"{mod.__name__}.{name}", value))
    return found


def test_every_package_router_is_mounted_or_excused(served_ops: set[tuple[str, str]]) -> None:
    """Class-wide: a NEW router added under api/routes or api/services must be mounted."""
    served_paths = {p for _, p in served_ops}
    dormant = []
    for qualname, router in _all_package_routers():
        if qualname in UNMOUNTED:
            continue
        # Mounted under SOME prefix: every route's (method, path-suffix) is served.
        ops = _schema_ops(router)
        if not all(any(m == sm and sp.endswith(p) for sm, sp in served_ops) for m, p in ops):
            dormant.append(qualname)
    assert served_paths, "app serves nothing; test premise broken"
    assert not dormant, f"routers defined but not mounted (mount or add to UNMOUNTED): {dormant}"


def test_unmounted_allowlist_is_not_stale() -> None:
    names = {q for q, _ in _all_package_routers()}
    stale = sorted(set(UNMOUNTED) - names)
    assert not stale, f"UNMOUNTED names routers that no longer exist: {stale}"
