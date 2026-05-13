"""
Analyst Agent - Feature extraction with configurable perspectives.

Uses Gemma 3 4B for multi-perspective analysis. Multiple instances
can run in parallel, each viewing the problem from a different angle.
"""

import logging
from datetime import datetime
from typing import Any

from cohezion.agents.base import BaseAgent
from cohezion.swarm.swarm_types import Perspective, SwarmConfig, ThoughtVector


logger = logging.getLogger(__name__)


# Perspective-specific system prompts
PERSPECTIVE_PROMPTS = {
    Perspective.TECHNICAL: """You are a technical analyst. Focus on:
- Implementation feasibility and technical constraints
- Algorithmic efficiency and system architecture
- Code quality, patterns, and best practices
- Performance implications and scalability
Provide concrete technical assessments with specifics.""",
    Perspective.ETHICAL: """You are an ethics analyst. Focus on:
- Potential societal impacts and consequences
- Fairness, bias, and inclusivity considerations
- Privacy and data sovereignty concerns
- Long-term implications for stakeholders
Provide measured ethical assessments with nuance.""",
    Perspective.HISTORICAL: """You are a historical analyst. Focus on:
- Precedents and similar past approaches
- Evolution of ideas and technologies over time
- Lessons learned from historical successes and failures
- Contextual understanding from prior work
Ground your analysis in documented history.""",
    Perspective.EMPIRICAL: """You are an empirical analyst. Focus on:
- Observable facts and measurable outcomes
- Scientific evidence and experimental data
- Quantifiable metrics and statistical validity
- Reproducibility and verification methods
Support claims with evidence and data.""",
    Perspective.METAPHYSICAL: """You are a metaphysical analyst. Focus on:
- Underlying principles and fundamental nature
- Abstract patterns and universal connections
- Conceptual frameworks and ontological implications
- Synthesis of seemingly disparate domains
Explore the deeper structure beneath surface phenomena.""",
}


class AnalystAgent(BaseAgent):
    """
    Gemma-based analyst for feature extraction and thought generation.

    Each analyst instance operates with a specific Perspective, allowing
    the swarm to examine problems from multiple angles in parallel.
    """

    def __init__(
        self,
        perspective: Perspective,
        config: SwarmConfig | None = None,
    ):
        config = config or SwarmConfig()
        super().__init__(
            model_name=config.analyst_model,
            config=config,
        )
        self.perspective = perspective
        self.system_prompt = PERSPECTIVE_PROMPTS.get(perspective, PERSPECTIVE_PROMPTS[Perspective.TECHNICAL])

    async def process(self, query: str, **kwargs: Any) -> ThoughtVector:
        """
        Analyze the query from this agent's perspective.

        Returns a ThoughtVector containing the analysis and metadata.
        """
        return await self.analyze(query)

    async def analyze(self, query: str, **kwargs: Any) -> ThoughtVector:
        """
        Perform perspective-specific analysis on the query.

        Args:
            query: The user's question or task description

        Returns:
            ThoughtVector with the analysis results
        """
        prompt = f"""Analyze the following query from your {self.perspective.value} perspective.
Provide a focused, insightful analysis in 2-3 paragraphs.

Query: {query}

Your {self.perspective.value} analysis:"""

        try:
            response = await self._call_ollama(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=0.7,
                max_tokens=1024,
                **kwargs,
            )

            return ThoughtVector(
                perspective=self.perspective,
                content=response.strip(),
                embedding=getattr(response, "embedding", None),
                persistence_id=getattr(response, "persistence_id", None),
                frequency_count=getattr(response, "frequency", 1),
                phi_score=getattr(response, "phi_score", 0.8),
                confidence=getattr(response, "confidence", 0.8),
                timestamp=datetime.now(),
                metadata={
                    "model": self.model_name,
                    "query_length": len(query),
                    "narration": getattr(response, "narration", None),
                },
            )

        except Exception as e:
            logger.error(f"Analyst ({self.perspective.value}) failed: {e}")
            return ThoughtVector(
                perspective=self.perspective,
                content=f"Analysis failed: {e!s}",
                confidence=0.0,
                timestamp=datetime.now(),
                metadata={"error": str(e)},
            )

    def __repr__(self) -> str:
        return f"AnalystAgent(perspective={self.perspective.value}, model={self.model_name})"
