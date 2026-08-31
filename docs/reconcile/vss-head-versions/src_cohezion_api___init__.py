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
import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
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


__all__ = [
    "_compute_coherence",
    "_get_rl_policy",
    "_get_vae",
    "_rl_policy",
    "_vae_trainer",
    "app",
    "set_token_client",
]
