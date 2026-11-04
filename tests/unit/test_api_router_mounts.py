"""Every API route module must be reachable from the app (2026-11-04).

The 2026-07-30 refactor (8f712a8b, #267) moved inline routes into submodules and dropped
their include_router calls. 130 endpoints returned 404 for three months; the tests that
would have said so sat in a CI step that a collection error kept from running. This file is the
consumption check, kept in tests/unit so it runs in the gating step: a router that exists
but is not mounted fails here.
"""

from __future__ import annotations

import importlib
import inspect
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

import cohezion.api as api
from cohezion.security.rate_limiter import RateLimitResult


API_DIR = Path(api.__file__).parent

# Routers deliberately not mounted on the main app, with the reason.
NOT_MOUNTED: dict[str, str] = {
    # routes/main.py re-declares these paths and is mounted first; mounting the module routers
    # too would only add unreachable duplicates.
    "cohezion.api.routes.agentjet.agentjet_router": "paths served by routes/main.py",
    "cohezion.api.routes.mcp.mcp_router": "paths served by routes/main.py",
    "cohezion.api.routes.notebooks.notebooks_router": "paths served by routes/main.py",
    # Older copy of flume_inline (same six paths); flume_inline keeps the cohezion.api._get_vae
    # patch points the tests rely on.
    "cohezion.api.routes.flume.flume_router": "superseded by routes/flume_inline.py",
    # Never mounted in any revision, so never part of the public API. Left dormant on purpose
    # until someone decides to expose them; forge's /benchmark runs kernels on the host.
    "cohezion.api.routes.fleet.router": "never mounted; dormant pending a decision",
    "cohezion.api.services.forge.forge_router": "never mounted; dormant pending a decision",
    # Mounted at /api/brand on one branch (e5bef2f1e) and dropped on another (30d523d55);
    # nothing in src/web calls /api/brand.
    "cohezion.api.services.brand.brand_router": "dropped in 30d523d55; no caller",
}


def _paths(router: APIRouter, prefix: str = "") -> set[str]:
    return {prefix + r.path for r in router.routes if hasattr(r, "path")}


def _module_routers() -> list[tuple[str, APIRouter]]:
    found = []
    for path in sorted([*API_DIR.glob("routes/*.py"), *API_DIR.glob("services/*.py")]):
        if path.name == "__init__.py":
            continue
        mod_name = "cohezion.api." + ".".join(path.relative_to(API_DIR).with_suffix("").parts)
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue  # optional dependency missing; _mount_domain_routers logs this case
        for attr, value in inspect.getmembers(mod, lambda v: isinstance(v, APIRouter)):
            if value.routes:
                found.append((f"{mod_name}.{attr}", value))
    return found


def test_no_domain_router_failed_to_mount():
    assert api.UNMOUNTED_ROUTERS == []


@pytest.mark.parametrize(
    ("dotted", "path"),
    [
        ("cohezion.api.services.physics_extended.physics_ext_router", "/api/physics/bioelectric"),
        ("cohezion.api.routes.metrics.metrics_router", "/metrics/system"),
        ("cohezion.api.routes.compound.compound_router", "/compound/health"),
        ("cohezion.api.routes.skills.skills_router", "/skills/list"),
    ],
)
def test_restored_endpoints_do_not_404(dotted, path):
    """Discriminating: each of these returned 404 before the mounts were restored."""
    resp = TestClient(api.app).get(path)
    assert resp.status_code != 404, f"{path} ({dotted}) is not mounted"


# Prefixes the app mounts routers under (see _DOMAIN_ROUTERS and the explicit mounts).
_PREFIXES = (
    "",
    "/api",
    "/api/universe",
    "/api/journeys",
    "/api/anima",
    "/api/architecture",
    "/api/agui",
)


def _probe_path(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "x", path)


def test_every_route_module_router_is_mounted_or_explained(monkeypatch):
    """A mounted path answers TRACE with 405 (wrong method); an unmounted one with 404."""
    allow = RateLimitResult(allowed=True, remaining=1, reset_after=0.0, limit=1)
    monkeypatch.setattr(api, "get_rate_limiter", lambda: SimpleNamespace(check=lambda *_: allow))
    client = TestClient(api.app, raise_server_exceptions=False)
    missing = []
    for dotted, router in _module_routers():
        if dotted in NOT_MOUNTED:
            continue
        sample = sorted(_paths(router))[0]
        if all(
            client.request("TRACE", prefix + _probe_path(sample)).status_code == 404
            for prefix in _PREFIXES
        ):
            missing.append(f"{dotted} ({sample})")
    assert not missing, (
        "routers defined but never mounted on cohezion.api.app (mount them in "
        "_DOMAIN_ROUTERS or list them in NOT_MOUNTED with a reason): " + ", ".join(missing)
    )
