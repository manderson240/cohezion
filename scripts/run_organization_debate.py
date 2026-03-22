#!/usr/bin/env python3
"""
FLUME-Tracked Swarm Debate: Project Organization for Anthropic Showcase

This script runs a debate through the swarm to decide the best path forward
for organizing Cohezion as a showcase for the Anthropic Universes application.

CREDITS:
- R-Zero Protocol: Based on Huang et al. "R-Zero: Self-Evolving Reasoning LLM from Zero Data"
  https://chengsong-huang.github.io/R-Zero.github.io/
- FLUME: Fluid Latent Understanding through Manifold Encoding (Cohezion original)
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from cohezion.swarm.swarm_types import Perspective, SwarmConfig
from cohezion.swarm.workflows import DebateWorkflow


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


DEBATE_QUERY = """
We are organizing the Cohezion platform as a showcase for applying to Anthropic's
Research Engineer, Universes position. The swarm must debate and decide:

1. **Structure**: How should we organize 27+ modules to match Anthropic/HuggingFace standards?
2. **Showcase**: What are the TOP features to highlight? (FLUME, R-Zero, Swarms of SLMs)
3. **Evidence**: How do we validate our claims with working demos?
4. **Credits**: How do we properly attribute R-Zero and other external work?
5. **Automation**: Should we create cron jobs for continuous simulation data gathering?

CONTEXT:
- We have: SurrealDB, Marimo notebooks, Quarto integration, cohezion.duckdns.org domain
- We have open-notebooks.ai integration
- FLUME is our original creation (256-dim thought vectors, trajectory prediction)
- Swarms of small LMs that punch above their weight is our innovation
- R-Zero Challenger/Solver protocol adapted from Huang et al.

CONSTRAINT: The user said "We are calling ourselves Cohezion so we need to exemplify coherence"

What is the most coherent path forward?
"""


async def run_organization_debate():
    """Run the swarm debate with FLUME tracking."""

    # Configure for strategic decision-making
    config = SwarmConfig(
        analyst_model="phi3:mini",  # Local efficient model
        critic_model="phi3:mini",
        synthesizer_model="mistral:7b",  # Available for synthesis
    )

    # Use all three perspectives
    workflow = DebateWorkflow(
        config=config,
        perspectives=[
            Perspective.TECHNICAL,  # Engineering quality
            Perspective.ETHICAL,  # Attribution, honesty
            Perspective.HISTORICAL,  # What worked before
        ],
    )

    try:
        logger.info("Starting FLUME-tracked swarm debate...")
        start_time = datetime.now()

        response = await workflow.execute(DEBATE_QUERY)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Save results
        result = {
            "query": DEBATE_QUERY,
            "response": response.content,
            "confidence": response.confidence,
            "processing_time_ms": response.processing_time_ms,
            "model_chain": response.model_chain,
            "metrics": workflow.get_metrics(),
            "timestamp": start_time.isoformat(),
            "duration_seconds": duration,
        }

        output_path = Path("src/cohezion/knowledge_graph/debates/project_organization_2026-01-18.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2))

        # Print summary
        print("\n" + "=" * 80)
        print("SWARM DEBATE RESULT: PROJECT ORGANIZATION")
        print("=" * 80)
        print(f"\nConfidence: {response.confidence:.0%}")
        print(f"Processing Time: {response.processing_time_ms:.0f}ms")
        print(f"Model Chain: {' → '.join(response.model_chain)}")
        print("\n" + "-" * 80)
        print("SYNTHESIZED DECISION:")
        print("-" * 80)
        print(response.content)
        print("\n" + "=" * 80)
        print(f"\nResults saved to: {output_path}")

        return result

    finally:
        await workflow.close()


if __name__ == "__main__":
    asyncio.run(run_organization_debate())
