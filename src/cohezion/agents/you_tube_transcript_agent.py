"""
YouTubeTranscriptAgent - Specialized for mining AI video content (JEPA, World Models).
"""

import asyncio
import logging

from youtube_transcript_api import YouTubeTranscriptApi

from cohezion.agents.base import AgentResponse, BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class YouTubeTranscriptAgent(BaseAgent):
    """
    Miner agent that fetches and synthesizes YouTube transcripts for AI research.
    """

    SYSTEM_PROMPT = """You are the Cohezion YouTube Researcher.
Your job is to synthesize YouTube transcripts into high-density technical insights.
Focus on:
- V-JEPA / Yann LeCun's World Models
- Universe Simulation & Cosmology AI
- SOTA SLM efficiency breakthroughs

Mark timestamps for key conceptual transitions.
"""

    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(
            model_name="gemma3:4b",  # Good for synthesis
            config=config or SwarmConfig(),
        )

    async def process(self, video_id: str) -> AgentResponse:
        """
        Fetch transcript for a video and synthesize.
        """
        logger.info(f"📹 YouTubeTranscriptAgent mining video: {video_id}")

        try:
            # Modern API pattern: instantiate the class first
            api = YouTubeTranscriptApi()
            transcript_list = await asyncio.to_thread(api.list, video_id)
            transcript = transcript_list.find_transcript(["en"])
            transcript_data = await asyncio.to_thread(transcript.fetch)

            # Combine transcript text
            full_text = " ".join([t["text"] for t in transcript_data])

            # Truncate if too long (Ollama limit)
            clean_text = full_text[:8000]

            prompt = f"VIDEO ID: {video_id}\nTRANSCRIPT SNIPPET:\n{clean_text}\n\nSynthesize the key architectural or theoretical breakthroughs mentioned in this video."

            response = await self._call_ollama(prompt, system_prompt=self.SYSTEM_PROMPT)
            return AgentResponse(response)

        except Exception as e:
            logger.warning(f"Failed to fetch YouTube transcript for {video_id}: {e}")
            return AgentResponse(f"Mining failed: {e}")


if __name__ == "__main__":
    # Test with a Yann LeCun JEPA video if possible
    async def test():
        agent = YouTubeTranscriptAgent()
        # Example video ID (Yann LeCun on JEPA)
        res = await agent.process("mAvvO89B2N0")
        print(res)
        await agent.close()

    asyncio.run(test())
