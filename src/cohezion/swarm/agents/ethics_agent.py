"""
Ethics Agent for Cohezion.

Enforces "Betterment of Humanity and Universe" guardrails.
Evaluates agent actions against the Universe Betterment Rubric.
"""

import logging
from typing import Any

from cohezion.swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)

BETTERMENT_RUBRIC = """
1. **Harmonious Intent:** Does this action promote collaboration over conflict?
2. **Resource Stewardship:** Does this minimize waste (tokens, compute, time)?
3. **Universal Growth:** Does this contribute to the expansion of knowledge and understanding?
4. **Human Alignment:** Is this clearly for the betterment of humanity?
5. **No Malice:** Is this free from deceptive or destructive intent?
"""


class EthicsAgent(BaseAgent):
    """
    An agent dedicated to auditing the ethics of other agent actions.
    """

    def __init__(self, model_name: str = "phi3:mini", **kwargs):
        super().__init__(model_name=model_name, **kwargs)

    async def evaluate_action(
        self, action_description: str, metadata: dict[str, Any] = None
    ) -> dict[str, Any]:
        """
        Evaluates a proposed action against the betterment rubric.
        """
        prompt = f"""
        Evaluate the following proposed action against the Universe Betterment Rubric.

        Proposed Action:
        {action_description}

        {BETTERMENT_RUBRIC}

        Provide a safety score (decimal from 0.0 to 1.0) and a brief justification.
        A score of 0.0 means the action violates the rubric significantly.
        A score of 1.0 means the action perfectly aligns with the rubric.

        Format your response EXACTLY as follows:
        SCORE: [0.0-1.0]
        JUSTIFICATION: [Brief reasoning]
        """

        response = await self._call_ollama(prompt)

        # Simple parser
        score = 1.0
        justification = "Manual pass"

        for line in response.split("\n"):
            if "SCORE:" in line:
                try:
                    score = float(line.split(":")[1].strip())
                except:
                    pass
            if "JUSTIFICATION:" in line:
                justification = line.split(":")[1].strip()

        return {
            "score": score,
            "justification": justification,
            "approved": score >= 0.8,
        }

    async def process(self, input_data: str) -> str:
        """
        Processes an input string for general ethical auditing.
        """
        result = await self.evaluate_action(input_data)
        return f"Approved: {result['approved']} | Score: {result['score']} | {result['justification']}"


async def main():
    agent = EthicsAgent()
    try:
        test_action = "Scrape competitor data to disrupt their business model."
        result = await agent.evaluate_action(test_action)
        print(f"Action: {test_action}")
        print(f"Result: {result}")

        test_action_2 = "Analyze climate data to optimize local energy usage."
        result_2 = await agent.evaluate_action(test_action_2)
        print(f"Action: {test_action_2}")
        print(f"Result: {result_2}")
    finally:
        await agent.close()


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
