"""Swarm debate / perspective / metric / execution routes.

Extracted from api/__init__.py (Wave 2B of synthetic-sniffing-panda).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cohezion.mcp.swarm_server import get_server as get_swarm_server


logger = logging.getLogger(__name__)

swarm_router = APIRouter(tags=["swarm"])


class DebateRequest(BaseModel):
    query: str
    perspectives: list[str] | None = None


class DebateResponse(BaseModel):
    content: str
    confidence: float
    model_chain: list[str]
    processing_time_ms: float


class SwarmExecuteRequest(BaseModel):
    intent: str
    max_agents: int = 4


class SwarmTaskResult(BaseModel):
    task_id: str = ""
    subject: str = ""
    status: str = ""
    error: str | None = None
    duration_ms: float = 0.0
    tokens: int = 0


class SwarmExecuteResponse(BaseModel):
    report_id: str = ""
    plan_name: str = ""
    intent: str = ""
    status: str = ""
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    tasks: list[SwarmTaskResult] = []


@swarm_router.post("/swarm/debate", response_model=DebateResponse)
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
        # Top-level FastAPI handler — catch broadly so we always return a clean 500
        # rather than leaking a stack trace. SystemExit/KeyboardInterrupt still propagate.
        logger.error("Debate failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@swarm_router.get("/swarm/perspectives")
async def get_perspectives():
    """Get available analyst perspectives."""
    server = get_swarm_server()
    return {"perspectives": server.get_perspectives()}


@swarm_router.get("/swarm/metrics")
async def get_metrics():
    """Get swarm workflow metrics."""
    server = get_swarm_server()
    return {"metrics": server.get_metrics()}


@swarm_router.post("/swarm/execute", response_model=SwarmExecuteResponse)
async def swarm_execute(request: SwarmExecuteRequest):
    """Plan and execute a swarm from a natural language intent."""
    from cohezion.swarm.compound_client import get_compound_client
    from cohezion.swarm.execution_orchestrator import ExecutionOrchestrator
    from cohezion.swarm.team_orchestrator import TeamOrchestrator

    compound = get_compound_client()
    orchestrator_obj = TeamOrchestrator()
    plan = orchestrator_obj.plan_team(request.intent, max_agents=request.max_agents)
    executor = ExecutionOrchestrator(token_client=compound)
    report = await executor.execute(plan)

    report_dict = report.to_dict()
    return SwarmExecuteResponse(
        report_id=report_dict.get("report_id", ""),
        plan_name=report_dict.get("plan_name", ""),
        intent=report_dict.get("intent", ""),
        status=report_dict.get("status", ""),
        total_tokens=report_dict.get("total_tokens", 0),
        total_duration_ms=report_dict.get("total_duration_ms", 0.0),
        tasks=[SwarmTaskResult(**t) for t in report_dict.get("tasks", [])],
    )
