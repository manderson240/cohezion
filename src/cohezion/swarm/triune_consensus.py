"""Triune Consensus & Homology Visualization (Story 2.7, NFR-7, FR-14).

Computes geometric equilibrium of the Triune agents (Architect, Engineer, Biologist)
and live KL Divergence for 512D→12D projection validation.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np


logger = logging.getLogger(__name__)

TRIUNE_AGENTS = ["architect", "engineer", "biologist"]


@dataclass
class AgentProposal:
    agent_id: str  # "architect" | "engineer" | "biologist"
    state_12d: list[float]
    confidence: float  # 0.0-1.0


@dataclass
class GeometricEquilibrium:
    """The geometric center of the Triune proposals."""

    centroid_12d: list[float]
    max_divergence: float  # Max L2 distance from centroid
    is_consensus: bool  # True if all agents agree within threshold

    def to_dict(self) -> dict:
        return {
            "centroid_12d": self.centroid_12d,
            "max_divergence": self.max_divergence,
            "is_consensus": self.is_consensus,
        }


@dataclass
class ConsensusReport:
    equilibrium: GeometricEquilibrium
    kl_divergence: float
    proposals: list[AgentProposal]
    quorum_reached: bool

    def to_dict(self) -> dict:
        return {
            "equilibrium": self.equilibrium.to_dict(),
            "kl_divergence": self.kl_divergence,
            "agent_count": len(self.proposals),
            "quorum_reached": self.quorum_reached,
        }


class TriuneConsensus:
    """Computes geometric equilibrium and KL divergence across Triune agents."""

    def __init__(self, consensus_threshold: float = 0.3) -> None:
        self.consensus_threshold = consensus_threshold
        self._history: list[ConsensusReport] = []

    def deliberate(self, proposals: list[AgentProposal]) -> ConsensusReport:
        """Compute geometric equilibrium and KL divergence from proposals."""
        if not proposals:
            raise ValueError("At least one proposal required")

        states = np.array([p.state_12d for p in proposals])
        centroid = states.mean(axis=0)

        # Maximum divergence from centroid
        distances = [float(np.linalg.norm(s - centroid)) for s in states]
        max_divergence = max(distances)
        is_consensus = max_divergence <= self.consensus_threshold

        equilibrium = GeometricEquilibrium(
            centroid_12d=centroid.tolist(),
            max_divergence=round(max_divergence, 4),
            is_consensus=is_consensus,
        )

        # KL Divergence: compare confidence distributions
        kl_div = self._compute_kl_divergence([p.confidence for p in proposals])

        quorum = len(proposals) >= 2  # Minimum 2 of 3 agents needed for quorum
        report = ConsensusReport(
            equilibrium=equilibrium,
            kl_divergence=round(kl_div, 4),
            proposals=proposals,
            quorum_reached=quorum,
        )
        self._history.append(report)
        return report

    def get_history(self) -> list[dict]:
        return [r.to_dict() for r in self._history]

    def _compute_kl_divergence(self, probs: list[float]) -> float:
        """Compute KL divergence from uniform distribution."""
        n = len(probs)
        if n < 2:
            return 0.0
        uniform = 1.0 / n
        total = sum(probs) + 1e-9
        normalized = [p / total for p in probs]
        kl = 0.0
        for p in normalized:
            if p > 1e-9:
                kl += p * math.log(p / uniform)
        return kl
