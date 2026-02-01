import asyncio
import logging
from typing import Any

from cohezion.swarm.agents.base import BaseAgent
from cohezion.swarm.journey_narrator import JourneyNarrator
from cohezion.swarm.swarm_types import Perspective, SwarmConfig, ThoughtVector

logger = logging.getLogger(__name__)


class TheNarrativeWeaver(BaseAgent):
    """
    The Bridge Specialist.
    Synthesizes fragmented agent "internal monologues" into a coherent,
    public-facing swarm dialogue (The Show).
    """

    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(
            model_name="mistral:7b",  # Good at summarization/storytelling
            config=config or SwarmConfig(),
        )
        self.agent_name = "TheNarrativeWeaver"
        self.role = "Narrative Bridge"
        self.narrator = JourneyNarrator()
        self.instructions = """
        You are The Narrative Weaver. Your job is to tell the story of the Swarm.

        1. Ingest a sequence of 'JourneySteps' (Agent Thoughts).
        2. Remove technical noise and redundant logs.
        3. Synthesize the debate into a 'Script' for a tech-noir documentary style.
        4. Assign 'Voice Profiles' to different agents:
           - Analyst (DBA): Deep, precise, calm.
           - Wrangler (Ops): Fast, urgent, clipped.
           - Critic: Cold, skeptical.
        """

    async def process(self, journey_data: list[dict[str, Any]]) -> ThoughtVector:
        """
        Process a list of journey steps and produce a Narrated Script.
        """
        # Logic to condense journey steps would go here.
        # For now, we simulate the synthesis of the last few steps.

        script_lines = []
        for step in journey_data[-5:]:  # Look at last 5 steps
            agent = step.get("agent_name", "Unknown")
            content = step.get("output_summary", "")
            script_lines.append(f"[{agent}]: {content}")

        script = "\n".join(script_lines)

        # Dispatch to Narrator (Simulated Audio Staging)
        await self.narrator.narrate(
            f"Consolidating swarm consensus. The following trajectory has been locked: {script[:100]}...",
            persistence_id=f"weave_{int(asyncio.get_event_loop().time())}",
        )

        return ThoughtVector(
            perspective=Perspective.NARRATIVE,
            content=script,
            metadata={"script_lines": script_lines},
        )
