"""
Synthesizer Agent - Aggregation and final response generation.

Uses Mistral 7B for its larger context window and strong
rhetorical capabilities to weave disparate threads into coherence.
"""

import logging
import time
from typing import Any

from cohezion.agents.base import BaseAgent
from cohezion.swarm.swarm_types import CritiqueResult, SwarmConfig, SynthesizedResponse


logger = logging.getLogger(__name__)


SYNTHESIZER_SYSTEM_PROMPT = """You are a master synthesizer. Your role is to:

1. INTEGRATE: Weave multiple perspectives into a coherent whole
2. RESOLVE: Address contradictions identified by the critic
3. BALANCE: Give appropriate weight to each perspective based on relevance
4. CLARIFY: Produce a clear, actionable response

Your output should be:
- Comprehensive yet concise
- Well-structured with clear sections
- Actionable where appropriate
- Honest about remaining uncertainties

Do not simply concatenate perspectives. Create genuine synthesis."""


class SynthesizerAgent(BaseAgent):
    """
    Mistral-based synthesizer for final response generation.

    Takes the analyst outputs and critic's review, then produces
    a coherent, unified response that resolves contradictions.
    """

    def __init__(self, config: SwarmConfig | None = None):
        config = config or SwarmConfig()
        super().__init__(
            model_name=config.synthesizer_model,
            config=config,
        )

    async def process(self, critique: CritiqueResult, **kwargs: Any) -> SynthesizedResponse:
        """Process critique result and return synthesized response."""
        return await self.synthesize(critique, original_query=kwargs.get("original_query", ""))

    async def synthesize(
        self,
        critique: CritiqueResult,
        original_query: str = "",
    ) -> SynthesizedResponse:
        """
        Synthesize analyst outputs into a coherent final response.

        Args:
            critique: The CritiqueResult containing analyst outputs and issues
            original_query: The original user query for context

        Returns:
            SynthesizedResponse with the unified answer
        """
        start_time = time.perf_counter()

        # Build context from analyst outputs
        perspectives = self._format_perspectives(critique)
        issues = self._format_issues(critique)

        prompt = f"""Original Query: {original_query}

{perspectives}

{issues}

CRITIC'S RECOMMENDATION: {critique.recommendation}

Based on the above analysis, provide a synthesized response that:
1. Addresses the original query comprehensively
2. Integrates insights from all perspectives
3. Resolves any contradictions
4. Notes any remaining uncertainties

SYNTHESIZED RESPONSE:"""

        try:
            response = await self._call_ollama(
                prompt=prompt,
                system_prompt=SYNTHESIZER_SYSTEM_PROMPT,
                temperature=0.5,
                max_tokens=2048,
            )

            processing_time = (time.perf_counter() - start_time) * 1000

            # Build model chain for traceability
            model_chain = []
            for output in critique.analyst_outputs:
                if output.metadata.get("model"):
                    model_chain.append(output.metadata["model"])
            model_chain.append(self.model_name)  # Add synthesizer

            return SynthesizedResponse(
                content=response.strip(),
                source_critique=critique,
                resolution_notes=self._generate_resolution_notes(critique),
                confidence=critique.overall_coherence,
                processing_time_ms=processing_time,
                model_chain=list(dict.fromkeys(model_chain)),  # Dedupe
            )

        except Exception as e:
            logger.error(f"Synthesizer failed: {e}")
            return SynthesizedResponse(
                content=f"Synthesis failed: {e!s}",
                source_critique=critique,
                confidence=0.0,
                processing_time_ms=(time.perf_counter() - start_time) * 1000,
                model_chain=[self.model_name],
            )

    @staticmethod
    def _format_perspectives(critique: CritiqueResult) -> str:
        """Format analyst perspectives for the prompt."""
        sections = ["## ANALYST PERSPECTIVES"]
        for output in critique.analyst_outputs:
            sections.append(
                (
                    f"\n### {output.perspective.value.upper()} (confidence: "
                    f"{output.confidence:.0%})\n{output.content}"
                )
            )
        return "\n".join(sections)

    @staticmethod
    def _format_issues(critique: CritiqueResult) -> str:
        """Format identified issues for the prompt."""
        if not critique.has_issues:
            return "## CRITIC'S REVIEW\nNo major contradictions or issues detected."

        sections = ["## CRITIC'S REVIEW"]

        if critique.contradictions:
            sections.append("\n### Contradictions:")
            for c in critique.contradictions:
                sections.append(f"- {c.description} (severity: {c.severity:.0%})")

        if critique.logical_issues:
            sections.append("\n### Logical Issues:")
            for issue in critique.logical_issues:
                sections.append(f"- {issue}")

        sections.append(f"\nOverall coherence: {critique.overall_coherence:.0%}")

        return "\n".join(sections)

    @staticmethod
    def _generate_resolution_notes(critique: CritiqueResult) -> list[str]:
        """Generate notes about how contradictions were resolved."""
        notes = []

        if not critique.has_issues:
            notes.append("All perspectives were coherent; no resolution needed.")
            return notes

        for c in critique.contradictions:
            if c.suggested_resolution:
                notes.append(f"Resolved: {c.suggested_resolution}")
            else:
                notes.append(f"Addressed contradiction: {c.description[:100]}...")

        return notes

    def __repr__(self) -> str:
        return f"SynthesizerAgent(model={self.model_name})"
