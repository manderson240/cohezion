"""
Git Health Agent - Analyzes repository hygiene and lineage.

Enables the swarm to examine git history and health from a repository-centric
perspective, identifying patterns of decay or rapid complexity growth.
"""

import logging
from datetime import datetime
from typing import Any

from cohezion.swarm.agents.base import BaseAgent
from cohezion.swarm.git_health import GitCommit, HealthTrace
from cohezion.swarm.swarm_types import Perspective, SwarmConfig, ThoughtVector

logger = logging.getLogger(__name__)

GIT_HEALTH_PROMPT = """You are a Git Health Specialist. Focus on:
- Repository hygiene (commit frequency, message quality, branch management)
- Code lineage and development velocity
- Identifying "heat maps" of rapid change and complexity accumulation
- Traceability between requirements and commits
Provide a diagnostic assessment of the repository's git health."""


class GitHealthAgent(BaseAgent):
    """
    Agent specialized in repository health and git history analysis.
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
        self.perspective = Perspective.TECHNICAL  # Or a new GIT perspective if needed
        self.system_prompt = GIT_HEALTH_PROMPT

    async def process(
        self,
        query: str,
        context: list[GitCommit] | list[HealthTrace] | None = None,
        **kwargs: Any,
    ) -> ThoughtVector:
        """
        Analyze the query and git context.
        """
        context_str = ""
        if context:
            context_str = "\n\nGit Context:\n"
            for item in context[:10]:  # Limit context
                if isinstance(item, GitCommit):
                    context_str += (
                        f"- {item.hash[:8]}: {item.message} ({item.author})\n"
                    )
                elif isinstance(item, HealthTrace):
                    context_str += f"- {item.file_path}:{item.line} (Authored by {item.author} in {item.commit_hash[:8]})\n"

        prompt = f"""Analyze the git health based on the following query and context.
Query: {query}{context_str}

Provide a focused analysis in 2-3 paragraphs."""

        try:
            response = await self._call_ollama(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=0.7,
                max_tokens=1024,
            )

            return ThoughtVector(
                perspective=self.perspective,
                content=response.strip(),
                confidence=0.85,
                timestamp=datetime.now(),
                metadata={
                    "model": self.model_name,
                    "agent": "GitHealthAgent",
                    "context_size": len(context) if context else 0,
                },
            )

        except Exception as e:
            logger.error(f"GitHealthAgent failed: {e}")
            return ThoughtVector(
                perspective=self.perspective,
                content=f"Analysis failed: {str(e)}",
                confidence=0.0,
                timestamp=datetime.now(),
                metadata={"error": str(e)},
            )
