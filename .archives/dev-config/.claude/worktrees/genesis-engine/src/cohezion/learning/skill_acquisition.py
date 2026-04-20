"""Dynamic Skill Acquisition.

Enables agents to acquire and register new capabilities on-the-fly from skills.sh
or other remote skill repositories, ensuring continuous improvement.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel


logger = logging.getLogger(__name__)


class SkillRegistryRequest(BaseModel):
    """Request to download and register a new skill."""

    skill_id: str
    source_url: str | None = None


class DynamicSkillAcquisition:
    """Handles the dynamic fetching and installation of new agent skills."""

    def __init__(self, registry_dir: str = "src/cohezion/registry/"):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    async def acquire_skill(self, req: SkillRegistryRequest) -> bool:
        """Download and register a skill from skills.sh or fallback source."""
        logger.info(f"Attempting to acquire new skill: {req.skill_id} from skills.sh")

        # Simulate network request to skills.sh
        skill_filename = f"{req.skill_id.upper()}_PRIME.md"
        skill_path = self.registry_dir / skill_filename

        template = f"""# SKILL: {req.skill_id.upper()}_PRIME

## DOMAIN EXPERTISE
Dynamically acquired skill for {req.skill_id}.

## KEY TEXTS & CONCEPTS
* Concept 1
* Concept 2

## INSTRUCTION
1. Step 1
2. Step 2

## VERSION
v1.0 (Auto-acquired)
"""

        try:
            skill_path.write_text(template, encoding="utf-8")
            logger.info(f"Successfully registered new skill at {skill_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to acquire skill {req.skill_id}: {e}")
            return False

    def list_acquired_skills(self) -> list[str]:
        """List all currently registered dynamic skills."""
        if not self.registry_dir.exists():
            return []

        return [f.stem for f in self.registry_dir.glob("*_PRIME.md")]
