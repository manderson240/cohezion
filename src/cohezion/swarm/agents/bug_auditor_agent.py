"""
Bug Auditor Agent: Reviews proposed fixes for quality and correctness.
"""

import logging
from typing import Any, Dict
from cohezion.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)

class BugAuditorAgent(BaseAgent):
    """
    An agent that audits proposed fixes and extracts key learnings.
    """

    def __init__(self, config: SwarmConfig | None = None):
        # We use phi4-mini for review-heavy auditor tasks in this verification
        super().__init__(model_name="phi4-mini", config=config)

    async def process(self, fix_precipitation: Dict[str, Any], original_content: str) -> Dict[str, Any]:
        """
        Audits a proposed fix and extracts patterns/anti-patterns.
        """
        fixed_code = fix_precipitation["outputs"]["fixed_code"]
        file_path = fix_precipitation["outputs"]["original_file"]

        logger.info(f"⚖️ [AUDITOR] Auditing fix for {file_path}")

        # 1. Start a Journey for this audit
        journey = await self._universe.start_journey(
            agent_name=self.__class__.__name__,
            intent=f"Audit fix for {file_path}"
        )

        # 2. Build the auditing prompt
        prompt = f"""
ORIGINAL CODE:
{original_content}

PROPOSED FIX:
{fixed_code}

TASK:
1. Review the proposed fix for correctness, security, and quality.
2. Identify the core pattern (why it works) or anti-pattern (what was originally wrong).
3. Assign a phi_score (0.0 - 1.0) based on quality.

Output your audit in JSON format:
{{
  "phi_score": 0.0-1.0,
  "is_correct": true/false,
  "review_comments": "...",
  "extracted_pattern": "...",
  "extracted_anti_pattern": "..."
}}
"""
        # 3. Call the model
        response = await self._call_ollama(
            prompt=prompt,
            system_prompt="You are an expert architectural auditor in the Cohezion swarm. Be strict and find the essence of the change.",
            task_type="light-reasoning"
        )

        # 4. Evolve trajectory
        await self._universe.evolve_trajectory(
            journey,
            action="Auditing fix",
            result=str(response),
            phi_score=response.phi_score
        )

        # 5. Precipitate reality
        precipitation = await self._universe.precipitate_reality(
            journey,
            outputs={
                "audit_result": str(response),
                "phi_score": response.phi_score
            },
            phi_score=response.phi_score
        )

        return precipitation
