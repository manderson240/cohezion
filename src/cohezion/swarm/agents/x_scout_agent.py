"""
XScoutAgent - Monitors high-signal researcher feeds on X (Twitter).
"""

import asyncio
import logging
import os

from cohezion.swarm.agents.base import AgentResponse, BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class XScoutAgent(BaseAgent):
    """
    Agent that "scouts" X for researcher updates.
    Notes: In this environment, we simulate or use a mock if API keys aren't present.
    """

    SYSTEM_PROMPT = """You are the Cohezion X-Scout.
Extract the 'alpha' from short-form researcher updates.
Look for mentions of Paper IDs, Repo links, or disruptive theoretical claims (JEPA, Manifolds).
"""

    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(
            model_name="phi3:mini",  # Fast classification/extraction
            config=config or SwarmConfig(),
        )
        # Auth would go here, using mock for now unless env vars exist
        self.api_key = os.getenv("X_API_KEY")

    async def process(self, username: str = "ylecun") -> AgentResponse:
        """
        Scout recent tweets from a user.
        """
        logger.info(f"🐦 XScoutAgent scouting: @{username}")

        # Simulated data for Yann LeCun / World Models focus
        simulated_tweets = [
            "JEPA is the future of autonomous machine intelligence. No more generative hallucinations.",
            "Our new V-JEPA model shows remarkable efficiency in learning world models from raw video.",
            "The path to AGI is through world models, not just predicting tokens.",
        ]

        prompt = f"USER: @{username}\nRECENT UPDATES:\n" + "\n".join(simulated_tweets)
        prompt += "\n\nIdentify any specific architectural claims and assign a Cohezion Relevance Score (0-1)."

        response = await self._call_ollama(prompt, system_prompt=self.SYSTEM_PROMPT)
        return AgentResponse(response)


if __name__ == "__main__":
    asyncio.run(XScoutAgent().process())
