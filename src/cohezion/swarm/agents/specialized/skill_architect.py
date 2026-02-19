"""Skill Architect Agent for autonomous skill evolution."""

import logging
import os
from pathlib import Path
from typing import Any

from cohezion.core.mcp_client import get_mcp_client
from cohezion.core.routing.router import LOCAL_ROUTER

logger = logging.getLogger(__name__)


class SkillArchitectAgent:
    """
    Agent responsible for synthesizing disconnected learnings into unified PRIME skills.
    """

    def __init__(self, skills_dir: str = "src/cohezion/skills"):
        self.skills_dir = Path(skills_dir)
        self.local_router: Any = None  # Will be lazy loaded
        self.mcp = get_mcp_client()

    async def evolve_skills(self) -> list[str]:
        """
        Scan vault learnings and evolve existing skills.
        """
        updated_skills = []
        try:
            # 1. List all learnings in the vault
            # learnings/project/skill/time.md
            learnings = self.mcp.vault_list("learnings/")
            
            # 2. Group by "skill" name (directory level)
            groups = {}
            for item in learnings:
                # expecting: project/skill/time.md
                parts = item.split("/")
                if len(parts) >= 2:
                    skill_name = parts[1]
                    if skill_name not in groups:
                        groups[skill_name] = []
                    groups[skill_name].append(item)

            # 3. Process each group
            for skill_name, learning_paths in groups.items():
                logger.info(f"Evolving skill '{skill_name}' with {len(learning_paths)} learnings.")
                
                # Fetch contents of all learnings
                contents = []
                for lp in learning_paths:
                    try:
                        c = self.mcp.vault_read(f"learnings/{lp}")
                        contents.append(c)
                    except Exception as e:
                        logger.warning(f"Failed to read learning {lp}: {e}")

                if not contents:
                    continue

                # 4. Synthesize into PRIME format
                synthesis = await self._synthesize_skill(skill_name, contents)
                
                # 5. Write to local skills directory
                skill_file = self.skills_dir / f"{skill_name.lower()}_prime.md"
                # Ensure directory exists
                skill_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(skill_file, "w") as f:
                    f.write(synthesis)
                
                updated_skills.append(str(skill_file))
                logger.info(f"Skill evolved and saved to: {skill_file}")

        except Exception as e:
            logger.error(f"Failed to evolve skills: {e}")
            
        return updated_skills

    async def _synthesize_skill(self, skill_name: str, learnings: list[str]) -> str:
        """
        Use local SLM to synthesize learnings into a PRIME skill.
        """
        learnings_text = "\n\n---\n\n".join(learnings)
        
        prompt = f"""Synthesize the following disconnected learnings into a single, comprehensive PRIME skill for '{skill_name}'.
Follow the standard SKILL_PRIME format exactly.

FORMAT:
# SKILL: {skill_name.upper()}_PRIME

## DOMAIN EXPERTISE
[High-level definition]

## KEY TEXTS & CONCEPTS
- [Concept 1]
- [Concept 2]

## INSTRUCTION
1. [Step 1]
2. [Step 2]

## VERSION
v1.0 (Synthesized)

## SEE ALSO
- [Related Skills]

LEARNINGS TO SYNTHESIZE:
{learnings_text}
"""
        try:
            synthesis = await LOCAL_ROUTER.route_task(
                task_type="reasoning", 
                prompt=prompt
            )
            return synthesis
        except Exception as e:
            logger.error(f"Synthesis failed for {skill_name}: {e}")
            return f"# SKILL: {skill_name.upper()}_PRIME\n\nERROR: Synthesis failed."

def get_skill_architect() -> SkillArchitectAgent:
    return SkillArchitectAgent()
