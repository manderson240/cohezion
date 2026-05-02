"""
PRIME Skill Service - Logic for parsing and matching PRIME skills.
"""

import logging

from fastapi import HTTPException
from pydantic import BaseModel


logger = logging.getLogger(__name__)

# --- Models ---


class TemplateParseRequest(BaseModel):
    skill_name: str


class TemplateParseResponse(BaseModel):
    name: str
    domain_expertise: str
    concepts: dict[str, str]
    instructions: list[str]
    version: str
    see_also: list[str]
    agent_stub: str
    config_class: str


# --- Service Logic ---


async def parse_template_service(
    request: TemplateParseRequest,
) -> TemplateParseResponse:
    """Parse a PRIME skill definition and return structured spec."""
    from cohezion.core.config_templates import ConfigTemplateManager

    manager = ConfigTemplateManager()

    try:
        spec = manager.engine.get_spec_by_name(request.skill_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    if spec is None:
        raise HTTPException(
            status_code=404,
            detail=f"Skill not found: {request.skill_name}",
        )

    return TemplateParseResponse(
        name=spec.name,
        domain_expertise=spec.domain_expertise,
        concepts=spec.concepts,
        instructions=spec.instructions,
        version=spec.version,
        see_also=spec.see_also,
        agent_stub=manager.engine.generate_agent_stub(spec),
        config_class=manager.engine.generate_config_class(spec),
    )
