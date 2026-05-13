"""A2A Protocol Endpoints (Agent-to-Agent v1.0).

Implements Google's A2A protocol for multi-agent collaboration.
Reference: https://github.com/a2a-protocol/a2a

Extracted from api/__init__.py (Wave 2B of synthetic-sniffing-panda).
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, field_validator

from cohezion.mcp.manager.auth import validate_token
from cohezion.protocols.a2a_server import A2AServer, AgentCard


a2a_router = APIRouter(tags=["a2a"])


# Initialize A2A server (singleton at module level)
_a2a_server = A2AServer(
    agent_card=AgentCard(
        name="Cohezion Portfolio Agent",
        description=(
            "FLUME VAE latent space navigation, Compound Loop engineering,"
            " Universe Simulation, Swarm Orchestration, and Evaluation Infrastructure"
        ),
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


class A2AMessageModel(BaseModel):
    """A2A message format with size validation."""

    role: str
    parts: list[dict[str, Any]]

    @field_validator("parts")
    @classmethod
    def validate_parts_size(cls, parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Limit message parts to 1MB total to prevent DOS attacks."""
        import json

        # Estimate size by serializing to JSON
        serialized = json.dumps(parts)
        size_bytes = len(serialized.encode("utf-8"))
        max_size = 1_048_576  # 1 MB

        if size_bytes > max_size:
            raise ValueError(f"Message parts exceed maximum size of {max_size} bytes (got {size_bytes} bytes)")

        return parts


class A2ASendTaskRequest(BaseModel):
    """Request body for POST /tasks/send."""

    message: A2AMessageModel
    task_id: str | None = None


@a2a_router.get("/.well-known/agent.json")
async def get_agent_card():
    """A2A Protocol: Agent discovery endpoint."""
    return _a2a_server.get_agent_card()


@a2a_router.post("/tasks/send")
async def send_a2a_task(request: A2ASendTaskRequest, api_key: str = Depends(verify_a2a_token)):
    """A2A Protocol: Task submission endpoint."""
    # Validate message has content
    if not request.message.parts:
        raise HTTPException(status_code=400, detail="Message parts cannot be empty")

    # Route through A2A server
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


@a2a_router.get("/tasks/{task_id}")
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


@a2a_router.post("/tasks/{task_id}/cancel")
async def cancel_a2a_task(task_id: str, api_key: str = Depends(verify_a2a_token)):
    """A2A Protocol: Task cancellation endpoint."""
    success = await _a2a_server.cancel_task(task_id)

    # Check if task exists
    task = await _a2a_server.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return {"canceled": success, "state": task.state}
