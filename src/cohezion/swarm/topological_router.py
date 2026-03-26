"""Topology-aware agent routing using persistent homology.

Goes beyond visualization to use TDA as an OPTIMIZATION signal for
task routing in multi-agent systems. Extends the position paper
[2505.22467] by implementing actual topology-aware routing.

Strategy:
  1. Compute persistence diagram of each agent's trajectory history
  2. Classify agents by topological regime:
     - EXPLOIT: High-persistence H₀ cluster (stable behavior, send known tasks)
     - EXPLORE: Between clusters (boundary agent, send novel tasks)
     - PIVOT: H₁ loop detected (stuck cycling, needs new strategy)
  3. Match incoming tasks to agents based on topological distance

Key insight from [PH-GCAPCN, 2603.06964]:
  Persistent homology in RL yields 9-18% higher rewards. We apply
  this to cognitive agent routing, not power grids.

References:
  - [2505.22467] Topological Structure Learning for LLM-Based MAS
  - [2603.06964] Topology-Aware RL over Graphs (PH-GCAPCN)
  - Edelsbrunner & Harer (2010): Computational Topology
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

import numpy as np

from cohezion.compound.topological_persistence import (
    TopologicalPersistence,
    trajectory_persistence_summary,
)

logger = logging.getLogger(__name__)


class TopologicalRegime(str, Enum):
    """Agent behavioral regime determined by trajectory topology."""

    EXPLOIT = "exploit"  # Stable cluster — send familiar tasks
    EXPLORE = "explore"  # Between clusters — send novel tasks
    PIVOT = "pivot"  # Stuck in loop — needs strategy change
    UNKNOWN = "unknown"  # Insufficient data


@dataclass
class AgentTopology:
    """Topological profile of an agent's trajectory history."""

    agent_id: str
    regime: TopologicalRegime
    n_clusters: int  # H₀ features
    n_loops: int  # H₁ features
    persistence_entropy_h0: float
    persistence_entropy_h1: float
    max_persistence_h0: float
    max_persistence_h1: float
    total_persistence: float
    trajectory_length: int

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "regime": self.regime.value,
            "n_clusters": self.n_clusters,
            "n_loops": self.n_loops,
            "persistence_entropy_h0": self.persistence_entropy_h0,
            "persistence_entropy_h1": self.persistence_entropy_h1,
            "max_persistence_h0": self.max_persistence_h0,
            "max_persistence_h1": self.max_persistence_h1,
            "total_persistence": self.total_persistence,
            "trajectory_length": self.trajectory_length,
        }


@dataclass
class RoutingDecision:
    """Result of topology-aware task routing."""

    task_id: str
    assigned_agent: str
    regime: TopologicalRegime
    confidence: float
    reasoning: str

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "assigned_agent": self.assigned_agent,
            "regime": self.regime.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }


class TopologicalRouter:
    """Route tasks to agents based on their topological trajectory profile.

    Parameters
    ----------
    min_trajectory_length : int
        Minimum trajectory points needed to compute topology (default: 5).
    loop_threshold : float
        Minimum H₁ persistence to count as a loop (default: 0.1).
    cluster_threshold : float
        Minimum H₀ persistence to count as a cluster (default: 0.05).
    """

    def __init__(
        self,
        min_trajectory_length: int = 5,
        loop_threshold: float = 0.1,
        cluster_threshold: float = 0.05,
    ) -> None:
        self.min_trajectory_length = min_trajectory_length
        self.loop_threshold = loop_threshold
        self.cluster_threshold = cluster_threshold
        self._agent_trajectories: dict[str, list[np.ndarray]] = {}
        self._agent_topologies: dict[str, AgentTopology] = {}

    def record_trajectory_point(self, agent_id: str, point: np.ndarray) -> None:
        """Record a new trajectory point for an agent."""
        if agent_id not in self._agent_trajectories:
            self._agent_trajectories[agent_id] = []
        self._agent_trajectories[agent_id].append(point.copy())

    def analyze_agent(self, agent_id: str) -> AgentTopology:
        """Compute topological profile for an agent.

        Uses persistent homology to classify the agent into
        EXPLOIT, EXPLORE, or PIVOT regime.
        """
        trajectory = self._agent_trajectories.get(agent_id, [])

        if len(trajectory) < self.min_trajectory_length:
            topo = AgentTopology(
                agent_id=agent_id,
                regime=TopologicalRegime.UNKNOWN,
                n_clusters=0,
                n_loops=0,
                persistence_entropy_h0=0.0,
                persistence_entropy_h1=0.0,
                max_persistence_h0=0.0,
                max_persistence_h1=0.0,
                total_persistence=0.0,
                trajectory_length=len(trajectory),
            )
            self._agent_topologies[agent_id] = topo
            return topo

        # Compute persistence summary
        summary = trajectory_persistence_summary(
            trajectory, significance_threshold=self.cluster_threshold
        )

        # Classify regime
        regime = self._classify_regime(summary)

        topo = AgentTopology(
            agent_id=agent_id,
            regime=regime,
            n_clusters=summary["n_clusters"],
            n_loops=summary["n_loops"],
            persistence_entropy_h0=summary["persistence_entropy_h0"],
            persistence_entropy_h1=summary["persistence_entropy_h1"],
            max_persistence_h0=summary["max_persistence_h0"],
            max_persistence_h1=summary["max_persistence_h1"],
            total_persistence=summary["total_persistence"],
            trajectory_length=len(trajectory),
        )
        self._agent_topologies[agent_id] = topo
        return topo

    def _classify_regime(self, summary: dict) -> TopologicalRegime:
        """Classify agent regime from persistence summary.

        Rules:
        - PIVOT: significant H₁ loops (agent is cycling)
        - EXPLOIT: single dominant H₀ cluster, low entropy (stable)
        - EXPLORE: multiple clusters or high entropy (diverse behavior)
        """
        # Check for loops first (highest priority — stuck cycling)
        if summary["n_loops"] > 0 and summary["max_persistence_h1"] > self.loop_threshold:
            return TopologicalRegime.PIVOT

        # Check cluster structure
        if summary["n_clusters"] <= 1 and summary["persistence_entropy_h0"] < 0.5:
            # Single stable cluster
            return TopologicalRegime.EXPLOIT

        # Multiple clusters or high entropy
        return TopologicalRegime.EXPLORE

    def route_task(
        self,
        task_id: str,
        task_complexity: str = "medium",
        available_agents: list[str] | None = None,
    ) -> RoutingDecision:
        """Route a task to the best agent based on topology.

        Parameters
        ----------
        task_id : str
            Task identifier.
        task_complexity : str
            "simple", "medium", or "complex".
        available_agents : list[str] or None
            Agents available for assignment. If None, uses all known agents.

        Returns
        -------
        RoutingDecision with assigned agent, regime, and reasoning.
        """
        agents = available_agents or list(self._agent_trajectories.keys())

        if not agents:
            return RoutingDecision(
                task_id=task_id,
                assigned_agent="",
                regime=TopologicalRegime.UNKNOWN,
                confidence=0.0,
                reasoning="No agents available",
            )

        # Analyze all available agents
        topologies = {}
        for agent_id in agents:
            topologies[agent_id] = self.analyze_agent(agent_id)

        # Routing strategy based on task complexity
        if task_complexity == "simple":
            # Simple tasks → EXPLOIT agents (stable, predictable)
            best = self._select_by_regime(
                topologies, [TopologicalRegime.EXPLOIT, TopologicalRegime.UNKNOWN]
            )
            reasoning = "Simple task → exploit agent (stable behavior)"
        elif task_complexity == "complex":
            # Complex tasks → EXPLORE agents (diverse, adaptive)
            best = self._select_by_regime(
                topologies, [TopologicalRegime.EXPLORE, TopologicalRegime.UNKNOWN]
            )
            reasoning = "Complex task → explore agent (diverse behavior)"
        else:
            # Medium tasks → anyone not in PIVOT
            best = self._select_by_regime(
                topologies,
                [TopologicalRegime.EXPLOIT, TopologicalRegime.EXPLORE, TopologicalRegime.UNKNOWN],
            )
            reasoning = "Medium task → best available non-pivot agent"

        if best is None:
            # Fallback: first available agent
            best_id = agents[0]
            regime = topologies[best_id].regime
            confidence = 0.3
            reasoning = "Fallback: all agents in pivot, using first available"
        else:
            best_id = best.agent_id
            regime = best.regime
            confidence = 0.8 if regime != TopologicalRegime.UNKNOWN else 0.5

        return RoutingDecision(
            task_id=task_id,
            assigned_agent=best_id,
            regime=regime,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _select_by_regime(
        self,
        topologies: dict[str, AgentTopology],
        preferred_regimes: list[TopologicalRegime],
    ) -> AgentTopology | None:
        """Select best agent from preferred regimes.

        Within a regime, prefer agents with higher total persistence
        (more experience = better topology signal).
        """
        candidates = [t for t in topologies.values() if t.regime in preferred_regimes]
        if not candidates:
            return None

        # Sort by total persistence (more experience first)
        candidates.sort(key=lambda t: t.total_persistence, reverse=True)
        return candidates[0]

    def get_all_topologies(self) -> dict[str, AgentTopology]:
        """Return topological profiles for all known agents."""
        for agent_id in self._agent_trajectories:
            if agent_id not in self._agent_topologies:
                self.analyze_agent(agent_id)
        return self._agent_topologies.copy()

    def get_routing_summary(self) -> dict:
        """Summary of agent regimes for the dashboard."""
        topologies = self.get_all_topologies()
        regime_counts = {r.value: 0 for r in TopologicalRegime}
        for t in topologies.values():
            regime_counts[t.regime.value] += 1

        return {
            "total_agents": len(topologies),
            "regime_distribution": regime_counts,
            "agents": {aid: t.to_dict() for aid, t in topologies.items()},
        }


__all__ = [
    "AgentTopology",
    "RoutingDecision",
    "TopologicalRegime",
    "TopologicalRouter",
]
