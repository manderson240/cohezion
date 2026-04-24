"""Compound execution + feedback + health/history routes.

Extracted from api/__init__.py (Wave 2B of synthetic-sniffing-panda).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


logger = logging.getLogger(__name__)

compound_router = APIRouter(tags=["compound"])


class CompoundExecuteRequest(BaseModel):
    skill_name: str
    input_text: str
    model: str | None = None


class CompoundStepOut(BaseModel):
    step_index: int
    operation: str
    description: str
    output: str
    tokens_used: int
    duration_ms: float
    model: str = ""


class CompoundExecuteResponse(BaseModel):
    skill_name: str
    final_output: str
    steps: list[CompoundStepOut] = []
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    model_usage: dict[str, int] = {}


class CompoundFeedbackRequest(BaseModel):
    skill_name: str
    input_text: str
    model: str | None = None
    cycles: int = 1


class CompoundFeedbackResponse(BaseModel):
    skill_name: str
    cycles_completed: int = 0
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    total_refinements: int = 0
    compound_score_delta: float = 0.0
    patterns: list[str] = []


class CompoundHealthResponse(BaseModel):
    total_executions: int = 0
    total_refinements: int = 0
    total_cycles: int = 0
    success_rate: float = 0.0
    total_tokens: int = 0
    model_usage: dict[str, int] = {}
    top_refined_skills: list[dict[str, Any]] = []
    compound_score_trend: list[dict[str, Any]] = []


class CompoundHistoryResponse(BaseModel):
    skill_name: str
    executions: int = 0
    refinements: int = 0
    cycles: int = 0
    total_tokens: int = 0
    success_rate: float = 0.0
    latest_execution: float | None = None
    latest_refinement: float | None = None


@compound_router.post("/compound/execute", response_model=CompoundExecuteResponse)
async def compound_execute(request: CompoundExecuteRequest):
    """Execute a PRIME skill with live Ollama models via CompoundExecutor."""
    from cohezion.compound.executor import get_executor

    executor = get_executor()
    try:
        result = await executor.execute_skill(
            request.skill_name,
            request.input_text,
            model=request.model,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"Skill not found: {request.skill_name}"
        ) from exc
    except Exception as exc:
        # FastAPI endpoint — convert any executor failure to clean 500 with logged detail.
        logger.exception("Compound execution failed: %s", request.skill_name)
        raise HTTPException(status_code=500, detail="Execution failed") from exc

    return CompoundExecuteResponse(
        skill_name=result.skill_name,
        final_output=result.final_output,
        steps=[
            CompoundStepOut(
                step_index=s["step_index"],
                operation=s["operation"],
                description=s["description"],
                output=s["output"],
                tokens_used=s["tokens_used"],
                duration_ms=s["duration_ms"],
                model=s.get("model", ""),
            )
            for s in result.steps
        ],
        total_tokens=result.total_tokens,
        total_duration_ms=result.total_duration_ms,
        model_usage=result.model_usage,
    )


@compound_router.post("/compound/feedback", response_model=CompoundFeedbackResponse)
async def compound_feedback(request: CompoundFeedbackRequest):
    """Run a compound feedback cycle: execute -> analyze -> refine."""
    from cohezion.compound.feedback_loop import CompoundFeedbackLoop

    loop = CompoundFeedbackLoop()
    try:
        if request.cycles > 1:
            report = await loop.run_multi_cycle(
                request.skill_name,
                request.input_text,
                cycles=request.cycles,
                model=request.model,
            )
            return CompoundFeedbackResponse(
                skill_name=report.skill_name,
                cycles_completed=report.total_cycles,
                total_tokens=report.total_tokens,
                total_duration_ms=report.total_duration_ms,
                total_refinements=report.total_refinements,
                compound_score_delta=report.final_compound_score_delta,
            )
        else:
            result = await loop.run_cycle(
                request.skill_name,
                request.input_text,
                model=request.model,
            )
            return CompoundFeedbackResponse(
                skill_name=result.skill_name,
                cycles_completed=1,
                total_tokens=result.execution_tokens,
                total_duration_ms=result.execution_duration_ms,
                total_refinements=result.refinements_applied,
                compound_score_delta=result.compound_score_delta,
                patterns=result.patterns,
            )
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"Skill not found: {request.skill_name}"
        ) from exc
    except Exception as exc:
        # FastAPI endpoint — convert any feedback-loop failure to clean 500 with logged detail.
        logger.exception("Compound feedback failed: %s", request.skill_name)
        raise HTTPException(status_code=500, detail="Feedback cycle failed") from exc


@compound_router.get("/compound/health", response_model=CompoundHealthResponse)
async def compound_health():
    """Return compound system health from the metrics collector."""
    from cohezion.compound.metrics import get_collector

    collector = get_collector()
    return CompoundHealthResponse(**collector.to_health_dict())


@compound_router.get(
    "/compound/history/{skill_name}",
    response_model=CompoundHistoryResponse,
)
async def compound_history(skill_name: str):
    """Return compound execution history for a specific skill."""
    from cohezion.compound.metrics import get_collector

    collector = get_collector()
    history = collector.skill_history(skill_name)
    return CompoundHistoryResponse(**history)
