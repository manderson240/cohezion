"""Mycelium Distributed Knowledge Network.

Allows EVO agents to instantly broadcast and synchronize learned insights
across the entire semantic space, reducing redundant research paths.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel


logger = logging.getLogger(__name__)


class KnowledgeSpore(BaseModel):
    """A synthesized insight or learned paradigm broadcast to the network."""

    origin_evo_id: str
    topic: str
    insight_vector: list[float]  # Typically FLUME compressed dimension
    summary_text: str
    confidence: float


class MyceliumNetwork:
    """The distributed knowledge graph connecting all EVOs."""

    def __init__(self) -> None:
        self._network_graph: dict[str, list[KnowledgeSpore]] = {}
        self._connected_evos: set[str] = set()

    def connect_evo(self, evo_id: str) -> None:
        """Attach an EVO to the Mycelium network."""
        self._connected_evos.add(evo_id)
        if evo_id not in self._network_graph:
            self._network_graph[evo_id] = []
        logger.debug(f"EVO {evo_id} connected to Mycelium network.")

    async def broadcast_insight(self, spore: KnowledgeSpore) -> int:
        """Broadcast a newly learned intelligence spore to all connected EVOs."""
        logger.info(
            f"EVO {spore.origin_evo_id} broadcasting spore "
            f"on '{spore.topic}' with confidence {spore.confidence:.2f}"
        )

        receivers = 0
        for evo_id in self._connected_evos:
            if evo_id != spore.origin_evo_id:
                # In a real SurrealDB setting this would be a graph edge insertion
                self._network_graph[evo_id].append(spore)
                receivers += 1

        logger.info(f"Mycelium propagation complete. Reached {receivers} EVOs.")
        return receivers

    def query_insights(self, evo_id: str, topic_keyword: str) -> list[KnowledgeSpore]:
        """Allow an EVO to query its local Mycelium cache for related insights."""
        if evo_id not in self._network_graph:
            return []

        relevant = [
            spore
            for spore in self._network_graph[evo_id]
            if topic_keyword.lower() in spore.topic.lower()
            or topic_keyword.lower() in spore.summary_text.lower()
        ]
        return relevant
