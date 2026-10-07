"""
Cohezion API - FastAPI server exposing swarm and MCP tools.

Provides REST endpoints for Open-Notebook integration.

The route decorators live in submodules under ``cohezion.api.routes`` —
this module is the app factory + router-mount surface only.

Singletons (``_vae_trainer``, ``_rl_policy``) and the helper functions
``_get_vae``, ``_get_rl_policy``, ``_compute_coherence``, ``set_token_client``
remain attributes of this package because tests and conftest fixtures
reference them by full path (``patch("cohezion.api._get_vae", ...)`` etc.).
"""

import contextlib
import importlib
import logging
import math
import os
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles

from cohezion.api._helpers import (
    compute_coherence as _compute_coherence,
)
from cohezion.api._helpers import (
    get_rl_policy as _get_rl_policy,
)
from cohezion.api._helpers import (
    get_vae as _get_vae,
)
from cohezion.api.routes.eigent import router as eigent_router
from cohezion.api.routes.main import router as main_router
from cohezion.api.routes.metrics import set_token_client
from cohezion.api.telemetry import router as telemetry_router
from cohezion.security.rate_limiter import get_rate_limiter


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Singletons referenced by tests via ``cohezion.api._vae_trainer`` /
# ``cohezion.api._rl_policy``. The helpers in ``_helpers.py`` read/write these
# attributes on this module, which keeps conftest's reset hooks working.
_vae_trainer = None
_rl_policy = None


# Allowed CORS origins from environment, default to localhost only
_CORS_ORIGINS = os.environ.get(
    "COHEZION_CORS_ORIGINS", "http://localhost:3000,http://localhost:8080"
).split(",")

app = FastAPI(
    title="Cohezion API",
    description="AI Research Lab API - Swarm workflows and MCP tools",
    version="0.1.0",
    docs_url="/docs" if os.environ.get("COHEZION_ENV") != "production" else None,
    redoc_url="/redoc" if os.environ.get("COHEZION_ENV") != "production" else None,
)

# CORS — restricted to configured origins with explicit methods/headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-Agent-Token"],
)


# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    limiter = get_rate_limiter()
    client_ip = request.client.host if request.client else "unknown"
    result = limiter.check(client_ip, request.url.path)
    if not result.allowed:
        return JSONResponse(
            status_code=429,
            headers={
                "Retry-After": str(int(result.reset_after) + 1),
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": "0",
            },
            content={"detail": "Rate limit exceeded"},
        )
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(result.remaining)
    return response


def _json_safe(value):
    """Render non-finite floats as strings so a validation error can always be serialized."""
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


@app.exception_handler(RequestValidationError)
async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # FastAPI's default handler echoes the rejected input; a body carrying NaN/Infinity then
    # fails JSON encoding and the client gets a 500 instead of the 422. Same response shape.
    return JSONResponse(
        status_code=422, content={"detail": _json_safe(jsonable_encoder(exc.errors()))}
    )


# Static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")


# Root redirect to UI
@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


# Mount main router (contains health, mcp, knowledge, swarm, notebooks, simulations, agentjet, a2a)
app.include_router(main_router)

# Routers (module, router attribute, mount prefix) dropped by #267, which deleted the inline
# endpoints and mounts here: the first group are the extractions of those inline endpoints
# (routes/*.py, written in #89 but never mounted), the second the service routers whose mounts
# were removed. 130 of 169 routes served 404 until 2026-10-06. A failed import is LOGGED, not
# swallowed -- a silently missing router is how that went unnoticed. A (method, path) already
# registered (main_router serves some knowledge/swarm paths) is skipped, never duplicated.
# routes/flume_inline.py, not routes/flume.py, is the copy of the handlers that were live.
# tests/api/test_service_router_mounts.py pins every entry.
SERVICE_ROUTERS: tuple[tuple[str, str, str], ...] = (
    ("cohezion.api.routes.compound", "compound_router", ""),
    ("cohezion.api.routes.flume_inline", "flume_inline_router", ""),
    ("cohezion.api.routes.journeys_legacy", "journeys_legacy_router", ""),
    ("cohezion.api.routes.knowledge", "knowledge_router", ""),
    ("cohezion.api.routes.metrics", "metrics_router", ""),
    ("cohezion.api.routes.rl", "rl_router", ""),
    ("cohezion.api.routes.skills", "skills_router", ""),
    ("cohezion.api.routes.swarm", "swarm_router", ""),
    ("cohezion.api.routes.templates", "templates_router", ""),
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
)


def _route_keys(routes: list, prefix: str = "") -> set[tuple[str, str]]:
    return {
        (method, prefix + route.path)
        for route in routes
        if isinstance(route, APIRoute)
        for method in route.methods or ()
    }


# Tracked explicitly: FastAPI >=0.141 wraps included routers lazily, so app.router.routes does
# not list main_router's routes. main_router has no nested includes, so its .routes is complete.
_taken = _route_keys(main_router.routes)
for _module, _attr, _prefix in SERVICE_ROUTERS:
    try:
        _router = getattr(importlib.import_module(_module), _attr)
    except (ImportError, AttributeError) as exc:
        logger.warning("service router %s.%s not mounted: %s", _module, _attr, exc)
        continue
    _fresh = APIRouter()
    _fresh.routes.extend(
        r
        for r in _router.routes  # non-HTTP routes (websockets) have no keys: always keep them
        if not (isinstance(r, APIRoute) and _route_keys([r], _prefix) <= _taken)
    )
    _taken |= _route_keys(_fresh.routes, _prefix)
    app.include_router(_fresh, prefix=_prefix)

# Register Anima (system voice) endpoints
with contextlib.suppress(ImportError):
    from cohezion.api.services.anima import anima_router

    app.include_router(anima_router, prefix="/api/anima")

# Register Architecture Graph endpoints
with contextlib.suppress(ImportError):
    from cohezion.api.services.architecture import architecture_router

    app.include_router(architecture_router, prefix="/api/architecture")

# Register telemetry websocket
app.include_router(telemetry_router)

# Observability analytics endpoints (/metrics/unified, /cache, /efficiency, ...)
try:
    from cohezion.api.observability_endpoints import router as observability_router

    app.include_router(observability_router)
except ImportError:
    pass  # observability module not available

# Register Eigent workforce orchestration
app.include_router(eigent_router, prefix="/api")

# AG-UI protocol streaming endpoint
with contextlib.suppress(ImportError):
    from cohezion.api.routes.agui import agui_router

    app.include_router(agui_router, prefix="/api/agui")

# Training history (compound training loop data from SurrealDB)
with contextlib.suppress(ImportError):
    from cohezion.api.routes.training import training_router

    app.include_router(training_router)

# Work queue + Kanban UI (human-in-the-loop approval gate)
with contextlib.suppress(ImportError):
    from cohezion.api.work_queue_router import router as work_queue_router

    app.include_router(work_queue_router)

# SaaS Gateway (Zero-retention private inference + code audit commercial endpoints)
with contextlib.suppress(ImportError):
    from cohezion.api.routes.saas_gateway import router as saas_router

    app.include_router(saas_router)


__all__ = [
    "_compute_coherence",
    "_get_rl_policy",
    "_get_vae",
    "_rl_policy",
    "_vae_trainer",
    "app",
    "set_token_client",
]
