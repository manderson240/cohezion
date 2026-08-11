r"""Mycelium Swarm Knowledge & Context Transport Network
======================================================
Implements Mycelium distributed graph connections linking agents, background tasks,
local silicon nodes, and vault entries through organic hyphae transport links.

Hyphae Mechanics:
  - Hypha Link: Edge(u, v) with weight w \in [0.0, 1.0] representing context affinity.
  - Nutrient Transport: Instantaneous transfer of high-reward state vectors & learnings.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class HyphaEdge:
    source_node: str
    target_node: str
    hypha_strength: float
    nutrient_type: str


@dataclass(frozen=True, slots=True)
class TransportResult:
    delivered_nutrients: int
    active_hyphae_count: int
    network_coherence: float


class MyceliumNetwork:
    """Mycelium Distributed Knowledge Transport Network."""

    def __init__(self) -> None:
        self.nodes: set[str] = set()
        self.hyphae: list[HyphaEdge] = []

    def register_node(self, node_id: str) -> None:
        self.nodes.add(node_id)

    def grow_hypha(self, source: str, target: str, strength: float = 0.8, nutrient_type: str = "context_vector") -> HyphaEdge:
        self.register_node(source)
        self.register_node(target)
        edge = HyphaEdge(
            source_node=source,
            target_node=target,
            hypha_strength=min(1.0, max(0.0, strength)),
            nutrient_type=nutrient_type,
        )
        self.hyphae.append(edge)
        return edge

    def transport_nutrients(self, source: str) -> TransportResult:
        """Transport contextual nutrients from source across all connected mycelial hyphae."""
        connected = [e for e in self.hyphae if e.source_node == source]
        delivered = len(connected)
        avg_strength = (sum(e.hypha_strength for e in connected) / delivered) if delivered > 0 else 0.0

        return TransportResult(
            delivered_nutrients=delivered,
            active_hyphae_count=len(self.hyphae),
            network_coherence=round(avg_strength, 4),
        )
