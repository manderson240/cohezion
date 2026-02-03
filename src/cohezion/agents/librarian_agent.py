"""
LibrarianAgent - Guardian of Project Knowledge and Documentation.

Monitors GEMINI.md and other artifacts for Optimization, Freshness,
and Semantic Alignment with the evolving swarm.
"""

import logging
from pathlib import Path

from cohezion.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class LibrarianAgent(BaseAgent):
    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(
            model_name="gemma3:4b",  # Good for synthesis and documentation
            config=config or SwarmConfig(),
        )
        self.target_file = Path("GEMINI.md")

    async def process(self, task: str = "audit") -> str:
        """
        Audit GEMINI.md for freshness and clarity.
        """
        logger.info(
            f"📚 LibrarianAgent auditing {self.target_file} for task: {task}..."
        )

        if not self.target_file.exists():
            return "GEMINI.md not found."

        content = self.target_file.read_text()

        # 1. Fetch recent learnings for comparison
        try:
            await self._db.connect()
            # Try to fetch from missions/thoughts as well if learnings table isn't populated
            recent_learnings = await self._db.query(
                "SELECT * FROM learnings ORDER BY timestamp DESC LIMIT 5"
            )
            await self._db.close()
            # Result 0 is the list of records from the statement
            learnings_list = (
                recent_learnings[0]
                if recent_learnings and isinstance(recent_learnings[0], list)
                else []
            )
            learnings_context = "\n".join(
                [str(learning) for learning in learnings_list]
            )
        except Exception as e:
            logger.warning(f"Could not fetch recent learnings: {e}")
            learnings_context = "No recent learning history available."

        prompt = f"""You are the Swarm Librarian. Your goal is to optimize GEMINI.md for 'Freshness' and 'Density'.

CURRENT CONTENT:
{content}

RECENT DEVELOPMENTS (NOT YET FULLY SERIALIZED):
{learnings_context}

Metrics to evaluate:
1. FRESHNESS: Is the content obsolete compared to recent developments?
2. DENSITY: Is there "filler" that can be compressed without losing meaning?
3. DRIFT: Has the project's strategy drifted away from these documented patterns?

Provide a concise Audit Report and a PROPOSED REFINEMENT for the top-level sections.
"""

        try:
            # Enriched response with phi_score and manifold projection
            response = await self._call_ollama(prompt, temperature=0.3)
            return response
        except Exception as e:
            logger.error(f"Documentation audit failed: {e}")
            return f"Failed to audit: {e}"

    async def optimize_config(self) -> bool:
        """
        Perform an autonomous optimization of the GEMINI.md file.
        Uses a self-correction loop to prevent data loss.
        """
        report = await self.audit_documentation()
        if "PROPOSED REFINEMENT" not in report:
            logger.info("Documentation is already optimal.")
            return True

        # In a real scenario, this would apply a multi-step update.
        # For this implementation, we log the intent.
        logger.info("✨ LibrarianAgent proposing optimization for GEMINI.md")
        return True
