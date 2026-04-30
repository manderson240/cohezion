"""
Debate Protocol Workflow - Hierarchical voting with parallel analysts.

The core cognitive workflow of the Cohezion Swarm:
1. Broadcast query → 3 Analyst agents (parallel)
2. Critic reviews outputs, highlights contradictions
3. Synthesizer resolves and produces final answer
"""

import asyncio
import logging
import time
from typing import Any, ClassVar

from cohezion.agents.analyst import AnalystAgent
from cohezion.agents.critic import CriticAgent
from cohezion.agents.synthesizer import SynthesizerAgent
from cohezion.swarm.swarm_types import (
    Perspective,
    SwarmConfig,
    SynthesizedResponse,
    ThoughtVector,
)


logger = logging.getLogger(__name__)


class DebateWorkflow:
    """
    The Hierarchical Voting debate protocol.

    Coordinates multiple analyst perspectives, critical review,
    and synthesis into a unified response.
    """

    DEFAULT_PERSPECTIVES: ClassVar[list[Perspective]] = [
        Perspective.TECHNICAL,
        Perspective.ETHICAL,
        Perspective.HISTORICAL,
    ]

    def __init__(
        self,
        config: SwarmConfig | None = None,
        perspectives: list[Perspective] | None = None,
    ):
        self.config = config or SwarmConfig()
        self.perspectives = perspectives or self.DEFAULT_PERSPECTIVES

        # Initialize agents
        self.analysts = [AnalystAgent(perspective=p, config=self.config) for p in self.perspectives]
        self.critic = CriticAgent(config=self.config)
        self.synthesizer = SynthesizerAgent(config=self.config)

        self._metrics: dict[str, Any] = {
            "total_queries": 0,
            "total_time_ms": 0,
            "analyst_time_ms": 0,
            "critic_time_ms": 0,
            "synthesis_time_ms": 0,
        }

    async def execute(self, query: str) -> SynthesizedResponse:
        """
        Execute the full debate protocol.

        Args:
            query: The user's question or task

        Returns:
            SynthesizedResponse with the unified answer
        """
        total_start = time.perf_counter()
        self._metrics["total_queries"] += 1

        logger.info("Starting debate workflow for query: %s...", query[:100].replace("\n", " "))

        # Phase 1: Parallel analysis
        analyst_start = time.perf_counter()
        thought_vectors = await self._run_analysts(query)
        self._metrics["analyst_time_ms"] += (time.perf_counter() - analyst_start) * 1000

        logger.info(f"Collected {len(thought_vectors)} analyst perspectives")

        # Phase 2: Critical review
        critic_start = time.perf_counter()
        critique = await self.critic.critique(thought_vectors)
        self._metrics["critic_time_ms"] += (time.perf_counter() - critic_start) * 1000

        logger.info(
            f"Critique complete: coherence={critique.overall_coherence:.0%}, "
            f"contradictions={len(critique.contradictions)}"
        )

        # Phase 3: Synthesis
        synthesis_start = time.perf_counter()
        response = await self.synthesizer.synthesize(critique, original_query=query)
        self._metrics["synthesis_time_ms"] += (time.perf_counter() - synthesis_start) * 1000

        total_time = (time.perf_counter() - total_start) * 1000
        self._metrics["total_time_ms"] += total_time

        logger.info(f"Debate complete in {total_time:.0f}ms")

        return response

    async def _run_analysts(self, query: str) -> list[ThoughtVector]:
        """Run all analysts in parallel and collect results."""
        tasks = [analyst.analyze(query) for analyst in self.analysts]

        # Use asyncio.gather with return_exceptions to handle partial failures
        results = await asyncio.gather(*tasks, return_exceptions=True)

        thought_vectors: list[ThoughtVector] = []
        for result in results:
            if isinstance(result, ThoughtVector):
                thought_vectors.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Analyst failed: {result}")

        return thought_vectors

    async def close(self) -> None:
        """Clean up all agent resources."""
        close_tasks = [agent.close() for agent in self.analysts] + [
            self.critic.close(),
            self.synthesizer.close(),
        ]
        await asyncio.gather(*close_tasks, return_exceptions=True)

    def get_metrics(self) -> dict[str, Any]:
        """Return workflow metrics."""
        total = self._metrics["total_queries"]
        return {
            **self._metrics,
            "avg_total_time_ms": self._metrics["total_time_ms"] / max(1, total),
            "avg_analyst_time_ms": self._metrics["analyst_time_ms"] / max(1, total),
            "avg_critic_time_ms": self._metrics["critic_time_ms"] / max(1, total),
            "avg_synthesis_time_ms": self._metrics["synthesis_time_ms"] / max(1, total),
            "perspectives": [p.value for p in self.perspectives],
        }

    def __repr__(self) -> str:
        perspectives = ", ".join(p.value for p in self.perspectives)
        return f"DebateWorkflow(perspectives=[{perspectives}])"


async def main() -> None:
    """Test the debate workflow with a sample query."""
    import argparse

    parser = argparse.ArgumentParser(description="Test the Debate Workflow")
    parser.add_argument("--test", action="store_true", help="Run test query")
    parser.add_argument("--query", type=str, help="Custom query to process")
    args = parser.parse_args()

    if not args.test and not args.query:
        parser.print_help()
        return

    logging.basicConfig(level=logging.INFO)

    query = args.query or "What are the implications of quantum computing for cryptography?"

    workflow = DebateWorkflow()
    try:
        response = await workflow.execute(query)

        print("\n" + "=" * 60)
        print("DEBATE RESULT")
        print("=" * 60)
        print(f"\nConfidence: {response.confidence:.0%}")
        print(f"Processing time: {response.processing_time_ms:.0f}ms")
        print(f"Model chain: {' → '.join(response.model_chain)}")
        print(f"\n{response.content}")
        print("\n" + "=" * 60)

        print("\nWorkflow Metrics:")
        for k, v in workflow.get_metrics().items():
            print(f"  {k}: {v}")

    finally:
        await workflow.close()


if __name__ == "__main__":
    asyncio.run(main())
