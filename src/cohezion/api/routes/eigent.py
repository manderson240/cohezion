"""
Eigent API - Workforce orchestration and task breakdown.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from cohezion.swarm.agents.eigent_agent import EigentAgent


router = APIRouter(prefix="/eigent", tags=["eigent"])
logger = logging.getLogger(__name__)

# Cache for active agents
_agents = {}


class WorkforceRequest(BaseModel):
    task: str
    role: str = "System Architect"
    duration_days: int = 7


class WorkforceResponse(BaseModel):
    agent_id: str
    status: str
    message: str


async def run_long_horizon_task(agent_id: str, task: str, days: int):
    """
    Background worker for long-running autonomous tasks.
    """
    try:
        agent = _agents[agent_id]
        logger.info(f"Starting long-running task {agent_id} for {days} days: {task}")

        # Placeholder for loop: would use SurrealDB to check state
        # For simulation, we run for a short time or simulate intervals
        # Real implementation would use systemd or a persistent scheduler
        await agent.run_journey(task, days)

    except Exception as e:
        logger.error(f"Error in long-horizon task {agent_id}: {e}")


@router.post("/workforce", response_model=WorkforceResponse)
async def create_workforce(request: WorkforceRequest, background_tasks: BackgroundTasks):
    """
    Activate a specialized workforce for a specific task.
    """
    try:
        agent_id = f"eigent-{request.role.lower().replace(' ', '-')}"

        if agent_id not in _agents:
            _agents[agent_id] = EigentAgent(role=request.role)

        # Add the long-running task to background processing
        background_tasks.add_task(run_long_horizon_task, agent_id, request.task, request.duration_days)

        return WorkforceResponse(
            agent_id=agent_id,
            status="active",
            message=f"Agent '{request.role}' activated for {request.duration_days} days.",
        )
    except Exception as e:
        logger.error(f"Failed to create workforce: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{agent_id}")
async def get_workforce_status(agent_id: str):
    """
    Check the status of an active workforce.
    """
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {"agent_id": agent_id, "status": "active", "last_checkpoint": "Not implemented"}
