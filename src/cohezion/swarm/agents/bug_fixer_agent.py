"""
Bug Fixer Agent: Generates concrete code fixes for confirmed bugs.
"""

import logging
from typing import Any

from cohezion.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class BugFixerAgent(BaseAgent):
    """
    An agent that generates fixes for confirmed bugs.
    """

    def __init__(self, config: SwarmConfig | None = None):
        # We use phi4-mini for coding-heavy fixer tasks in this verification
        super().__init__(model_name="phi4-mini", config=config)

    async def process(
        self, bug_analysis: dict[str, Any], file_content: str
    ) -> dict[str, Any]:
        """
        Generates a fix for a confirmed bug.
        """
        issue = bug_analysis["outputs"]["issue"]
        analysis = bug_analysis["outputs"]["analysis"]

        logger.info(f"🛠️ [FIXER] Fixing bug in {issue['file_path']}:{issue['line']}")

        # 1. Start a Journey for this fix
        journey = await self._universe.start_journey(
            agent_name=self.__class__.__name__,
            intent=f"Fix bug: {issue['message']} at {issue['file_path']}:{issue['line']}",
        )

        # 2. Build the fixing prompt
        prompt = f"""
BUG ANALYSIS:
File: {issue["file_path"]}
Line: {issue["line"]}
Issue: {issue["message"]}
Analysis: {analysis}

ORIGINAL CODE:
{file_content}

TASK:
Generate a concrete fix for this bug. 
Follow Cohezion coding standards:
- Python >= 3.11
- Black formatting
- Type hints
- NumPy-style docstrings
- Use circuit breakers (from cohezion.reliability) for external calls if applicable.

Output ONLY the corrected code for the entire file.
"""
        # 3. Call the model
        response = await self._call_ollama(
            prompt=prompt,
            system_prompt="You are an expert software engineer in the Cohezion swarm. Write high-quality, production-ready code.",
            task_type="light-coding",
        )

        # 4. Evolve trajectory
        await self._universe.evolve_trajectory(
            journey,
            action="Generating fix",
            result="Code generated",
            phi_score=response.phi_score,
        )

        # 5. Precipitate reality
        precipitation = await self._universe.precipitate_reality(
            journey,
            outputs={"fixed_code": str(response), "original_file": issue["file_path"]},
            phi_score=response.phi_score,
        )

        return precipitation
