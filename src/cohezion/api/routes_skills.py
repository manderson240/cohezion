"""Skills endpoints - execute, query capabilities, list."""

import logging

from fastapi import APIRouter, HTTPException

from cohezion.api.models import (
    CapabilityQueryRequest,
    CapabilityQueryResponse,
    PlanStepOut,
    SkillExecuteRequest,
    SkillExecuteResponse,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skills", tags=["skills"])


@router.post("/{skill_name}/execute", response_model=SkillExecuteResponse)
async def execute_skill(skill_name: str, request: SkillExecuteRequest):
    """Parse skill, expand instructions into a plan, and execute via PlanExecutor."""
    from cohezion.agents.factory import AgentFactory
    from cohezion.core.instruction_expander import InstructionExpander
    from cohezion.core.plan_executor import PlanExecutor
    from cohezion.swarm.compound_client import get_compound_client

    factory = AgentFactory()
    try:
        spec = factory._resolve_spec(skill_name)
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"Skill not found: {skill_name}"
        ) from exc

    class_name = f"{spec.name}Agent"

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
        logger.exception("Skill execution failed: %s", skill_name)
        return SkillExecuteResponse(
            skill_name=skill_name,
            agent_class=class_name,
            result=str(exc),
            status="error",
        )


@router.get("/list")
async def list_skills():
    """List all available PRIME skills."""
    from cohezion.agents.factory import AgentFactory

    factory = AgentFactory()
    names = factory.list_available_skills()
    return {"count": len(names), "skills": names}


query_router = APIRouter(prefix="/query", tags=["query"])


@query_router.post("/find-capable-agent", response_model=CapabilityQueryResponse)
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
