import logging
from typing import Any

from cohezion.flume.autoencoder import FlumeConfig, FlumeEncoder
from cohezion.swarm.agents.alignment_agent import AlignmentAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class ScalarContextManager:
    """
    Manages RLM context using a scalar importance heuristic.
    Allows for "compressed" context in shallow recursion and "deep" context in high-relevance areas.
    """

    def __init__(self, threshold: float = 0.6, config: SwarmConfig | None = None):
        self.threshold = threshold
        self.config = config or SwarmConfig()
        self._encoder = FlumeEncoder(FlumeConfig())
        self._summarizer_agent: AlignmentAgent | None = None

    def calculate_importance(
        self, text_segment: str, query: str, stability: float = 0.0
    ) -> float:
        """
        Assigns a scalar importance score (0.0-1.0) using vector similarity
        and optional stability weighting.
        """
        # 1. Vector Similarity
        similarity = self._encoder.similarity(query, text_segment)

        # 2. 12D Stability Boost
        # Breakthroughs (stability > 0.9) amplify the relevance of associated text.
        boost = 0.0
        if stability > 0.9:
            boost = (stability - 0.9) * 2.0  # Max boost of 0.2 at stability=1.0

        score = similarity + boost
        return min(max(score, 0.0), 1.0)

    async def recursive_summarize(self, segment: str, context_hint: str) -> str:
        """
        Summarizes a low-importance segment using an SLM to preserve
        compressed semantic value.
        """
        if self._summarizer_agent is None:
            # Using phi3:mini for efficient background summarization
            from dataclasses import replace

            sync_config = replace(self.config, mrp_sync=False)

            self._summarizer_agent = AlignmentAgent(config=sync_config)
            self._summarizer_agent.model_name = "phi3:mini"

        prompt = f"""Summarize this context segment for an RLM analysis.
Preserve key technical terms and 12D implications.
HINT: {context_hint}
SEGMENT: {segment}
SUMMARY:"""

        summary = await self._summarizer_agent._call_ollama(prompt, temperature=0.1)
        return summary

    async def prioritize_context(
        self, segments: list[str], query: str, stability: float = 0.0
    ) -> list[dict[str, Any]]:
        """
        Returns segments with associated scalars and automated summaries for low-score items.
        """
        prioritized = []
        for seg in segments:
            scalar = self.calculate_importance(seg, query, stability)

            action = "DIVE" if scalar >= self.threshold else "SUMMARIZE"
            content = seg

            if action == "SUMMARIZE":
                logger.info(
                    f"📍 Summarizing low-importance segment (scalar: {scalar:.2f})"
                )
                content = await self.recursive_summarize(seg, query)

            prioritized.append(
                {
                    "content": content,
                    "original_length": len(seg),
                    "summary_length": len(content),
                    "importance_scalar": scalar,
                    "action": action,
                }
            )
        return prioritized

    async def close(self):
        if self._summarizer_agent:
            await self._summarizer_agent.close()


def get_scalar_context_manager() -> ScalarContextManager:
    return ScalarContextManager()
