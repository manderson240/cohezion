"""
Critic Agent - Logic verification and contradiction detection.

Uses Phi-3-Mini for its strong reasoning capabilities despite small size.
Reviews analyst outputs to find contradictions and logical issues.
"""

import logging
from typing import Any

from cohezion.agents.base import BaseAgent
from cohezion.swarm.swarm_types import (
    Contradiction,
    CritiqueResult,
    SwarmConfig,
    ThoughtVector,
)


logger = logging.getLogger(__name__)


CRITIC_SYSTEM_PROMPT = """You are a logical critic and truth auditor. Your role is to:

1. DETECT CONTRADICTIONS: Identify when analyst perspectives conflict with each other
2. CHECK LOGIC: Find logical fallacies, unsupported claims, or circular reasoning
3. ASSESS COHERENCE: Rate how well the perspectives complement each other
4. SUGGEST RESOLUTION: Propose how contradictions might be resolved

Be precise and specific. Quote exact phrases when identifying issues.
Format your response as structured analysis with clear sections."""


class CriticAgent(BaseAgent):
    """
    Phi-3 based critic for logic verification.

    Reviews multiple analyst outputs, detects contradictions,
    and assesses overall coherence of the collective analysis.
    """

    def __init__(self, config: SwarmConfig | None = None):
        config = config or SwarmConfig()
        super().__init__(
            model_name=config.critic_model,
            config=config,
        )

    async def process(self, analyst_outputs: list[ThoughtVector], **kwargs: Any) -> CritiqueResult:
        """Process analyst outputs and return critique."""
        return await self.critique(analyst_outputs)

    async def critique(self, analyst_outputs: list[ThoughtVector]) -> CritiqueResult:
        """
        Review analyst outputs for contradictions and logical issues.

        Args:
            analyst_outputs: List of ThoughtVectors from analyst agents

        Returns:
            CritiqueResult with detected issues and coherence score
        """
        if not analyst_outputs:
            return CritiqueResult(
                analyst_outputs=[],
                overall_coherence=0.0,
                recommendation="No analyst outputs to critique.",
            )

        # Format analyst outputs for review
        formatted_outputs = self._format_outputs(analyst_outputs)

        prompt = f"""Review the following analyst perspectives and identify any contradictions
or logical issues.

{formatted_outputs}

Provide your critique in the following format:

CONTRADICTIONS:
- List any contradictions between perspectives (quote specific phrases)

LOGICAL ISSUES:
- List any fallacies or unsupported claims

COHERENCE SCORE: [0-100]
- Brief justification for the score

RECOMMENDATION:
- How should these perspectives be synthesized?"""

        try:
            response = await self._call_ollama(
                prompt=prompt,
                system_prompt=CRITIC_SYSTEM_PROMPT,
                temperature=0.3,  # Lower temperature for analytical task
                max_tokens=1500,
            )

            return self._parse_critique(response, analyst_outputs)

        except Exception as e:
            logger.error(f"Critic failed: {e}")
            return CritiqueResult(
                analyst_outputs=analyst_outputs,
                overall_coherence=0.5,
                recommendation=f"Critique failed: {e!s}",
            )

    def _format_outputs(self, outputs: list[ThoughtVector]) -> str:
        """Format analyst outputs for the prompt."""
        sections = []
        for i, output in enumerate(outputs, 1):
            sections.append(
                f"## Perspective {i}: {output.perspective.value.upper()}\n{output.content}\n"
            )
        return "\n".join(sections)

    def _parse_critique(
        self, response: str, analyst_outputs: list[ThoughtVector]
    ) -> CritiqueResult:
        """Parse the critic's response into structured CritiqueResult."""
        contradictions: list[Contradiction] = []
        logical_issues: list[str] = []
        coherence = 0.5
        recommendation = ""

        lines = response.split("\n")
        current_section = None

        for line in lines:
            line_lower = line.lower().strip()

            # Detect section headers
            if "contradiction" in line_lower:
                current_section = "contradictions"
            elif "logical" in line_lower and "issue" in line_lower:
                current_section = "logical"
            elif "coherence" in line_lower and "score" in line_lower:
                current_section = "coherence"
                # Try to extract score
                import re

                score_match = re.search(r"(\d+)", line)
                if score_match:
                    coherence = int(score_match.group(1)) / 100.0
            elif "recommendation" in line_lower:
                current_section = "recommendation"
            elif line.startswith("-") or line.startswith("•"):
                content = line.lstrip("-•").strip()
                if content:
                    if current_section == "contradictions":
                        # Create a contradiction entry
                        if len(analyst_outputs) >= 2:
                            contradictions.append(
                                Contradiction(
                                    source_perspectives=(
                                        analyst_outputs[0].perspective,
                                        analyst_outputs[-1].perspective,
                                    ),
                                    description=content,
                                    severity=0.5,
                                )
                            )
                    elif current_section == "logical":
                        logical_issues.append(content)
                    elif current_section == "recommendation":
                        recommendation += content + " "

        return CritiqueResult(
            analyst_outputs=analyst_outputs,
            contradictions=contradictions,
            logical_issues=logical_issues,
            overall_coherence=coherence,
            recommendation=recommendation.strip() or "Synthesize perspectives carefully.",
        )

    def __repr__(self) -> str:
        return f"CriticAgent(model={self.model_name})"
