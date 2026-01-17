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
    
    # Full 12D physics state for each step
    # Dimensions: x, y, z, time, mass, sentiment, complexity, factuality, connectivity, stability, novelty, coherence
    
    # Simulate analyst steps - each has different perspective affecting physics
    analyst_states = [
        {  # Technical analyst
            "x": random.uniform(-0.3, 0.1), "y": random.uniform(0.2, 0.5), "z": random.uniform(0.3, 0.5),
            "time": 0.1, "mass": random.uniform(0.7, 0.85), "sentiment": random.uniform(0.4, 0.6),
            "complexity": random.uniform(0.7, 0.9), "factuality": random.uniform(0.8, 0.95),
            "connectivity": random.uniform(0.3, 0.5), "stability": random.uniform(0.6, 0.8),
            "novelty": random.uniform(0.5, 0.7), "coherence": random.uniform(0.7, 0.85),
        },
        {  # Ethical analyst
            "x": random.uniform(0.1, 0.4), "y": random.uniform(-0.3, 0.1), "z": random.uniform(0.4, 0.6),
            "time": 0.2, "mass": random.uniform(0.65, 0.8), "sentiment": random.uniform(0.5, 0.8),
            "complexity": random.uniform(0.5, 0.7), "factuality": random.uniform(0.6, 0.8),
            "connectivity": random.uniform(0.4, 0.6), "stability": random.uniform(0.5, 0.7),
            "novelty": random.uniform(0.6, 0.8), "coherence": random.uniform(0.65, 0.8),
        },
        {  # Historical analyst  
            "x": random.uniform(-0.4, -0.1), "y": random.uniform(-0.2, 0.2), "z": random.uniform(0.35, 0.55),
            "time": 0.3, "mass": random.uniform(0.6, 0.75), "sentiment": random.uniform(0.3, 0.5),
            "complexity": random.uniform(0.6, 0.8), "factuality": random.uniform(0.7, 0.9),
            "connectivity": random.uniform(0.5, 0.7), "stability": random.uniform(0.7, 0.85),
            "novelty": random.uniform(0.3, 0.5), "coherence": random.uniform(0.7, 0.85),
        },
    ]
    
    for i, (perspective, state) in enumerate(zip(["technical", "ethical", "historical"], analyst_states)):
        tracker.record_step(
            agent_type=AgentType.ANALYST,
            agent_name=f"analyst_{perspective}",
            perspective=perspective,
            input_text="What is the meaning of consciousness?",
            output_text=f"{perspective.title()} analysis of consciousness...",
            physics_state=state,
            duration_ms=random.uniform(200, 500),
            confidence=random.uniform(0.7, 0.9),
        )
    
    # Critic step - consolidates and critiques, high factuality check
    tracker.record_step(
        agent_type=AgentType.CRITIC,
        agent_name="critic_phi3",
        perspective=None,
        input_text="Three analyst perspectives on consciousness",
        output_text="Critique: Found 2 contradictions between perspectives...",
        physics_state={
            "x": 0.0, "y": 0.0, "z": 0.75,
            "time": 0.6, "mass": 0.9, "sentiment": 0.5,
            "complexity": 0.8, "factuality": 0.95,
            "connectivity": 0.8, "stability": 0.85,
            "novelty": 0.25, "coherence": 0.9,
        },
        duration_ms=350,
        confidence=0.88,
    )
    
    # Synthesizer step - final integration, high coherence and stability
    tracker.record_step(
        agent_type=AgentType.SYNTHESIZER,
        agent_name="synthesizer_mistral",
        perspective=None,
        input_text="Analyst outputs + critique",
        output_text="Synthesized understanding of consciousness integrating all perspectives...",
        physics_state={
            "x": 0.0, "y": 0.0, "z": 1.0,
            "time": 1.0, "mass": 1.0, "sentiment": 0.65,
            "complexity": 0.75, "factuality": 0.9,
            "connectivity": 0.95, "stability": 0.95,
            "novelty": 0.4, "coherence": 0.98,
        },
        duration_ms=400,
        confidence=0.92,
    )
    
    journey = tracker.end_journey(
        final_response="Consciousness is an emergent property...",
        final_confidence=0.92,
    )
    
    return {"journey_id": journey.journey_id, "steps": len(journey.steps)}


# Journey visualization endpoint
@app.get("/journeys/{journey_id}/visualize")
async def visualize_journey(journey_id: str):
    """Render an animated visualization of the journey trajectory."""
    from fastapi.responses import FileResponse
    from pathlib import Path
    import json
    import numpy as np
    
    from cohezion.viz.hypertools_renderer import HyperToolsViz
    from cohezion.swarm.journey_tracker import get_journey_tracker
    
    tracker = get_journey_tracker()
    journey_file = tracker.output_dir / f"{journey_id}.json"
    
    if not journey_file.exists():
        raise HTTPException(status_code=404, detail=f"Journey {journey_id} not found")
    
    journey = json.loads(journey_file.read_text())
    
    # Extract physics trajectory as numpy array
    trajectory_data = []
    for step in journey.get("steps", []):
        ps = step.get("physics_state", {})
        # Create 6D vector from physics state
        vec = [
            ps.get("x", 0),
            ps.get("y", 0),
            ps.get("z", 0),
            ps.get("mass", 0.5),
            ps.get("coherence", 0.5),
            ps.get("novelty", 0.5),
        ]
        trajectory_data.append(vec)
    
    if len(trajectory_data) < 2:
        raise HTTPException(status_code=400, detail="Journey needs at least 2 steps for visualization")
    
    trajectory = np.array(trajectory_data)
    
    # Render with HyperTools
    viz = HyperToolsViz(output_dir=Path("renders"))
    output_path = viz.animate_trajectory(
        trajectory,
        output_name=f"journey_{journey_id}",
        fps=2,  # Slow for visibility
    )
    
    return FileResponse(
        output_path,
        media_type="image/gif",
        filename=f"{journey_id}_trajectory.gif",
    )


# Static image visualization
@app.get("/journeys/{journey_id}/plot")
async def plot_journey(journey_id: str):
    """Render a multi-panel 12D physics visualization of the journey."""
    from fastapi.responses import FileResponse
    from pathlib import Path
    import json
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    from cohezion.swarm.journey_tracker import get_journey_tracker
    
    tracker = get_journey_tracker()
    journey_file = tracker.output_dir / f"{journey_id}.json"
    
    if not journey_file.exists():
        raise HTTPException(status_code=404, detail=f"Journey {journey_id} not found")
    
    journey = json.loads(journey_file.read_text())
    steps = journey.get("steps", [])
    
    # All 12 dimensions
    dims = ['x', 'y', 'z', 'time', 'mass', 'sentiment', 'complexity', 'factuality', 
            'connectivity', 'stability', 'novelty', 'coherence']
    
    # Extract all physics values
    physics_data = {d: [s["physics_state"].get(d, 0) for s in steps] for d in dims}
    agent_types = [s.get("agent_type", "unknown") for s in steps]
    
    # Color by agent type
    colors = {'analyst': '#818cf8', 'critic': '#f97316', 'synthesizer': '#22c55e'}
    point_colors = [colors.get(t, '#888888') for t in agent_types]
    
    # Create multi-panel figure
    fig = plt.figure(figsize=(16, 12), facecolor='#0a0a1a')
    
    # 3D spatial plot (main)
    ax3d = fig.add_subplot(2, 3, 1, projection='3d')
    ax3d.set_facecolor('#0a0a1a')
    ax3d.plot(physics_data['x'], physics_data['y'], physics_data['z'], 'w-', alpha=0.4, linewidth=2)
    for i, (x, y, z, c) in enumerate(zip(physics_data['x'], physics_data['y'], physics_data['z'], point_colors)):
        ax3d.scatter([x], [y], [z], c=c, s=150, alpha=0.9, edgecolors='white', linewidths=1)
        ax3d.text(x, y, z, f" {i+1}", color='white', fontsize=8)
    ax3d.set_xlabel('X', color='white')
    ax3d.set_ylabel('Y', color='white')
    ax3d.set_zlabel('Z', color='white')
    ax3d.set_title('Spatial Trajectory (X,Y,Z)', color='white', fontsize=10)
    ax3d.tick_params(colors='white', labelsize=7)
    
    # Mass & Time evolution
    ax_mass = fig.add_subplot(2, 3, 2, facecolor='#0a0a1a')
    step_nums = range(1, len(steps) + 1)
    ax_mass.bar(step_nums, physics_data['mass'], color=point_colors, alpha=0.8, label='Mass')
    ax_mass.plot(step_nums, physics_data['time'], 'w-o', markersize=6, label='Time')
    ax_mass.set_xlabel('Step', color='white')
    ax_mass.set_ylabel('Value', color='white')
    ax_mass.set_title('Mass & Time Evolution', color='white', fontsize=10)
    ax_mass.legend(facecolor='#1a1a2e', labelcolor='white', fontsize=8)
    ax_mass.tick_params(colors='white')
    ax_mass.set_ylim(0, 1.1)
    
    # Coherence & Stability (key metrics)
    ax_coh = fig.add_subplot(2, 3, 3, facecolor='#0a0a1a')
    ax_coh.fill_between(step_nums, physics_data['coherence'], alpha=0.3, color='#22c55e')
    ax_coh.plot(step_nums, physics_data['coherence'], 'g-o', markersize=8, label='Coherence', linewidth=2)
    ax_coh.fill_between(step_nums, physics_data['stability'], alpha=0.2, color='#818cf8')
    ax_coh.plot(step_nums, physics_data['stability'], 'b-s', markersize=6, label='Stability')
    ax_coh.set_xlabel('Step', color='white')
    ax_coh.set_ylabel('Value', color='white')
    ax_coh.set_title('Coherence & Stability', color='white', fontsize=10)
    ax_coh.legend(facecolor='#1a1a2e', labelcolor='white', fontsize=8)
    ax_coh.tick_params(colors='white')
    ax_coh.set_ylim(0, 1.1)
    
    # Novelty & Connectivity
    ax_nov = fig.add_subplot(2, 3, 4, facecolor='#0a0a1a')
    ax_nov.plot(step_nums, physics_data['novelty'], 'r-o', markersize=8, label='Novelty', linewidth=2)
    ax_nov.plot(step_nums, physics_data['connectivity'], 'c-^', markersize=6, label='Connectivity')
    ax_nov.set_xlabel('Step', color='white')
    ax_nov.set_ylabel('Value', color='white')
    ax_nov.set_title('Novelty & Connectivity', color='white', fontsize=10)
    ax_nov.legend(facecolor='#1a1a2e', labelcolor='white', fontsize=8)
    ax_nov.tick_params(colors='white')
    ax_nov.set_ylim(0, 1.1)
    
    # Sentiment, Complexity, Factuality
    ax_sent = fig.add_subplot(2, 3, 5, facecolor='#0a0a1a')
    width = 0.25
    x = np.array(list(step_nums))
    ax_sent.bar(x - width, physics_data['sentiment'], width, label='Sentiment', color='#f97316', alpha=0.8)
    ax_sent.bar(x, physics_data['complexity'], width, label='Complexity', color='#a78bfa', alpha=0.8)
    ax_sent.bar(x + width, physics_data['factuality'], width, label='Factuality', color='#22d3ee', alpha=0.8)
    ax_sent.set_xlabel('Step', color='white')
    ax_sent.set_ylabel('Value', color='white')
    ax_sent.set_title('Sentiment, Complexity, Factuality', color='white', fontsize=10)
    ax_sent.legend(facecolor='#1a1a2e', labelcolor='white', fontsize=7)
    ax_sent.tick_params(colors='white')
    ax_sent.set_ylim(0, 1.1)
    
    # Full 12D heatmap
    ax_heat = fig.add_subplot(2, 3, 6, facecolor='#0a0a1a')
    heatmap_data = np.array([physics_data[d] for d in dims])
    im = ax_heat.imshow(heatmap_data, aspect='auto', cmap='viridis', vmin=0, vmax=1)
    ax_heat.set_yticks(range(len(dims)))
    ax_heat.set_yticklabels([d.capitalize() for d in dims], fontsize=8, color='white')
    ax_heat.set_xticks(range(len(steps)))
    ax_heat.set_xticklabels([f"{i+1}" for i in range(len(steps))], color='white')
    ax_heat.set_xlabel('Step', color='white')
    ax_heat.set_title('12D Physics Heatmap', color='white', fontsize=10)
    cbar = plt.colorbar(im, ax=ax_heat, shrink=0.8)
    cbar.ax.yaxis.set_tick_params(color='white')
    cbar.ax.yaxis.set_ticklabels([f'{x:.1f}' for x in cbar.get_ticks()], color='white')
    
    # Title
    fig.suptitle(f"12D Physics Journey: {journey['query'][:50]}...", 
                 color='white', fontsize=14, fontweight='bold', y=0.98)
    
    # Legend for agent types
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=colors['analyst'], label='Analyst'),
        Patch(facecolor=colors['critic'], label='Critic'),
        Patch(facecolor=colors['synthesizer'], label='Synthesizer'),
    ]
    fig.legend(handles=legend_elements, loc='lower center', ncol=3, 
               facecolor='#1a1a2e', labelcolor='white', fontsize=9)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    output_dir = Path("renders")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"journey_{journey_id}_12d_plot.png"
    plt.savefig(output_path, dpi=150, facecolor='#0a0a1a', bbox_inches='tight')
    plt.close()
    
    return FileResponse(
        output_path,
        media_type="image/png",
        filename=f"{journey_id}_12d_plot.png",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

