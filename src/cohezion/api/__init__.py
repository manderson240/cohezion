"""
Cohezion API - FastAPI server exposing swarm and MCP tools.

Provides REST endpoints for Open-Notebook integration.
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from cohezion.api.helpers import get_rl_policy, get_vae, reset_rl_policy, reset_vae
from cohezion.api.routes_admin import compare_router, knowledge_router, swarm_router
from cohezion.api.routes_compound import router as compound_router
from cohezion.api.routes_core import (
    health_router,
    mcp_router,
)
from cohezion.api.routes_core import (
    knowledge_router as core_knowledge_router,
)
from cohezion.api.routes_core import (
    swarm_router as core_swarm_router,
)
from cohezion.api.routes_flume import router as flume_router
from cohezion.api.routes_journeys import router as journeys_router
from cohezion.api.routes_metrics import router as metrics_router
from cohezion.api.routes_metrics import set_token_client
from cohezion.api.routes_misc import router as misc_router
from cohezion.api.routes_rl import router as rl_router
from cohezion.api.routes_skills import query_router
from cohezion.api.routes_skills import router as skills_router
from cohezion.security.middleware import add_security_headers_middleware, add_security_middleware


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cohezion API",
    description="AI Research Lab API - Swarm workflows and MCP tools",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


app.include_router(health_router)
app.include_router(mcp_router)
app.include_router(core_knowledge_router)
app.include_router(core_swarm_router)
app.include_router(journeys_router)
app.include_router(flume_router)
app.include_router(rl_router)
app.include_router(metrics_router)
app.include_router(skills_router)
app.include_router(query_router)
app.include_router(compound_router)
app.include_router(knowledge_router)
app.include_router(swarm_router)
app.include_router(compare_router)
app.include_router(misc_router)

# Add security middleware (must be after all routes)
add_security_middleware(app)
add_security_headers_middleware(app)


__all__ = [
    "app",
    "get_rl_policy",
    "get_vae",
    "reset_rl_policy",
    "reset_vae",
    "set_token_client",
]
