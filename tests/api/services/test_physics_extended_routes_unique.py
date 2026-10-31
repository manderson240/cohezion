"""physics_extended.py contained the Phase-18 block (7 response models + 7 routes) three times,
byte-identical, so every one of those paths was registered 3x (duplicate OpenAPI operations;
the 2nd and 3rd handlers are shadowed dead code).  Found 2026-10-31 via ruff F811."""

from __future__ import annotations

import collections

from cohezion.api.services.physics_extended import physics_ext_router


def test_no_route_is_registered_twice() -> None:
    seen = collections.Counter(
        (tuple(sorted(r.methods or ())), r.path) for r in physics_ext_router.routes
    )
    assert {k: n for k, n in seen.items() if n > 1} == {}


def test_phase18_routes_still_present() -> None:
    paths = {r.path for r in physics_ext_router.routes}
    for name in ("bec", "mercury", "colibre", "mhd", "bismuth", "toroidal", "tensor-metric"):
        assert f"/physics/{name}/status" in paths, name


def test_physics_extended_router_is_mounted_on_the_app() -> None:
    """The #267 squash (8f712a8bd) removed the include_router call, so the whole router was
    unreachable and its 22 endpoint tests all returned 404 on main."""
    from cohezion.api import app

    paths = app.openapi()["paths"]
    assert "/api/physics/bec/status" in paths
    assert "/api/physics/bioelectric" in paths
