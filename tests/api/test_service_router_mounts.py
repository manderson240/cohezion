"""Every route of every router in cohezion.api.SERVICE_ROUTERS is SERVED, by its own handler.

#267 deleted the inline endpoints and router mounts from api/__init__.py: 130 of 169 routes
returned 404 on main while every router module still existed and its own unit tests (which build
standalone apps) passed. Existence of a router proves nothing; these tests dispatch real ASGI
requests through the assembled app and record which endpoint the router chose, without running
it (APIRoute.handle is replaced by a recorder), so a shadowed or unmounted route fails.
"""

from __future__ import annotations

import importlib
import re
import warnings
from pathlib import Path

import httpx
import pytest
from fastapi.routing import APIRoute
from starlette.responses import Response

from cohezion.api import SERVICE_ROUTERS, app
from cohezion.api.routes import main as routes_main


_BEFORE_267 = Path(__file__).parent / "routes_before_pr267.txt"

# main_router already served these (method, path) when the routers were re-mounted; the copies in
# routes/knowledge.py and routes/swarm.py are skipped, so main_router must be the one answering.
SERVED_BY_MAIN = {
    ("POST", "/knowledge/search"),
    ("GET", "/knowledge/skills"),
    ("GET", "/knowledge/skills/{skill_name}"),
    ("POST", "/swarm/debate"),
    ("GET", "/swarm/perspectives"),
    ("GET", "/swarm/metrics"),
}


def _concrete(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "zz9", path)


@pytest.fixture
def dispatched(monkeypatch: pytest.MonkeyPatch):
    """Return a function mapping (method, path) to the endpoint the app dispatches it to."""
    seen: list = []

    async def record(self: APIRoute, scope, receive, send) -> None:
        seen.append(self.endpoint)
        await Response(status_code=204)(scope, receive, send)

    monkeypatch.setattr(APIRoute, "handle", record)

    async def resolve(method: str, path: str):
        seen.clear()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await client.request(method, _concrete(path))
        return seen[0] if seen else None

    return resolve


def _router_routes() -> list[tuple[str, str, str, object]]:
    out = []
    for module, attr, prefix in SERVICE_ROUTERS:
        router = getattr(importlib.import_module(module), attr)
        for route in router.routes:
            assert isinstance(route, APIRoute), f"{module}: nested/non-HTTP route bypasses dedupe"
            for method in sorted(route.methods or ()):
                if method != "HEAD":
                    out.append((module, method, prefix + route.path, route.endpoint))
    return out


ROUTER_ROUTES = _router_routes()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("module", "method", "path", "endpoint"),
    ROUTER_ROUTES,
    ids=[f"{m} {p}" for _, m, p, _ in ROUTER_ROUTES],
)
async def test_route_is_answered_by_its_own_handler(dispatched, module, method, path, endpoint):
    got = await dispatched(method, path)
    assert got is not None, f"{method} {path} ({module}) is not served"
    if (method, path) in SERVED_BY_MAIN:
        assert got.__module__ == routes_main.__name__, f"{method} {path} should stay on main_router"
    else:
        assert got is endpoint, f"{method} {path} answered by {got.__module__}.{got.__qualname__}"


def _served() -> tuple[set[tuple[str, str]], list[str]]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        app.openapi_schema = None
        paths = app.openapi()["paths"]
    served = {(m.upper(), p) for p, ops in paths.items() for m in ops}
    return served, [str(w.message) for w in caught]


def test_every_route_served_before_267_is_still_served() -> None:
    lines = [ln for ln in _BEFORE_267.read_text().splitlines() if ln and not ln.startswith("#")]
    before = {tuple(ln.split(" ", 1)) for ln in lines}
    assert len(before) == 169
    assert not before - _served()[0]


def test_no_route_is_registered_twice() -> None:
    # The paths dict merges a duplicated route into one key, so count FastAPI's own warning:
    # physics_extended.py once registered seven endpoints three times each.
    dups = [m for m in _served()[1] if "Duplicate Operation ID" in m]
    assert not dups, dups[:3]


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/flume/train", "/flume/encode", "/flume/latent-space"])
async def test_flume_is_served_by_the_copy_of_the_live_handlers(dispatched, path) -> None:
    # routes/flume.py and routes/flume_inline.py define the same paths; flume_inline's bodies
    # match the pre-#267 live handlers (0.94-1.00 similarity, flume.py 0.74-0.99). Pin it so a
    # swap to the stale copy cannot pass by also changing SERVICE_ROUTERS.
    got = await dispatched("POST", path)
    assert got is not None and got.__module__ == "cohezion.api.routes.flume_inline"
