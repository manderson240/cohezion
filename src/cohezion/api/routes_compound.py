"""Compound engineering endpoints - execute, feedback, health, history."""

import logging

from fastapi import APIRouter, HTTPException

from cohezion.api.models import (
    CompoundExecuteRequest,
    CompoundExecuteResponse,
    CompoundFeedbackRequest,
    CompoundFeedbackResponse,
    CompoundHealthResponse,
    CompoundHistoryResponse,
    CompoundStepOut,
)
from cohezion.security.utils import sanitize_error_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compound", tags=["compound"])


@router.post("/execute", response_model=CompoundExecuteResponse)
async def compound_execute(request: CompoundExecuteRequest):
    """Execute a PRIME skill with live Ollama models via CompoundExecutor."""
    from cohezion.compound.executor import get_executor  # type: ignore[attr-defined]

    executor = get_executor()  # type: ignore[reportAttributeAccessIssue]
    try:
        result = await executor.execute_skill(  # type: ignore[reportUnknownMemberType]
            request.skill_name,
            request.input_text,
            model=request.model,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"Skill not found: {request.skill_name}"
        ) from exc
    except Exception as exc:
        logger.exception("Compound execution failed: %s", request.skill_name)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

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


@router.post("/feedback", response_model=CompoundFeedbackResponse)
async def compound_feedback(request: CompoundFeedbackRequest):
    """Run a compound feedback cycle: execute -> analyze -> refine."""
    from cohezion.compound.feedback_loop import CompoundFeedbackLoop

    loop = CompoundFeedbackLoop()  # type: ignore[reportCallIssue]
    try:
        if request.cycles > 1:
            report = await loop.run_multi_cycle(  # type: ignore[reportAttributeAccessIssue]
                request.skill_name,
                request.input_text,
                cycles=request.cycles,
                model=request.model,
            )
            return CompoundFeedbackResponse(
                skill_name=report.skill_name,  # type: ignore[reportUnknownMemberType]
                cycles_completed=report.total_cycles,  # type: ignore[reportUnknownMemberType]
                total_tokens=report.total_tokens,  # type: ignore[reportUnknownMemberType]
                total_duration_ms=report.total_duration_ms,  # type: ignore[reportUnknownMemberType]
                total_refinements=report.total_refinements,  # type: ignore[reportUnknownMemberType]
                compound_score_delta=report.final_compound_score_delta,  # type: ignore[reportUnknownMemberType]
            )
        else:
            result = await loop.run_cycle(  # type: ignore[reportAttributeAccessIssue]
                request.skill_name,
                request.input_text,
                model=request.model,
            )
            return CompoundFeedbackResponse(
                skill_name=result.skill_name,  # type: ignore[reportUnknownMemberType]
                cycles_completed=1,
                total_tokens=result.execution_tokens,  # type: ignore[reportUnknownMemberType]
                total_duration_ms=result.execution_duration_ms,  # type: ignore[reportUnknownMemberType]
                total_refinements=result.refinements_applied,  # type: ignore[reportUnknownMemberType]
                compound_score_delta=result.compound_score_delta,  # type: ignore[reportUnknownMemberType]
                patterns=result.patterns,  # type: ignore[reportUnknownMemberType]
            )
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"Skill not found: {request.skill_name}"
        ) from exc
    except Exception as exc:
        logger.exception("Compound feedback failed: %s", request.skill_name)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/health", response_model=CompoundHealthResponse)
async def compound_health():
    """Return compound system health from the metrics collector."""
    from cohezion.compound.metrics import get_collector

    collector = get_collector()
    return CompoundHealthResponse(**collector.to_health_dict())


@router.get("/history/{skill_name}", response_model=CompoundHistoryResponse)
async def compound_history(skill_name: str):
    """Return compound execution history for a specific skill."""
    from cohezion.compound.metrics import get_collector

    collector = get_collector()
    history = collector.get_skill_history(skill_name)  # type: ignore[reportAttributeAccessIssue]
    return CompoundHistoryResponse(skill_name=skill_name, executions=history)
