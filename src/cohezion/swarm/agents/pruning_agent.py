"""
PruningAgent - Knowledge Compression & Clutter Reduction (Gateway 9).

Identifies redundant thoughts, merges conceptual overlaps, and maintains
high information density across the swarm's memory.
"""

import logging

from cohezion.swarm.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class PruningAgent(BaseAgent):
    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(
            model_name="mistral:7b",
            config=config or SwarmConfig(),
        )

    async def process(self, task: str = "compress") -> str:
        """
        Perform knowledge compression on the swarm's memory.
        """
        logger.info("🧹 PruningAgent initiating knowledge compression...")

        # 1. Fetch thoughts from DB
        try:
            await self._db.connect()
            # Group by query_hash to find redundant tasks
            res = await self._db.query(
                "SELECT content, metadata.query_hash as qh, metadata.agent as agent "
                "FROM agent_thought ORDER BY timestamp DESC LIMIT 100"
            )
            await self._db.close()

            # Result format from our mock is often list of lists
            thoughts = res[0] if res and isinstance(res[0], list) else []
            logger.info(f"Retrieved {len(thoughts)} thoughts from DB.")
            if thoughts:
                logger.info(f"First thought keys: {thoughts[0].keys()}")

        except Exception as e:
            logger.error(f"Failed to fetch thoughts for pruning: {e}")
            return f"Compression failed: {e}"

        if not thoughts:
            return "No thoughts found to compress."

        # 2. Identify redundancy
        groups = {}
        for t in thoughts:
            qh = t.get("qh", "unknown")
            if qh not in groups:
                groups[qh] = []
            groups[qh].append(t)

        redundant_groups = {k: v for k, v in groups.items() if len(v) > 1}

        if not redundant_groups:
            return "No significant redundancy detected in recent memory."

        # 3. Propose compression
        report = ["## Knowledge Compression Report"]
        for qh, group in redundant_groups.items():
            report.append(f"\n### Cluster: {qh} ({len(group)} duplicates)")
            example_content = group[0].get("content", "")[:200]
            report.append(f"Content Preview: {example_content}...")

            # Simple merge logic for MVP: Propose a synthesis
            prompt = f"""The following {len(group)} thoughts are semantically redundant.
Synthesize them into a single, high-density 'Master Thought' that preserves
all unique information while removing repetition.

THOUGHTS:
{chr(10).join([t.get('content', '')[:500] for t in group])}

MASTER THOUGHT:
"""
            synthesis = await self._call_ollama(prompt, temperature=0.3)
            report.append(f"**Proposed Synthesis:**\n{synthesis}")

        return "\n".join(report)

    async def execute_pruning(self, report: str) -> bool:
        """
        Apply the proposed compression (stub for now).
        """
        logger.info("Applying pruning optimizations to SurrealDB...")
        # In a real scenario, this would delete redundant rows and insert the Master Thought
        return True
