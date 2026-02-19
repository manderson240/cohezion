"""Core API endpoints - health, MCP, knowledge, swarm."""

import logging

from fastapi import APIRouter, HTTPException

from cohezion.api.models import DebateRequest, DebateResponse, SearchRequest
from cohezion.mcp.knowledge_server import get_server as get_knowledge_server
from cohezion.mcp.registry import get_registry
from cohezion.mcp.swarm_server import get_server as get_swarm_server


logger = logging.getLogger(__name__)

# Create routers
health_router = APIRouter(tags=["health"])
mcp_router = APIRouter(prefix="/mcp", tags=["mcp"])
knowledge_router = APIRouter(prefix="/knowledge", tags=["knowledge"])
swarm_router = APIRouter(prefix="/swarm", tags=["swarm"])


# Health endpoint
@health_router.get("/health")
async def health():
    return {"status": "healthy", "service": "cohezion"}


# MCP endpoints
@mcp_router.get("/servers")
async def list_servers():
    """List all available MCP servers."""
    registry = get_registry()
    return {
        "servers": [
            {"name": s.name, "type": s.type, "status": s.status}
            for s in registry.list_servers()
        ]
    }


@mcp_router.get("/tools")
async def list_tools():
    """List all available MCP tools."""
    registry = get_registry()
    return {"tools": registry.list_tools()}


# Knowledge endpoints
@knowledge_router.post("/search")
async def search_knowledge(request: SearchRequest):
    """Search knowledge base."""
    server = get_knowledge_server()
    results = server.search_knowledge(request.query, request.limit)
    return {"results": results}


@knowledge_router.get("/skills")
async def list_skills():
    """List all skills."""
    server = get_knowledge_server()
    return {"skills": server.list_skills()}


@knowledge_router.get("/skills/{skill_name}")
async def get_skill(skill_name: str):
    """Get a specific skill."""
    server = get_knowledge_server()
    result = server.get_skill(skill_name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# Swarm endpoints
@swarm_router.post("/debate", response_model=DebateResponse)
async def run_debate(request: DebateRequest):
    """Run a multi-perspective debate."""
    server = get_swarm_server()
    try:
        result = server.run_debate(request.query, request.perspectives)
        return DebateResponse(
            content=result["content"],
            confidence=result["confidence"],
            model_chain=result["model_chain"],
            processing_time_ms=result["processing_time_ms"],
        )
    except Exception as e:
        logger.error("Debate failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@swarm_router.get("/perspectives")
async def get_perspectives():
    """Get available analyst perspectives."""
    server = get_swarm_server()
    return {"perspectives": server.get_perspectives()}


@swarm_router.get("/metrics")
async def get_metrics():
    """Get swarm workflow metrics."""
    server = get_swarm_server()
    return {"metrics": server.get_metrics()}
