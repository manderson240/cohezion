"""
SkillDistiller Agent - Autonomous Skill Extraction from repetitive tasks.

Monitors SurrealDB for REPETITIVE_TASK_DETECTED events and distills them
into reusable PRIME skills.
"""

import logging
from pathlib import Path
from typing import Any

from cohezion.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)

SKILL_TEMPLATE = """# SKILL: {name}_PRIME

## DOMAIN EXPERTISE
{expertise}

## KEY CONCEPTS
{concepts}

## INSTRUCTION
{instruction}

## VERSION
v0.1
"""


class SkillDistiller(BaseAgent):
    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(
            model_name="gemma3:4b",  # Precise extraction model
            config=config or SwarmConfig(),
        )
        self.skills_dir = Path("src/cohezion/skills")
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    async def process(self, query_hash: str) -> str:
        """
        Distill a repetitive task into a new skill.

        Args:
            query_hash: Hash of the repetitive task to analyze.
        """
        logger.info(f"🔮 Distilling repetitive task {query_hash} into a new skill...")

        # 1. Fetch task details from SurrealDB
        try:
            await self._db.connect()
            result = await self._db.query(
                "SELECT content FROM agent_thought WHERE metadata.query_hash = $hash LIMIT 5",
                {"hash": query_hash},
            )
            await self._db.close()

            if not result or len(result) == 0:
                return "No task history found for distillation."

            contexts = [r["content"] for r in result]
            joined_context = "\n---\n".join(contexts)

        except Exception as e:
            logger.error(f"Failed to fetch context for distillation: {e}")
            return f"Error: {e}"

        # 2. Use LLM to distill skill components
        prompt = f"""You are a Meta-Architect. Analyze the following task outputs and distill them into a formal Cohezion Skill (PRIME format).

TASK OUTPUTS:
{joined_context}

Provide the following in JSON format:
{{
  "name": "UPPERCASE_NAME",
  "expertise": "Single paragraph defining domain expertise",
  "concepts": ["bullet 1", "bullet 2"],
  "instruction": "Numbered steps for implementation"
}}
"""
        try:
            response = await self._call_ollama(prompt, temperature=0.3)
            # Basic JSON extraction (naive)
            skill_data = self._parse_json(response)

            # 3. Write to file
            skill_content = SKILL_TEMPLATE.format(**skill_data)
            file_path = self.skills_dir / f"{skill_data['name']}_PRIME.md"
            file_path.write_text(skill_content)

            logger.info(f"✅ New skill distilled: {file_path}")
            return f"Successfully distilled skill: {skill_data['name']}"

        except Exception as e:
            logger.error(f"Distillation failed: {e}")
            return f"Failed to distill skill: {e}"

    def _parse_json(self, text: str) -> dict[str, Any]:
        """Simple helper to extract JSON from markdown/text."""
        import json
        import re

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("No JSON found in response")

    async def run_audit(self):
        """Scan for repetitive tasks and distill them autonomously."""
        try:
            await self._db.connect()
            # Find hashes with >= 5 occurrences
            result = await self._db.query(
                "SELECT metadata.query_hash as hash, count() as count FROM agent_thought GROUP BY hash HAVING count >= 5"
            )
            await self._db.close()

            for row in result:
                hash_val = row["hash"]
                # Check if skill already exists (naive check)
                await self.process(hash_val)

        except Exception as e:
            logger.error(f"Autonomous audit failed: {e}")
