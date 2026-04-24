"""Template parsing routes (PRIME skill -> structured spec + generated code).

Extracted from api/__init__.py (Wave 2B of synthetic-sniffing-panda).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


logger = logging.getLogger(__name__)

templates_router = APIRouter(tags=["templates"])


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


@templates_router.post("/templates/parse", response_model=TemplateParseResponse)
async def parse_template(request: TemplateParseRequest):
    """Parse a PRIME skill definition and return structured spec + generated code."""
    from cohezion.core.config_templates import ConfigTemplateManager

    manager = ConfigTemplateManager()

    try:
        spec = manager.engine.get_spec_by_name(request.skill_name)
    except (KeyError, ValueError, OSError, AttributeError, RuntimeError, UnicodeDecodeError, TypeError) as e:
        logger.error("Template parse failed for %s: %s", request.skill_name, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Template parsing failed") from e

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
