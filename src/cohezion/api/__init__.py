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


# Journey endpoints - Agent trajectory visualization
@app.get("/journeys")
async def list_journeys():
    """List recent agent journeys."""
    from cohezion.swarm.journey_tracker import get_journey_tracker
    tracker = get_journey_tracker()
    journeys = tracker.get_recent_journeys(limit=20)
    return {"journeys": [{"id": j["journey_id"], "query": j["query"][:50], "steps": j["step_count"]} for j in journeys]}


@app.get("/journeys/{journey_id}")
async def get_journey(journey_id: str):
    """Get a specific journey with full trajectory."""
    from cohezion.swarm.journey_tracker import get_journey_tracker
    tracker = get_journey_tracker()
    journey_file = tracker.output_dir / f"{journey_id}.json"
    if not journey_file.exists():
        raise HTTPException(status_code=404, detail=f"Journey {journey_id} not found")
    import json
    return json.loads(journey_file.read_text())


@app.get("/journeys/{journey_id}/trajectory")
async def get_journey_trajectory(journey_id: str):
    """Get physics trajectory for visualization."""
    from cohezion.swarm.journey_tracker import get_journey_tracker
    tracker = get_journey_tracker()
    trajectory = tracker.get_journey_trajectory(journey_id)
    if not trajectory:
        raise HTTPException(status_code=404, detail=f"Journey {journey_id} not found")
    return {"trajectory": trajectory}


# Demo journey endpoint
@app.post("/journeys/demo")
async def create_demo_journey():
    """Create a demo journey to showcase visualization."""
    from cohezion.swarm.journey_tracker import get_journey_tracker, AgentType
    import random
    
    tracker = get_journey_tracker()
    journey_id = tracker.start_journey("What is the meaning of consciousness?")
    
    # Simulate analyst steps
    for perspective in ["technical", "ethical", "historical"]:
        tracker.record_step(
            agent_type=AgentType.ANALYST,
            agent_name=f"analyst_{perspective}",
            perspective=perspective,
            input_text="What is the meaning of consciousness?",
            output_text=f"{perspective.title()} analysis of consciousness...",
            physics_state={
                "x": random.uniform(-0.5, 0.5),
                "y": random.uniform(-0.5, 0.5),
                "z": random.uniform(0.3, 0.7),
                "mass": random.uniform(0.6, 0.9),
                "coherence": random.uniform(0.7, 0.95),
                "novelty": random.uniform(0.4, 0.8),
            },
            duration_ms=random.uniform(200, 500),
            confidence=random.uniform(0.7, 0.9),
        )
    
    # Critic step
    tracker.record_step(
        agent_type=AgentType.CRITIC,
        agent_name="critic_phi3",
        perspective=None,
        input_text="Three analyst perspectives on consciousness",
        output_text="Critique: Found 2 contradictions between perspectives...",
        physics_state={
            "x": 0.0, "y": 0.0, "z": 0.8,
            "mass": 0.95, "coherence": 0.92, "novelty": 0.3,
        },
        duration_ms=350,
        confidence=0.88,
    )
    
    # Synthesizer step
    tracker.record_step(
        agent_type=AgentType.SYNTHESIZER,
        agent_name="synthesizer_mistral",
        perspective=None,
        input_text="Analyst outputs + critique",
        output_text="Synthesized understanding of consciousness integrating all perspectives...",
        physics_state={
            "x": 0.0, "y": 0.0, "z": 1.0,
            "mass": 1.0, "coherence": 0.95, "novelty": 0.5,
        },
        duration_ms=400,
        confidence=0.92,
    )
    
    journey = tracker.end_journey(
        final_response="Consciousness is an emergent property...",
        final_confidence=0.92,
    )
    
    return {"journey_id": journey.journey_id, "steps": len(journey.steps)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

