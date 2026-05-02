"""API endpoints for ResearchAgent.

Exposes autonomous research capabilities via REST API.
Integrates with existing Cohezion API infrastructure.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from cohezion.research import (
    MultiAgentResearchConfig,
    ResearchAgent,
    ResearchConfig,
    ResearchSwarm,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])


# Request/Response models
class ResearchConfigRequest(BaseModel):
    """Research configuration request."""

    experiment_time_budget: float = Field(default=300.0, ge=60.0, le=3600.0)
    max_experiments: int = Field(default=100, ge=1, le=1000)
    target_metric: str = Field(default="val_bpb")
    model_depth: int = Field(default=8, ge=1, le=32)
    vocab_size: int = Field(default=8192, ge=256, le=65536)
    enable_guardrails: bool = Field(default=True)


class MultiAgentConfigRequest(BaseModel):
    """Multi-agent research configuration."""

    num_agents: int = Field(default=3, ge=1, le=10)
    experiments_per_agent: int = Field(default=33, ge=1, le=100)
    agent_diversity: str = Field(default="high")


class ResearchResponse(BaseModel):
    """Research session response."""

    session_id: str
    status: str
    experiments_completed: int
    best_metric: float | None
    experiments_remaining: int


class ResearchResultResponse(BaseModel):
    """Research result details."""

    session_id: str
    experiments_completed: int
    best_metric: float | None
    checkpoint_path: str | None
    agent_breakdown: dict[str, Any] | None
    collaboration_insights: list[str]


def _sanitize_metric(value: float | None) -> float | None:
    """Return None for non-finite floats (inf, -inf, nan) to keep JSON valid."""
    if value is None or not math.isfinite(value):
        return None
    return value


def _sanitize_json(obj: Any) -> Any:
    """Recursively replace non-finite floats with None for JSON compliance."""
    if isinstance(obj, float):
        return None if not math.isfinite(obj) else obj
    if isinstance(obj, dict):
        return {k: _sanitize_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_json(item) for item in obj]
    return obj


# Active sessions storage (in production: use Redis/SurrealDB)
_MAX_SESSIONS = 50
_active_sessions: dict[str, ResearchAgent] = {}
_active_swarm_sessions: dict[str, ResearchSwarm] = {}


@router.post("/start", response_model=ResearchResponse)
async def start_research(
    config: ResearchConfigRequest,
    background_tasks: BackgroundTasks,
):
    """Start autonomous research session.

    Launches research agent to optimize training configuration.
    """
    try:
        if len(_active_sessions) + len(_active_swarm_sessions) >= _MAX_SESSIONS:
            raise HTTPException(status_code=429, detail="Too many active sessions")

        research_config = ResearchConfig(
            experiment_time_budget=config.experiment_time_budget,
            max_experiments=config.max_experiments,
            target_metric=config.target_metric,
            model_depth=config.model_depth,
            vocab_size=config.vocab_size,
            enable_guardrails=config.enable_guardrails,
        )

        agent = ResearchAgent(config=research_config)
        session_id = agent.session.session_id

        # Store session
        _active_sessions[session_id] = agent

        # Start in background
        background_tasks.add_task(agent.run_session)

        logger.info(f"Started research session: {session_id}")

        return ResearchResponse(
            session_id=session_id,
            status="running",
            experiments_completed=0,
            best_metric=None,
            experiments_remaining=config.max_experiments,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start research: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/start-multi-agent", response_model=ResearchResponse)
async def start_multi_agent_research(
    config: MultiAgentConfigRequest,
    background_tasks: BackgroundTasks,
):
    """Start multi-agent research session.

    Coordinates multiple agents with different strategies.
    """
    try:
        multi_config = MultiAgentResearchConfig(
            num_agents=config.num_agents,
            experiments_per_agent=config.experiments_per_agent,
            agent_diversity=config.agent_diversity,
        )

        swarm = ResearchSwarm(config=multi_config)
        session_id = f"swarm-{datetime.now().isoformat()}"

        # Store session
        _active_swarm_sessions[session_id] = swarm

        # Start in background - FastAPI handles async tasks automatically
        background_tasks.add_task(swarm.run_multi_agent_research)

        logger.info(f"Started multi-agent research: {session_id}")

        return ResearchResponse(
            session_id=session_id,
            status="running",
            experiments_completed=0,
            best_metric=None,
            experiments_remaining=config.num_agents * config.experiments_per_agent,
        )

    except Exception as e:
        logger.error(f"Failed to start multi-agent research: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/status/{session_id}", response_model=ResearchResponse)
async def get_research_status(session_id: str):
    """Get research session status."""
    # Check single agent session
    if session_id in _active_sessions:
        agent = _active_sessions[session_id]

        return ResearchResponse(
            session_id=session_id,
            status="running" if agent.session.active else "completed",
            experiments_completed=agent.session.experiments_completed,
            best_metric=_sanitize_metric(agent.session.best_metric),
            experiments_remaining=agent.config.max_experiments - agent.session.experiments_completed,
        )

    # Check multi-agent session
    if session_id in _active_swarm_sessions:
        swarm = _active_swarm_sessions[session_id]

        return ResearchResponse(
            session_id=session_id,
            status="running",  # Simplified
            experiments_completed=swarm.results.experiments_completed,
            best_metric=_sanitize_metric(swarm.results.best_metric),
            experiments_remaining=0,  # Would calculate
        )

    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/results/{session_id}", response_model=ResearchResultResponse)
async def get_research_results(session_id: str):
    """Get research session results."""
    # Check single agent session
    if session_id in _active_sessions:
        agent = _active_sessions[session_id]
        best = agent.get_best_result()

        return ResearchResultResponse(
            session_id=session_id,
            experiments_completed=agent.session.experiments_completed,
            best_metric=best["metric"] if best else None,
            checkpoint_path=best.get("checkpoint") if best else None,
            agent_breakdown=None,
            collaboration_insights=[],
        )

    # Check multi-agent session
    if session_id in _active_swarm_sessions:
        swarm = _active_swarm_sessions[session_id]
        report = swarm.get_collaboration_report()

        return ResearchResultResponse(
            session_id=session_id,
            experiments_completed=report["total_experiments"],
            best_metric=_sanitize_metric(report.get("best_metric")),
            checkpoint_path=None,
            agent_breakdown=report["agent_breakdown"],
            collaboration_insights=report["insights"],
        )

    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/stop/{session_id}")
async def stop_research(session_id: str):
    """Stop research session gracefully."""
    if session_id in _active_sessions:
        agent = _active_sessions.pop(session_id)
        agent.stop()

        logger.info(f"Stopped research session: {session_id}")
        return {"status": "stopped", "session_id": session_id}

    if session_id in _active_swarm_sessions:
        # Swarm doesn't have explicit stop yet
        del _active_swarm_sessions[session_id]

        logger.info(f"Stopped multi-agent session: {session_id}")
        return {"status": "stopped", "session_id": session_id}

    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/experiments/{session_id}")
async def get_experiment_log(session_id: str, limit: int = Query(default=100, ge=1, le=10000)):
    """Get experiment log for a session."""
    if session_id not in _active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    agent = _active_sessions[session_id]

    try:
        # Read experiment log
        log_path = agent.config.experiment_log

        if not log_path.exists():
            return {"experiments": []}

        experiments = []
        with open(log_path) as f:
            for line in f:
                if len(experiments) >= limit:
                    break
                try:
                    exp = json.loads(line)
                    experiments.append(_sanitize_json(exp))
                except json.JSONDecodeError:
                    continue

        return {"experiments": experiments}

    except Exception as e:
        logger.error(f"Failed to read experiment log: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/dashboard")
async def get_research_dashboard():
    """Get research dashboard overview."""
    active_count = len(_active_sessions) + len(_active_swarm_sessions)

    return {
        "active_sessions": active_count,
        "single_agent_sessions": len(_active_sessions),
        "multi_agent_sessions": len(_active_swarm_sessions),
        "timestamp": datetime.now().isoformat(),
    }
