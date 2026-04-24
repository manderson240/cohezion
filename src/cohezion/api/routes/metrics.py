"""Observability / metrics routes (Phase 3D).

Extracted from api/__init__.py (Wave 2B of synthetic-sniffing-panda).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel


logger = logging.getLogger(__name__)

metrics_router = APIRouter(tags=["metrics"])


class AgentMetrics(BaseModel):
    name: str
    type: str
    description: str
    metrics: dict[str, Any] = {}


class AgentMetricsResponse(BaseModel):
    count: int
    agents: list[AgentMetrics]


class TrainingMetricsResponse(BaseModel):
    flume_vae: dict[str, Any]
    rl_policy: dict[str, Any]


class PipelineStageStatus(BaseModel):
    stage: str
    status: str
    detail: str = ""


class PipelineStatusResponse(BaseModel):
    stages: list[PipelineStageStatus]
    complete_count: int
    total_count: int


class SystemMetricsResponse(BaseModel):
    cpu_percent: float
    memory_total_gb: float
    memory_available_gb: float
    memory_percent: float
    ollama_available: bool
    ollama_models: list[str] = []


class TokenMetricsResponse(BaseModel):
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0
    tokens_saved: int = 0
    total_calls: int = 0
    model_usage: dict[str, int] = {}


class CompoundMetricsResponse(BaseModel):
    total_learnings: int = 0
    top_compound_scores: list[dict[str, Any]] = []
    suggested_refinements: list[dict[str, Any]] = []
    total_executions: int = 0


@metrics_router.get("/metrics/agents", response_model=AgentMetricsResponse)
async def metrics_agents():
    """Return registered agent stats from CapabilityRegistry."""
    from cohezion.registry.capability_registry import CapabilityRegistry

    registry = CapabilityRegistry()
    caps = registry.find("agent", top_k=50)
    agents = [
        AgentMetrics(
            name=cap.name,
            type=cap.type,
            description=cap.description,
            metrics={"score": round(cap.score, 4), "path": cap.path},
        )
        for cap in caps
    ]
    return AgentMetricsResponse(count=len(agents), agents=agents)


@metrics_router.get("/metrics/training", response_model=TrainingMetricsResponse)
async def metrics_training():
    """Return training metrics from checkpoint files."""
    import json as _json

    flume_info: dict[str, Any] = {"status": "no_checkpoint"}
    rl_info: dict[str, Any] = {"status": "no_checkpoint"}

    # FLUME VAE
    flume_metrics = Path("data/flume/checkpoints/training_metrics.json")
    flume_ckpt = Path("data/flume/checkpoints/flume_vae_ep50.pt")
    if flume_metrics.exists():
        try:
            data = _json.loads(flume_metrics.read_text())
            flume_info = {
                "status": "trained",
                "epochs": len(data) if isinstance(data, list) else data.get("epochs", 0),
                "checkpoint": str(flume_ckpt) if flume_ckpt.exists() else None,
                "metrics": data if isinstance(data, dict) else {"epoch_data": data[-3:]},
            }
        except (OSError, _json.JSONDecodeError, ValueError, KeyError, AttributeError, TypeError):
            flume_info = {"status": "checkpoint_found", "path": str(flume_metrics)}
    elif flume_ckpt.exists():
        flume_info = {"status": "checkpoint_found", "path": str(flume_ckpt)}

    # RL Policy
    rl_metrics = Path("data/rl/checkpoints/training_metrics.json")
    rl_ckpt = Path("data/rl/checkpoints/policy_final.pt")
    if rl_metrics.exists():
        try:
            data = _json.loads(rl_metrics.read_text())
            rl_info = {
                "status": "trained",
                "episodes": len(data) if isinstance(data, list) else data.get("episodes", 0),
                "checkpoint": str(rl_ckpt) if rl_ckpt.exists() else None,
                "metrics": data if isinstance(data, dict) else {"episode_data": data[-3:]},
            }
        except (OSError, _json.JSONDecodeError, ValueError, KeyError, AttributeError, TypeError):
            rl_info = {"status": "checkpoint_found", "path": str(rl_metrics)}
    elif rl_ckpt.exists():
        rl_info = {"status": "checkpoint_found", "path": str(rl_ckpt)}

    return TrainingMetricsResponse(flume_vae=flume_info, rl_policy=rl_info)


@metrics_router.get("/metrics/pipeline", response_model=PipelineStatusResponse)
async def metrics_pipeline():
    """Return pipeline stage completion status."""
    stages: list[PipelineStageStatus] = []

    # Stage 1: Mass sim .npy export
    npy_dir = Path("data/mass_sim/artifacts")
    npy_files = list(npy_dir.glob("*.npy")) if npy_dir.exists() else []
    stages.append(
        PipelineStageStatus(
            stage="mass_sim_export",
            status="complete" if npy_files else "pending",
            detail=f"{len(npy_files)} .npy files" if npy_files else "No .npy exports found",
        )
    )

    # Stage 2: VAE training
    vae_ckpt = Path("data/flume/checkpoints/flume_vae_ep50.pt")
    stages.append(
        PipelineStageStatus(
            stage="vae_training",
            status="complete" if vae_ckpt.exists() else "pending",
            detail=str(vae_ckpt) if vae_ckpt.exists() else "No VAE checkpoint",
        )
    )

    # Stage 3: RL training
    rl_ckpt = Path("data/rl/checkpoints/policy_final.pt")
    stages.append(
        PipelineStageStatus(
            stage="rl_training",
            status="complete" if rl_ckpt.exists() else "pending",
            detail=str(rl_ckpt) if rl_ckpt.exists() else "No RL checkpoint",
        )
    )

    # Stage 4: Weight bridge
    pipeline_ran = Path("data/pipeline_results")
    stages.append(
        PipelineStageStatus(
            stage="weight_bridge",
            status="complete" if pipeline_ran.exists() else "pending",
            detail="Weight bridge validated" if pipeline_ran.exists() else "Not yet executed",
        )
    )

    complete = sum(1 for s in stages if s.status == "complete")
    return PipelineStatusResponse(stages=stages, complete_count=complete, total_count=len(stages))


@metrics_router.get("/metrics/system", response_model=SystemMetricsResponse)
async def metrics_system():
    """Return system resource metrics."""
    import psutil

    mem = psutil.virtual_memory()

    # Check Ollama availability
    ollama_available = False
    ollama_models: list[str] = []
    try:
        import asyncio
        import httpx as _httpx

        async with _httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                ollama_available = True
                models_data = resp.json().get("models", [])
                ollama_models = [m["name"] for m in models_data]
    except (
        _httpx.HTTPError,
        _httpx.TimeoutException,
        OSError,
        ConnectionError,
        ValueError,
        KeyError,
        TypeError,
        asyncio.TimeoutError,
    ) as e:
        logger.debug("Ollama status check unavailable: %s", e)

    return SystemMetricsResponse(
        cpu_percent=psutil.cpu_percent(interval=0.1),
        memory_total_gb=round(mem.total / (1024**3), 2),
        memory_available_gb=round(mem.available / (1024**3), 2),
        memory_percent=mem.percent,
        ollama_available=ollama_available,
        ollama_models=ollama_models,
    )


@metrics_router.get("/metrics/tokens", response_model=TokenMetricsResponse)
async def metrics_tokens():
    """Return token efficiency metrics from the shared compound client."""
    from cohezion.swarm.compound_client import get_compound_client

    # Use a module-level override if set, otherwise the compound singleton
    client = getattr(metrics_tokens, "_client", None)
    if client is None:
        client = get_compound_client()
    return TokenMetricsResponse(**client.get_metrics())


def set_token_client(client: Any) -> None:
    """Register a TokenEfficientClient for the /metrics/tokens endpoint.

    Pass ``None`` to revert to the default compound client singleton.
    """
    metrics_tokens._client = client  # type: ignore[attr-defined]


@metrics_router.get("/metrics/compound", response_model=CompoundMetricsResponse)
async def metrics_compound():
    """Return compound engineering metrics from retrospection analysis."""
    from cohezion.compound.metrics import get_collector
    from cohezion.core.compound.retrospection import RetrospectionEngine

    engine = RetrospectionEngine()
    learnings = engine.analyze_learnings()
    scores = engine.calculate_compound_scores()
    refinements = engine.suggest_skill_refinements()

    top_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]
    collector = get_collector()

    return CompoundMetricsResponse(
        total_learnings=len(learnings),
        top_compound_scores=[{"name": name, "score": score} for name, score in top_scores],
        suggested_refinements=[
            {
                "skill_name": r.skill_name,
                "reason": r.reason,
                "learning_count": len(r.suggested_additions),
            }
            for r in refinements
        ],
        total_executions=collector.total_executions,
    )
