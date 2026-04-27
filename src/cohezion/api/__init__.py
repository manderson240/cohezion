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

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from cohezion.api._helpers import compute_coherence as _compute_coherence
from cohezion.api._helpers import get_rl_policy as _get_rl_policy
from cohezion.api._helpers import get_vae as _get_vae
from cohezion.api.routes.a2a import _a2a_server, a2a_router, verify_a2a_token
from cohezion.api.routes.agentjet import agentjet_router
from cohezion.api.routes.compound import compound_router
from cohezion.api.routes.flume_inline import flume_inline_router
from cohezion.api.routes.journeys_legacy import journeys_legacy_router
from cohezion.api.routes.knowledge import knowledge_router
from cohezion.api.routes.mcp import mcp_router
from cohezion.api.routes.metrics import metrics_router, set_token_client
from cohezion.api.routes.notebooks import notebooks_router
from cohezion.api.routes.rl import rl_router
from cohezion.api.routes.skills import skills_router
from cohezion.api.routes.swarm import swarm_router
from cohezion.api.routes.templates import templates_router
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


# Health check
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "cohezion"}


# --- Mount extracted routers (Wave 2B refactor) ---
# Order matches the original file roughly so OpenAPI ordering stays similar.
app.include_router(mcp_router)
app.include_router(knowledge_router)
app.include_router(swarm_router)
app.include_router(notebooks_router)
app.include_router(journeys_legacy_router)
app.include_router(flume_inline_router)
app.include_router(templates_router)
app.include_router(rl_router)
app.include_router(skills_router)
app.include_router(metrics_router)
app.include_router(compound_router)
app.include_router(agentjet_router)
app.include_router(a2a_router)


# Register research endpoints (late import to avoid circular dependencies)
try:
    from cohezion.api.research_endpoints import router as research_router

    app.include_router(research_router)
except ImportError:
    pass  # research module not available

# Register universe simulation endpoints
try:
    from cohezion.api.services.universe import universe_router

    app.include_router(universe_router, prefix="/api/universe")
except ImportError:
    pass  # universe module not available

# Register Genesis Engine endpoints (grounded physics layer)
try:
    from cohezion.api.services.genesis import genesis_router

    app.include_router(genesis_router, prefix="/api")
except ImportError:
    pass  # genesis module not available

# Register World Model endpoints (JEPA predictor)
try:
    from cohezion.api.services.world_model import world_model_router

    app.include_router(world_model_router, prefix="/api")
except ImportError:
    pass  # world_model module not available

# Register extended physics endpoints (bioelectric, natural-capital, cosmogony chain)
try:
    from cohezion.api.services.physics_extended import physics_ext_router

    app.include_router(physics_ext_router, prefix="/api")
except ImportError:
    pass  # physics_extended module not available

# Register Worldview Explorer endpoints (indigenous cosmologies)
try:
    from cohezion.api.services.worldviews import worldviews_router

    app.include_router(worldviews_router, prefix="/api")
except ImportError:
    pass  # worldviews module not available

# Register journey analysis endpoints
try:
    from cohezion.api.journeys import router as journeys_router

    app.include_router(journeys_router, prefix="/api/journeys")
except ImportError:
    pass  # journeys module not available

# Register Ouroboros self-healing endpoints
try:
    from cohezion.api.services.ouroboros_api import ouroboros_router

    app.include_router(ouroboros_router, prefix="/api")
except ImportError:
    pass  # ouroboros module not available

# Register Mycelium knowledge network endpoints
try:
    from cohezion.api.services.mycelium_api import mycelium_router

    app.include_router(mycelium_router, prefix="/api")
except ImportError:
    pass  # mycelium module not available

# Register disconnected modules API (M24)
try:
    from cohezion.api.services.modules_api import modules_router

    app.include_router(modules_router, prefix="/api")
except ImportError:
    pass  # modules API not available

# Register Anima (system voice) endpoints
try:
    from cohezion.api.services.anima import anima_router

    app.include_router(anima_router, prefix="/api/anima")
except ImportError:
    pass  # anima module not available

# Register Architecture Graph endpoints
try:
    from cohezion.api.services.architecture import architecture_router

    app.include_router(architecture_router, prefix="/api/architecture")
except ImportError:
    pass  # architecture module not available

# Register telemetry websocket
app.include_router(telemetry_router)

# AG-UI protocol streaming endpoint
try:
    from cohezion.api.routes.agui import agui_router

    app.include_router(agui_router, prefix="/api/agui")
except ImportError:
    pass  # agui module not available


# Training history (compound training loop data from SurrealDB)
try:
    from cohezion.api.routes.training import training_router

    app.include_router(training_router)
except ImportError:
    pass  # training routes not available


__all__ = [
    "app",
    "set_token_client",
    "_get_vae",
    "_get_rl_policy",
    "_compute_coherence",
    "_a2a_server",
    "verify_a2a_token",
    "_vae_trainer",
    "_rl_policy",
]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
