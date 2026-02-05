"""
Bug Scout Agent: Identifies functional bugs from static analysis hotspots.
"""

import logging
from typing import Any, Dict, List
from cohezion.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig
from cohezion.healing.deep_audit import CodeIssue

logger = logging.getLogger(__name__)

class BugScoutAgent(BaseAgent):
    """
    An agent that scouts for bugs by inspecting potential code issues.
    It look inward to the codebase and outward to verify functional impact.
    """

    def __init__(self, config: SwarmConfig | None = None):
        # We use phi4-mini for reasoning-heavy scout tasks in this verification
        super().__init__(model_name="phi4-mini", config=config)

    async def process(self, issue: CodeIssue, file_content: str) -> Dict[str, Any]:
        """
        Inspects a specific code issue and confirms if it's a functional bug.
        """
        logger.info(f"🔍 [SCOUT] Inspecting issue in {issue.file_path}:{issue.line}")

        # 1. Start a Journey for this scout task
        journey = await self._universe.start_journey(
            agent_name=self.__class__.__name__,
            intent=f"Verify bug: {issue.message} at {issue.file_path}:{issue.line}"
        )

        # 2. Build the scouting prompt
        prompt = f"""
ISSUE IDENTIFIED BY STATIC ANALYSIS:
File: {issue.file_path}
Line: {issue.line}
Severity: {issue.severity}
Category: {issue.category}
Message: {issue.message}

CODE CONTEXT (around line {issue.line}):
{file_content}

TASK:
Analyze the code and the static analysis warning. 
Determine if this is a real functional bug, a performance bottleneck, or a false positive.
If it is a bug, explain the impact and provide reproduction steps (if applicable).

Output your analysis in the following JSON format:
{{
  "is_bug": true/false,
  "confidence": 0.0-1.0,
  "impact_analysis": "...",
  "reproduction_steps": "...",
  "suggested_priority": "Low/Medium/High/Critical"
}}
"""
        # 3. Call the model
        response = await self._call_ollama(
            prompt=prompt,
            system_prompt="You are an expert bug hunter in the Cohezion swarm. Be precise and critical.",
            task_type="light-reasoning"
        )

        # 4. Evolve trajectory
        await self._universe.evolve_trajectory(
            journey,
            action="Scouting code issue",
            result=str(response),
            phi_score=response.phi_score
        )

        # 5. Precipitate reality
        precipitation = await self._universe.precipitate_reality(
            journey,
            outputs={
                "issue": vars(issue),
                "analysis": str(response)
            },
            phi_score=response.phi_score
        )

        return precipitation
