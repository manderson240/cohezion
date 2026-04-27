"""Skill execution + capability-query routes.

Extracted from api/__init__.py (Wave 2B of synthetic-sniffing-panda).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


logger = logging.getLogger(__name__)

skills_router = APIRouter(tags=["skills"])


class SkillExecuteRequest(BaseModel):
    input_text: str
    config: dict[str, Any] = {}


class PlanStepOut(BaseModel):
    step_index: int
    operation: str
    description: str
    output: str
    tokens_used: int
    duration_ms: float


class SkillExecuteResponse(BaseModel):
    skill_name: str
    agent_class: str
    result: str
    status: str
    plan_steps: list[PlanStepOut] | None = None
    total_tokens: int | None = None
    total_duration_ms: float | None = None


class CapabilityQueryRequest(BaseModel):
    query: str
    top_k: int = 5


class CapabilityQueryResponse(BaseModel):
    agents: list[dict[str, Any]]
    query: str


@skills_router.post("/skills/{skill_name}/execute", response_model=SkillExecuteResponse)
async def execute_skill(skill_name: str, request: SkillExecuteRequest):
    """Parse skill, expand instructions into a plan, and execute via PlanExecutor."""
    from cohezion.agents.factory import AgentFactory
    from cohezion.core.instruction_expander import InstructionExpander
    from cohezion.core.plan_executor import PlanExecutor
    from cohezion.swarm.compound_client import get_compound_client

    factory = AgentFactory()
    try:
        spec = factory._resolve_spec(skill_name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_name}") from None

    class_name = f"{spec.name}Agent"

    # Expand instructions into a plan and execute
    try:
        expander = InstructionExpander()
        plan = expander.expand(spec)
        compound = get_compound_client()
        executor = PlanExecutor(token_client=compound)
        exec_result = await executor.execute(plan, request.input_text)

        step_outputs = [
            PlanStepOut(
                step_index=sr.step_index,
                operation=sr.operation,
                description=plan.steps[sr.step_index].description,
                output=sr.output,
                tokens_used=sr.tokens_used,
                duration_ms=sr.duration_ms,
            )
            for sr in exec_result.steps
        ]

        return SkillExecuteResponse(
            skill_name=skill_name,
            agent_class=class_name,
            result=exec_result.final_output,
            status="executed",
            plan_steps=step_outputs,
            total_tokens=exec_result.total_tokens,
            total_duration_ms=exec_result.total_duration_ms,
        )
    except Exception as exc:
        # Skill execution can raise anything from user-supplied agent code;
        # report as structured error response rather than letting the request 500.
        logger.exception("Skill execution failed: %s", skill_name)
        return SkillExecuteResponse(
            skill_name=skill_name,
            agent_class=class_name,
            result=str(exc),
            status="error",
        )


@skills_router.post("/query/find-capable-agent", response_model=CapabilityQueryResponse)
async def find_capable_agent(request: CapabilityQueryRequest):
    """Use CapabilityRegistry to find best agents for a query."""
    from cohezion.registry.capability_registry import CapabilityRegistry

    registry = CapabilityRegistry()
    results = registry.find(request.query, top_k=request.top_k)
    return CapabilityQueryResponse(
        query=request.query,
        agents=[
            {
                "name": cap.name,
                "type": cap.type,
                "description": cap.description,
                "score": round(cap.score, 4),
                "path": cap.path,
            }
            for cap in results
        ],
    )


@skills_router.get("/skills/list")
async def list_prime_skills():
    """List all available PRIME skills."""
    from cohezion.agents.factory import AgentFactory

    factory = AgentFactory()
    names = factory.list_available_skills()
    return {"count": len(names), "skills": names}
