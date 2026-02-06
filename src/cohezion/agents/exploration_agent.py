"""
ExplorationAgent - Emergent Behavior & Novelty Tracking (Gateway 10).

Monitors the swarm for unusual conceptual transitions, "Surprise Events",
and emergent behaviors that deviate from standard patterns.
"""

import logging

import numpy as np

from cohezion.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class ExplorationAgent(BaseAgent):
    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(
            model_name="mistral:7b",
            config=config or SwarmConfig(),
        )

    async def process(self, task: str = "audit_novelty") -> str:
        """
        Audit the swarm's memory for high-novelty "Emergent Signals".
        """
        logger.info("🔭 ExplorationAgent scanning for emergent signals...")

        # 1. Fetch recent thoughts with embeddings
        try:
            nodes = await self._db.get_all_nodes(limit=50)
        except Exception as e:
            logger.error(f"Failed to fetch nodes for novelty scan: {e}")
            return f"Scan failed: {e}"

        if not nodes:
            return "No memory nodes found to analyze."

        logger.info(f"Retrieved {len(nodes)} nodes.")
        if nodes:
            logger.info(f"First node keys: {nodes[0].__dict__.keys()}")
            logger.info(f"First node embedding: {type(nodes[0].embedding)}")

        # 2. Compute Novelty (simplified: distance from centroid)
        embeddings = [n.embedding for n in nodes if n.embedding]
        logger.info(f"Found {len(embeddings)} embeddings.")
        if not embeddings:
            return "No embeddings found for novelty analysis. Ensure FLUME is active."

        # Convert to numpy for centroid calculation
        matrix = np.array(embeddings)
        centroid = np.mean(matrix, axis=0)

        # Calculate distances to centroid
        signals = []
        for node in nodes:
            if not node.embedding:
                continue

            vec = np.array(node.embedding)
            dist = np.linalg.norm(vec - centroid)

            # If distance is high (> 2 standard deviations), it's a surprise
            if dist > 1.5:  # Threshold for "Discovery"
                signals.append(
                    {
                        "id": node.id,
                        "content": node.content[:200],
                        "novelty_score": float(dist),
                        "agent": node.metadata.get("agent", "unknown"),
                    }
                )

        if not signals:
            return "No high-novelty signals detected in the current manifold."

        # 3. Analyze Surprise Events
        report = ["## Emergent Behavior & Novelty Report"]
        report.append(f"Centroid analyzed across {len(nodes)} conceptual points.")

        for signal in sorted(signals, key=lambda x: x["novelty_score"], reverse=True)[
            :5
        ]:
            report.append(
                f"\n### Signal: {signal['id']} (Novelty: {signal['novelty_score']:.2f})"
            )
            report.append(f"Agent: {signal['agent']}")
            report.append(f"Content: {signal['content']}...")

            # Ask the model to interpret why this is novel
            prompt = f"""Analyze this 'Surprise Event' from the swarm's memory.
Why is this conceptually novel compared to standard patterns?
Does it represent a new emergent behavior or a creative breakthrough?

EVENT CONTENT:
{signal["content"]}

INTERPRETATION:
"""
            interpretation = await self._call_ollama(prompt, temperature=0.5)
            report.append(f"**Interpretation:**\n{interpretation}")

        return "\n".join(report)
