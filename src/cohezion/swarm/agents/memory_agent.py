"""
MemoryAgent - Long-Term Contextual Memory (Gateway 7/14).

Retrieves relevant historical thoughts and outcomes from SurrealDB
using vector similarity search to provide agents with long-term context.
"""

import logging
from typing import Any

from cohezion.swarm.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class MemoryAgent(BaseAgent):
    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(
            model_name="mistral:7b",
            config=config or SwarmConfig(),
        )

    @staticmethod
    async def retrieve_context(
        db_client: Any, encoder: Any, query: str, limit: int
    ) -> str:
        """
        Static Memory Kernel (Dense Cluster).
        Performs the retrieval logic.
        """
        logger.info(f"🧠 MemoryCluster searching for: {query[:50]}...")

        # 1. Generate embedding
        z_query = encoder.get_semantic_vector(query)

        # 2. Query DB
        try:
            await db_client.connect()
            similar_nodes = await db_client.query_similar(z_query, limit=limit)
            await db_client.close()
        except Exception as e:
            logger.error(f"Memory retrieval failed: {e}")
            return ""

        if not similar_nodes:
            return ""

        # 3. Format
        context_lines = ["### Long-Term Memory Context:"]
        for i, node in enumerate(similar_nodes):
            context_lines.append(f"\n{i+1}. [Memory ID: {node.id}]")
            context_lines.append(f"Content: {node.content[:500]}...")
            if "agent" in node.metadata:
                context_lines.append(f"Source: {node.metadata['agent']} Agent")

        return "\n".join(context_lines)

    async def get_relevant_context(self, query: str, limit: int = 5) -> str:
        """
        Public Interface for Memory Retrieval.
        Delegates to the Static Memory Kernel (EVO Cluster).
        """
        if self._encoder is None:
            from cohezion.flume.autoencoder import FlumeConfig, FlumeEncoder

            self._encoder = FlumeEncoder(FlumeConfig())

        return await self.retrieve_context(self._db, self._encoder, query, limit)

    async def process(self, query: str, **kwargs: Any) -> str:
        """
        Synthesize context for a given query.
        """
        context = await self.get_relevant_context(query)
        if not context:
            return "No prior memory relevant to this query was found."

        prompt = f"""Based on the following retrieved memories, synthesize a concise
summary of what the swarm knows about this topic. Focus on unique insights
and previous outcomes.

TOPIC: {query}

MEMORIES:
{context}

MEMORY SYNTHESIS:
"""
        synthesis = await self._call_ollama(prompt, temperature=0.3)
        return synthesis
