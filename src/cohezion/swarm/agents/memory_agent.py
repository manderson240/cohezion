"""
MemoryAgent - Long-Term Contextual Memory (Gateway 7/14).

Retrieves relevant historical thoughts and outcomes from SurrealDB
using vector similarity search to provide agents with long-term context.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from cohezion.swarm.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)

class MemoryAgent(BaseAgent):
    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(
            model_name="mistral:7b",
            config=config or SwarmConfig(),
        )

    async def get_relevant_context(self, query: str, limit: int = 5) -> str:
        """
        Search memory for documents relevant to the query.
        """
        logger.info(f"🧠 MemoryAgent searching for context: {query[:50]}...")

        # 1. Generate embedding for the query
        if self._encoder is None:
            from cohezion.flume.autoencoder import FlumeEncoder, FlumeConfig
            self._encoder = FlumeEncoder(FlumeConfig())

        z_query = self._encoder.get_semantic_vector(query)

        # 2. Query SurrealDB for similar nodes
        try:
            await self._db.connect()
            similar_nodes = await self._db.query_similar(z_query, limit=limit)
            await self._db.close()
        except Exception as e:
            logger.error(f"Memory retrieval failed: {e}")
            return ""

        if not similar_nodes:
            logger.info("No relevant memories found.")
            return ""

        # 3. Format context block
        context_lines = ["### Long-Term Memory Context:"]
        for i, node in enumerate(similar_nodes):
            # Extract score if available (SurrealDB returns 'score' in metadata or result)
            # In our mock/InMemoryStore, we don't return the score directly in the object yet
            context_lines.append(f"\n{i+1}. [Memory ID: {node.id}]")
            context_lines.append(f"Content: {node.content[:500]}...")
            if "agent" in node.metadata:
                context_lines.append(f"Source: {node.metadata['agent']} Agent")

        return "\n".join(context_lines)

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
