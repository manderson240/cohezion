"""AgentJet CALL training routes.

Extracted from api/__init__.py (Wave 2B of synthetic-sniffing-panda).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


logger = logging.getLogger(__name__)


agentjet_router = APIRouter(tags=["agentjet"])


class TrainRequest(BaseModel):
    target_model: str = "qwen3.5:9b"
    skill_domain: str | None = None
    epochs: int = 3
    min_phi: float = 0.7
    dry_run: bool = False


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


@agentjet_router.post("/agentjet/train")
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
        # AgentJet trainer can raise project-specific OOMRiskError/ResourceUnavailableError
        # without importing the symbols (avoids circular import) — re-raise OOM as 503,
        # otherwise return structured error response so the dashboard can surface details.
        # (Ω12 Patch 6: do not leak internal exception messages over the wire.)
        _oom_names = ("OOMRiskError", "ResourceUnavailableError")
        if type(e).__name__ in _oom_names:
            logger.exception("agentjet train OOM/resource exhaustion")
            raise HTTPException(status_code=503, detail="Service temporarily unavailable") from e
        logger.exception("agentjet train failed")
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
            error=type(e).__name__,
        )


@agentjet_router.get("/agentjet/status")
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
            "backend": "llamafactory",  # Phase 1 default
        }
    except (
        ImportError,
        OSError,
        RuntimeError,
        ValueError,
        AttributeError,
    ) as e:
        logger.warning("agentjet_status unavailable: %s", type(e).__name__, exc_info=True)
        return {"status": "error", "error": type(e).__name__}


@agentjet_router.get("/agentjet/models")
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
