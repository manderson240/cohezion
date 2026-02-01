"""
Code Simplification Agent - Reduces complexity based on refactoring patterns.

Targeted agent for reducing code complexity identified by git health audits.
Implements CODE_SIMPLIFICATION_PRIME principles.
"""

import logging
from datetime import datetime
from typing import Any

from cohezion.swarm.agents.base import BaseAgent
from cohezion.swarm.git_health import HealthTrace
from cohezion.swarm.swarm_types import Perspective, SwarmConfig, ThoughtVector

logger = logging.getLogger(__name__)

SIMPLIFIER_PROMPT = """You are a Code Simplification Specialist. Your goal is to:
- Reduce cyclomatic complexity and nesting
- Apply guard clauses to flatten logic
- Use explicit naming and clear structures (match/case over if/else)
- Preserving functionality while maximizing readability
Analyze code snippets and propose specific refactors based on CODE_SIMPLIFICATION_PRIME."""


class CodeSimplificationAgent(BaseAgent):
    """
    Agent specialized in simplifying complex code structures.
    """

    def __init__(
        self,
        config: SwarmConfig | None = None,
    ):
        config = config or SwarmConfig()
        super().__init__(
            model_name=config.analyst_model,
            config=config,
        )
        self.perspective = Perspective.TECHNICAL
        self.system_prompt = SIMPLIFIER_PROMPT

    async def process(
        self, query: str, traces: list[HealthTrace] | None = None, **kwargs: Any
    ) -> ThoughtVector:
        """
        Analyze code traces and suggest simplifications.
        """
        context_str = ""
        if traces:
            context_str = "\n\nComplexity Traces:\n"
            for trace in traces[:5]:
                context_str += f"- File: {trace.file_path}, Line: {trace.line}\n"
                if trace.issue:
                    context_str += f"  Issue: {trace.issue.message} (Score: {trace.issue.category})\n"
                context_str += f"  Authored: {trace.author} on {trace.date.date()}\n"

        prompt = f"""Suggest code simplifications for the repository based on the following query and complexity findings.
Query: {query}{context_str}

Provide specific refactoring suggestions based on the identified issues."""

        try:
            response = await self._call_ollama(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=0.6,  # Slightly lower for more deterministic refactors
                max_tokens=2048,
            )

            return ThoughtVector(
                perspective=self.perspective,
                content=response.strip(),
                confidence=0.9,
                timestamp=datetime.now(),
                metadata={
                    "model": self.model_name,
                    "agent": "CodeSimplificationAgent",
                    "traces_count": len(traces) if traces else 0,
                },
            )

        except Exception as e:
            logger.error(f"CodeSimplificationAgent failed: {e}")
            return ThoughtVector(
                perspective=self.perspective,
                content=f"Refactoring proposal failed: {str(e)}",
                confidence=0.0,
                timestamp=datetime.now(),
                metadata={"error": str(e)},
            )
