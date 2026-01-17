"""
Cohezion API - FastAPI server exposing swarm and MCP tools.

Provides REST endpoints for Open-Notebook integration.
"""

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from cohezion.mcp.registry import get_registry
from cohezion.mcp.knowledge_server import get_server as get_knowledge_server
from cohezion.mcp.swarm_server import get_server as get_swarm_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cohezion API",
    description="AI Research Lab API - Swarm workflows and MCP tools",
    version="0.1.0",
)

# CORS for Open-Notebook
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")


# Root redirect to UI
@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


# Pydantic models
class DebateRequest(BaseModel):
    query: str
    perspectives: list[str] | None = None


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


class DebateResponse(BaseModel):
    content: str
    confidence: float
    model_chain: list[str]
    processing_time_ms: float


# Health check
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "cohezion"}


# MCP Registry endpoints
@app.get("/mcp/servers")
async def list_servers():
    """List all available MCP servers."""
    registry = get_registry()
    return {
        "servers": [
            {"name": s.name, "type": s.type, "status": s.status}
            for s in registry.list_servers()
        ]
    }


@app.get("/mcp/tools")
async def list_tools():
    """List all available MCP tools."""
    registry = get_registry()
    return {"tools": registry.list_tools()}


# Knowledge endpoints
@app.post("/knowledge/search")
async def search_knowledge(request: SearchRequest):
    """Search knowledge base."""
    server = get_knowledge_server()
    results = server.search_knowledge(request.query, request.limit)
    return {"results": results}


@app.get("/knowledge/skills")
async def list_skills():
    """List all skills."""
    server = get_knowledge_server()
    return {"skills": server.list_skills()}


@app.get("/knowledge/skills/{skill_name}")
async def get_skill(skill_name: str):
    """Get a specific skill."""
    server = get_knowledge_server()
    result = server.get_skill(skill_name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# Swarm endpoints
@app.post("/swarm/debate", response_model=DebateResponse)
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
        logger.error(f"Debate failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/swarm/perspectives")
async def get_perspectives():
    """Get available analyst perspectives."""
    server = get_swarm_server()
    return {"perspectives": server.get_perspectives()}


@app.get("/swarm/metrics")
async def get_metrics():
    """Get swarm workflow metrics."""
    server = get_swarm_server()
    return {"metrics": server.get_metrics()}


# Notebook endpoints
@app.get("/notebooks")
async def list_notebooks():
    """List all research notebooks."""
    import os
    from pathlib import Path
    notebooks_dir = Path("docs/notebooks")
    if not notebooks_dir.exists():
        return {"notebooks": []}
    notebooks = [f.stem for f in notebooks_dir.glob("*.md")]
    return {"notebooks": notebooks}


@app.get("/notebooks/{name}")
async def get_notebook(name: str):
    """Get a specific notebook."""
    from pathlib import Path
    notebook_path = Path(f"docs/notebooks/{name}.md")
    if not notebook_path.exists():
        raise HTTPException(status_code=404, detail=f"Notebook {name} not found")
    return {"name": name, "content": notebook_path.read_text()}


# Simulation endpoints
@app.get("/simulations")
async def list_simulations():
    """List all physics simulations."""
    import json
    from pathlib import Path
    sim_file = Path("src/cohezion/knowledge_graph/universe_nodes/physics_simulations.json")
    if not sim_file.exists():
        return {"simulations": []}
    data = json.loads(sim_file.read_text())
    return {"simulations": [s["id"] for s in data.get("simulations", [])]}


@app.get("/simulations/{sim_id}")
async def get_simulation(sim_id: str):
    """Get a specific simulation result."""
    import json
    from pathlib import Path
    sim_file = Path("src/cohezion/knowledge_graph/universe_nodes/physics_simulations.json")
    if not sim_file.exists():
        raise HTTPException(status_code=404, detail="No simulations found")
    data = json.loads(sim_file.read_text())
    for sim in data.get("simulations", []):
        if sim["id"] == sim_id:
            return sim
    raise HTTPException(status_code=404, detail=f"Simulation {sim_id} not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

