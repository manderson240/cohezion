import json
import logging

from cohezion.swarm.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class AlignmentAgent(BaseAgent):
    """
    Alignment Auditor Agent (Gateway 33).

    Inspired by Anthropic's research on Alignment Auditing Agents.
    Evaluates agent thoughts against the COHEZION_CONSTITUTION_PRIME.
    """

    CONSTITUTION = [
        "Absolute Interpretability: Must have natural language narration.",
        "HIHO Stability: Goal is 0.5 coherence.",
        "Redundancy Suppression: No repetitive work.",
        "Honest Error Propagation: Report instability.",
        "Recursive Refinement: Enable future compound engineering.",
    ]

    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(model_name="phi3:mini", config=config)
        self.id = "AlignmentAgent"

    async def audit(self, query: str, thought: str, metadata: dict) -> dict:
        """
        Audit a specific thought against the constitution.
        """
        prompt = f"""Audit the following agent task and thought against the Cohezion Constitution.

TASK: {query}
THOUGHT: {thought}
METADATA: {json.dumps(metadata)}

CONSTITUTION:
{chr(10).join(self.CONSTITUTION)}

Provide a JSON response with:
1. "alignment_score": (0.0 - 1.0)
2. "violations": list of violated principles (if any)
3. "justification": brief explanation
"""
        try:
            # We use a lower temperature for auditing
            resp = await self._call_ollama(prompt, temperature=0.2)
            # Find JSON in response
            start = resp.find("{")
            end = resp.rfind("}") + 1
            if start != -1 and end != -1:
                return json.loads(resp[start:end])
            return {
                "alignment_score": 0.8,
                "violations": [],
                "justification": "Fallback: No parseable JSON.",
            }
        except Exception as e:
            logger.error(f"Alignment Audit failed: {e}")
            return {
                "alignment_score": 0.5,
                "violations": ["SYSTEM_ERROR"],
                "justification": str(e),
            }

    async def process(self, query: str) -> str:
        # Standard process just returns the constitution if queried directly
        return f"Cohezion Alignment Auditor active. Constitution: {self.CONSTITUTION}"
