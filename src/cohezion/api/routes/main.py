"""Main REST and A2A API routes for Cohezion FastAPI application."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, field_validator

from cohezion.api.routes.agentjet import TrainRequest
from cohezion.api.routes.knowledge import SearchRequest
from cohezion.api.routes.swarm import DebateRequest, DebateResponse
from cohezion.mcp.knowledge_server import get_server as get_knowledge_server
from cohezion.mcp.manager.auth import validate_token
from cohezion.mcp.registry import get_registry
from cohezion.mcp.swarm_server import get_server as get_swarm_server
from cohezion.protocols.a2a_server import A2AServer, AgentCard


logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize A2A server (singleton at module level)
_a2a_server = A2AServer(
    agent_card=AgentCard(
        name="Cohezion Portfolio Agent",
        description="FLUME VAE latent space navigation, Compound Loop engineering, Universe Simulation, Swarm Orchestration, and Evaluation Infrastructure",
        url=os.getenv("PUBLIC_API_URL", "http://localhost:8080"),
        version="1.0.2",
        capabilities=[
            "simulation",
            "synthesis",
            "routing",
            "analysis",
            "flume-vae",
            "compound-loop",
        ],
    )
)


# Authentication dependency for A2A endpoints
async def verify_a2a_token(x_cohezion_key: str | None = Header(None)) -> str:
    """Validate X-Cohezion-Key header for A2A endpoints."""
    if not x_cohezion_key:
        raise HTTPException(
            status_code=401,
            detail="Missing X-Cohezion-Key header. Obtain token from ~/.cohezion/auth.token",
        )

    if not validate_token(x_cohezion_key):
        raise HTTPException(status_code=403, detail="Invalid API key")

    return x_cohezion_key


# Health check
@router.get("/health")
async def health():
    return {"status": "healthy", "service": "cohezion"}


# MCP Registry endpoints
@router.get("/mcp/servers")
async def list_servers():
    """List all available MCP servers."""
    registry = get_registry()
    return {
        "servers": [
            {"name": s.name, "type": s.type, "status": s.status} for s in registry.list_servers()
        ]
    }


@router.get("/mcp/tools")
async def list_tools():
    """List all available MCP tools."""
    registry = get_registry()
    return {"tools": registry.list_tools()}


# Knowledge endpoints
@router.post("/knowledge/search")
async def search_knowledge(request: SearchRequest):
    """Search knowledge base."""
    server = get_knowledge_server()
    results = server.search_knowledge(request.query, request.limit)
    return {"results": results}


@router.get("/knowledge/skills")
async def list_skills():
    """List all skills."""
    server = get_knowledge_server()
    return {"skills": server.list_skills()}


@router.get("/knowledge/skills/{skill_name}")
async def get_skill(skill_name: str):
    """Get a specific skill."""
    server = get_knowledge_server()
    result = server.get_skill(skill_name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# Swarm endpoints
@router.post("/swarm/debate", response_model=DebateResponse)
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
        logger.error(f"Debate failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/swarm/perspectives")
async def get_perspectives():
    """Get available analyst perspectives."""
    server = get_swarm_server()
    return {"perspectives": server.get_perspectives()}


@router.get("/swarm/metrics")
async def get_metrics():
    """Get swarm workflow metrics."""
    server = get_swarm_server()
    return {"metrics": server.get_metrics()}


# Notebook endpoints
@router.get("/notebooks")
async def list_notebooks():
    """List all research notebooks."""
    notebooks_dir = Path("docs/notebooks")
    if not notebooks_dir.exists():
        return {"notebooks": []}
    notebooks = [f.stem for f in notebooks_dir.glob("*.md")]
    return {"notebooks": notebooks}


@router.get("/notebooks/{name}")
async def get_notebook(name: str):
    """Get a specific notebook."""
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise HTTPException(status_code=400, detail="Invalid notebook name")

    base_dir = Path("docs/notebooks").resolve()
    notebook_path = (base_dir / f"{name}.md").resolve()

    if not str(notebook_path).startswith(str(base_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not notebook_path.exists():
        raise HTTPException(status_code=404, detail="Notebook not found")
    return {"name": name, "content": notebook_path.read_text()}


# Simulation endpoints
@router.get("/simulations")
async def list_simulations():
    """List all physics simulations."""
    import json

    sim_file = Path("src/cohezion/knowledge_graph/universe_nodes/physics_simulations.json")
    if not sim_file.exists():
        return {"simulations": []}
    data = json.loads(sim_file.read_text())
    return {"simulations": [s["id"] for s in data.get("simulations", [])]}


@router.get("/simulations/{sim_id}")
async def get_simulation(sim_id: str):
    """Get a specific simulation result."""
    import json

    sim_file = Path("src/cohezion/knowledge_graph/universe_nodes/physics_simulations.json")
    if not sim_file.exists():
        raise HTTPException(status_code=404, detail="No simulations found")
    data = json.loads(sim_file.read_text())
    for sim in data.get("simulations", []):
        if sim["id"] == sim_id:
            return sim
    raise HTTPException(status_code=404, detail=f"Simulation {sim_id} not found")


class TrainResponse(BaseModel):
    success: bool
    model_name: str
    base_model: str
    skill_domain: str | None
    epochs_completed: int
    samples_used: int
    avg_reward: float
    training_duration_s: float
    dry_run: bool
    error: str | None = None


@router.post("/agentjet/train")
async def agentjet_train(request: TrainRequest) -> TrainResponse:
    """Start an AgentJet CALL training cycle."""
    try:
        from cohezion.agentjet.trainer import AgentJetTrainer

        trainer = AgentJetTrainer()
        result = await trainer.train(
            target_model=request.target_model,
            skill_domain=request.skill_domain,
            epochs=request.epochs,
            min_phi=request.min_phi,
            dry_run=request.dry_run,
        )
        return TrainResponse(
            success=result.success,
            model_name=result.model_name,
            base_model=result.base_model,
            skill_domain=result.skill_domain,
            epochs_completed=result.epochs_completed,
            samples_used=result.samples_used,
            avg_reward=result.avg_reward,
            training_duration_s=result.training_duration_s,
            dry_run=result.dry_run,
            error=result.error,
        )
    except Exception as e:
        _oom_names = ("OOMRiskError", "ResourceUnavailableError")
        if type(e).__name__ in _oom_names:
            raise HTTPException(status_code=503, detail=str(e)) from e
        return TrainResponse(
            success=False,
            model_name="",
            base_model=request.target_model,
            skill_domain=request.skill_domain,
            epochs_completed=0,
            samples_used=0,
            avg_reward=0.0,
            training_duration_s=0.0,
            dry_run=request.dry_run,
            error=str(e),
        )


@router.get("/agentjet/status")
async def agentjet_status() -> dict:
    """Get AgentJet CALL system status."""
    try:
        from cohezion.agentjet.context_optimizer import OllamaContextManager

        mgr = OllamaContextManager()
        available_gb = await mgr.get_available_memory_gb()
        loaded_models = await mgr.get_loaded_models()
        return {
            "status": "ready",
            "available_memory_gb": available_gb,
            "loaded_models": loaded_models,
            "backend": "llamafactory",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/agentjet/models")
async def agentjet_models() -> dict:
    """List available training target models."""
    from cohezion.agentjet.context_optimizer import CONTEXT_PROFILES

    targets = [
        {"model": k, "size_gb": v.size_gb, "num_ctx": v.num_ctx}
        for k, v in CONTEXT_PROFILES.items()
        if not k.endswith(":training") and k != "default"
    ]
    return {
        "training_targets": targets,
        "recommended": ["qwen3.5:9b", "nemotron-3-nano:30b", "phi3:mini"],
    }


# A2A Protocol Endpoints
@router.get("/.well-known/agent.json")
async def get_agent_card():
    """A2A Protocol: Agent discovery endpoint."""
    return _a2a_server.get_agent_card()


@router.get("/agents")
async def list_agents() -> dict:
    """A2A multi-agent discovery: list all discoverable specialist agents."""
    from cohezion.registry.capability_registry import CapabilityRegistry

    registry = CapabilityRegistry(root_dir=Path(__file__).parents[4])
    agent_caps = [c for c in registry.capabilities if c.type == "agent"]
    return {
        "count": len(agent_caps),
        "agents": [
            {
                "id": c.name,
                "name": c.name,
                "description": c.description,
                "path": c.path,
                "tags": c.tags,
            }
            for c in agent_caps
        ],
    }


class A2AMessageModel(BaseModel):
    """A2A message format with size validation."""

    role: str
    parts: list[dict[str, Any]]

    @field_validator("parts")
    @classmethod
    def validate_parts_size(cls, parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        import json

        serialized = json.dumps(parts)
        size_bytes = len(serialized.encode("utf-8"))
        max_size = 1_048_576  # 1 MB

        if size_bytes > max_size:
            raise ValueError(
                f"Message parts exceed maximum size of {max_size} bytes (got {size_bytes} bytes)"
            )

        return parts


class A2ASendTaskRequest(BaseModel):
    """Request body for POST /tasks/send."""

    message: A2AMessageModel
    task_id: str | None = None


@router.post("/tasks/send")
async def send_a2a_task(request: A2ASendTaskRequest, api_key: str = Depends(verify_a2a_token)):
    """A2A Protocol: Task submission endpoint."""
    if not request.message.parts:
        raise HTTPException(status_code=400, detail="Message parts cannot be empty")

    task = await _a2a_server.send_task(
        message={"role": request.message.role, "parts": request.message.parts},
        task_id=request.task_id,
    )

    return {
        "id": task.id,
        "state": task.state,
        "messages": [{"role": m.role, "parts": m.parts} for m in task.messages],
        "updated_at": task.updated_at,
    }


@router.get("/tasks/{task_id}")
async def get_a2a_task(task_id: str, api_key: str = Depends(verify_a2a_token)):
    """A2A Protocol: Task status endpoint."""
    task = await _a2a_server.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return {
        "id": task.id,
        "state": task.state,
        "messages": [{"role": m.role, "parts": m.parts} for m in task.messages],
        "updated_at": task.updated_at,
    }


@router.post("/tasks/{task_id}/cancel")
async def cancel_a2a_task(task_id: str, api_key: str = Depends(verify_a2a_token)):
    """A2A Protocol: Task cancellation endpoint."""
    success = await _a2a_server.cancel_task(task_id)

    task = await _a2a_server.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return {"canceled": success, "state": task.state}
