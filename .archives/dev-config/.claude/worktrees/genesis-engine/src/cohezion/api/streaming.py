"""SSE streaming endpoints for long-running inference.

Enables real-time progress monitoring for multi-hour inference tasks
with checkpoint support and graceful cancellation.
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from cohezion.compound.session_manager import (
    SessionConfig,
    close_session,
    create_session,
    get_session,
    list_sessions,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/inference", tags=["streaming"])


class StreamingInferenceRequest(BaseModel):
    """Request to start streaming inference."""

    skill_name: str
    input_text: str
    model: str | None = None
    checkpoint_interval: int = 5
    max_duration_sec: float = 7200.0


class SessionListResponse(BaseModel):
    """Response with active sessions."""

    sessions: list[str]


@router.post("/stream")
async def stream_inference(request: StreamingInferenceRequest):
    """Start long-running inference with SSE streaming.

    Returns Server-Sent Events stream with progress updates:
    - start: Session initialized
    - resume: Resumed from checkpoint
    - step: Execution step completed
    - checkpoint: Checkpoint created
    - complete: Execution finished
    - error: Error occurred
    - cancelled: Cancelled by user
    - timeout: Max duration exceeded

    Args:
        request: StreamingInferenceRequest with skill_name, input_text, etc.

    Returns:
        StreamingResponse with SSE events
    """
    try:
        # Create session
        config = SessionConfig(
            checkpoint_interval_steps=request.checkpoint_interval,
            max_session_duration_sec=request.max_duration_sec,
        )
        session = create_session(config=config)

        # Define execution function (placeholder)
        async def execute_step(step_index: int, state: Any):
            """Execute a single step."""
            # TODO: Wire to actual skill execution with TokenEfficientClient
            # For now, return mock output
            output = f"Step {step_index} result"
            metrics = {"tokens": 50, "model": request.model or "default"}
            return output, metrics

        # Create event generator
        async def event_generator():
            async for event in session.execute_with_checkpoints(
                request.skill_name,
                request.input_text,
                execute_step,
            ):
                yield f"data: {json.dumps(event)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"X-Session-ID": session.session_id},
        )

    except Exception as e:
        logger.exception("Stream inference failed")
        raise HTTPException(status_code=500, detail=f"Streaming inference failed: {e!s}") from e


@router.post("/resume/{session_id}")
async def resume_session(session_id: str):
    """Resume inference from checkpoint.

    Args:
        session_id: Session ID to resume

    Returns:
        StreamingResponse with progress from checkpoint
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Return same streaming response as /stream
    async def event_generator():
        async def execute_step(step_index: int, state: Any):
            output = f"Step {step_index} result"
            metrics = {"tokens": 50}
            return output, metrics

        async for event in session.execute_with_checkpoints(
            "resumed_skill",
            "resumed_input",
            execute_step,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"X-Session-ID": session_id},
    )


@router.delete("/cancel/{session_id}")
async def cancel_session(session_id: str):
    """Request graceful session cancellation.

    Args:
        session_id: Session ID to cancel

    Returns:
        {"message": "Cancellation requested"}

    Raises:
        HTTPException: If session not found
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    session.cancel()
    return {"message": f"Cancellation requested for {session_id}"}


@router.get("/sessions")
async def list_active_sessions() -> SessionListResponse:
    """List all active sessions.

    Returns:
        SessionListResponse with session IDs
    """
    sessions = list_sessions()
    return SessionListResponse(sessions=sessions)


@router.get("/status/{session_id}")
async def get_session_status(session_id: str):
    """Get session status.

    Args:
        session_id: Session ID

    Returns:
        {"session_id": str, "active": bool, "state": dict | None}

    Raises:
        HTTPException: If session not found
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    state = None
    if session.state:
        state = {
            "current_step": session.state.current_step,
            "total_steps": session.state.total_steps,
            "intermediate_results_count": len(session.state.intermediate_results),
            "model_usage": session.state.model_usage,
        }

    return {
        "session_id": session_id,
        "active": not session.is_cancelled(),
        "state": state,
    }


@router.post("/close/{session_id}")
async def close_session_endpoint(session_id: str):
    """Close and clean up session.

    Args:
        session_id: Session ID to close

    Returns:
        {"message": "Session closed"}

    Raises:
        HTTPException: If session not found
    """
    if not close_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return {"message": f"Session {session_id} closed"}
