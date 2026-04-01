"""Topology-aware agent routing using persistent homology and Laplacian spectra.

Goes beyond visualization to use TDA as an OPTIMIZATION signal for
task routing in multi-agent systems. Extends the position paper
[2505.22467] by implementing actual topology-aware routing.

Strategy:
  1. Compute persistence diagram of each agent's trajectory history
  2. Compute graph Laplacian spectral features (Fiedler value, spectral gap)
  3. Classify agents by topological regime using BOTH topology and geometry:
     - EXPLOIT: High-persistence H₀ cluster + high Fiedler (tight, connected)
     - EXPLORE: Between clusters or low Fiedler + high H₁ (loose, loopy)
     - PIVOT: H₁ loop detected OR very low Fiedler (nearly disconnected)
  4. Match incoming tasks to agents based on topological distance

Key insights:
  [PH-GCAPCN, 2603.06964]: Persistent homology in RL yields 9-18% higher
    rewards. We apply this to cognitive agent routing, not power grids.
  [2507.19504]: Persistent Topological Laplacians capture BOTH topology AND
    geometry — persistent homology alone misses geometric shape information.
    The Fiedler value (algebraic connectivity) and spectral gap quantify
    how well-connected the trajectory graph is, complementing Betti numbers.

References:
  - [2505.22467] Topological Structure Learning for LLM-Based MAS
  - [2603.06964] Topology-Aware RL over Graphs (PH-GCAPCN)
  - [2507.19504] Persistent Topological Laplacians
  - Edelsbrunner & Harer (2010): Computational Topology
  - Fiedler (1973): Algebraic Connectivity of Graphs
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

import numpy as np
from scipy.spatial.distance import pdist, squareform

from cohezion.compound.topological_persistence import (
    trajectory_persistence_summary,
)


logger = logging.getLogger(__name__)


@dataclass
class SpectralFeatures:
    """Spectral features from the graph Laplacian of a trajectory point cloud.

    The graph Laplacian L = D - A captures geometric connectivity that
    persistent homology misses. The eigenvalues of L (the spectrum) encode
    how tightly connected different parts of the graph are.

    Attributes
    ----------
    fiedler_value : float
        2nd smallest eigenvalue of L (algebraic connectivity).
        High = well-connected graph, low = loosely coupled / near-disconnected.
    spectral_gap : float
        Ratio lambda_3 / lambda_2 (or 0 if lambda_2 ~ 0).
        Large gap = clear separation between connectivity mode and higher modes.
    eigenvalues : np.ndarray
        Full sorted spectrum of L.
    n_near_zero : int
        Number of eigenvalues near zero (~ number of connected components).
    """

    fiedler_value: float
    spectral_gap: float
    eigenvalues: np.ndarray
    n_near_zero: int

    def to_dict(self) -> dict:
        return {
            "fiedler_value": self.fiedler_value,
            "spectral_gap": self.spectral_gap,
            "n_near_zero": self.n_near_zero,
        }


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
    spectral: SpectralFeatures | None = None

    def to_dict(self) -> dict:
        result = {
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
        if self.spectral is not None:
            result["spectral"] = self.spectral.to_dict()
        return result


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
        fiedler_pivot_threshold: float = 0.05,
        fiedler_exploit_threshold: float = 0.3,
    ) -> None:
        self.min_trajectory_length = min_trajectory_length
        self.loop_threshold = loop_threshold
        self.cluster_threshold = cluster_threshold
        self.fiedler_pivot_threshold = fiedler_pivot_threshold
        self.fiedler_exploit_threshold = fiedler_exploit_threshold
        self._agent_trajectories: dict[str, list[np.ndarray]] = {}
        self._agent_topologies: dict[str, AgentTopology] = {}

    def spectral_features(
        self,
        trajectory_points: list[np.ndarray],
        epsilon: float | None = None,
    ) -> SpectralFeatures:
        """Compute graph Laplacian spectral features from trajectory points.

        Builds an epsilon-neighborhood graph from the point cloud, computes
        the graph Laplacian L = D - A, and extracts spectral features that
        capture geometric connectivity.

        Parameters
        ----------
        trajectory_points : list[np.ndarray]
            Trajectory points in latent space.
        epsilon : float | None
            Neighborhood radius for adjacency. If None, uses the median
            pairwise distance (adaptive to data scale).

        Returns
        -------
        SpectralFeatures
            Fiedler value, spectral gap, eigenvalues, near-zero count.
        """
        points = np.array(trajectory_points)
        n = points.shape[0]

        if n < 2:
            return SpectralFeatures(
                fiedler_value=0.0,
                spectral_gap=0.0,
                eigenvalues=np.zeros(n),
                n_near_zero=n,
            )

        # Compute pairwise distances and build adjacency
        dist_vec = pdist(points)
        dist_matrix = squareform(dist_vec)

        if epsilon is None:
            epsilon = float(np.median(dist_vec)) if len(dist_vec) > 0 else 1.0

        # Adjacency: connect points within epsilon
        adjacency = (dist_matrix <= epsilon).astype(float)
        np.fill_diagonal(adjacency, 0.0)

        # Graph Laplacian: L = D - A
        degree = np.diag(adjacency.sum(axis=1))
        laplacian = degree - adjacency

        # Eigenvalues (L is symmetric positive semi-definite)
        eigenvalues = np.linalg.eigvalsh(laplacian)
        eigenvalues = np.sort(eigenvalues)

        # Near-zero eigenvalues (~connected components)
        zero_tol = 1e-8
        n_near_zero = int(np.sum(np.abs(eigenvalues) < zero_tol))

        # Fiedler value (2nd smallest eigenvalue)
        fiedler_value = float(eigenvalues[1]) if n >= 2 else 0.0

        # Spectral gap: lambda_3 / lambda_2
        if n >= 3 and fiedler_value > zero_tol:
            spectral_gap = float(eigenvalues[2] / fiedler_value)
        else:
            spectral_gap = 0.0

        return SpectralFeatures(
            fiedler_value=fiedler_value,
            spectral_gap=spectral_gap,
            eigenvalues=eigenvalues,
            n_near_zero=n_near_zero,
        )

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

        # Compute spectral features (Laplacian spectrum)
        spectral = self.spectral_features(trajectory)

        # Classify regime using both topology and geometry
        regime = self._classify_regime(summary, spectral)

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
            spectral=spectral,
        )
        self._agent_topologies[agent_id] = topo
        return topo

    def _classify_regime(
        self,
        summary: dict,
        spectral: SpectralFeatures | None = None,
    ) -> TopologicalRegime:
        """Classify agent regime from persistence summary and spectral features.

        The Laplacian spectrum complements Betti numbers by capturing
        geometric connectivity. Combined rules:

        - PIVOT: significant H₁ loops OR very low Fiedler value
          (cycling behavior or nearly disconnected trajectory graph)
        - EXPLOIT: single dominant H₀ cluster + high Fiedler value
          (stable, tightly connected behavior)
        - EXPLORE: multiple clusters, high entropy, or low Fiedler + high H₁
          (loose, diverse, or loopy behavior)
        """
        fiedler = spectral.fiedler_value if spectral is not None else None
        n_components = spectral.n_near_zero if spectral is not None else 1

        # PIVOT: persistent loops (highest priority — stuck cycling)
        if summary["n_loops"] > 0 and summary["max_persistence_h1"] > self.loop_threshold:
            return TopologicalRegime.PIVOT

        # PIVOT: very low Fiedler AND multiple components confirmed by both
        # the Laplacian spectrum AND persistent homology (multiple significant
        # clusters). This prevents false PIVOTs from sparse epsilon-graphs in
        # high-dimensional spaces where the adaptive epsilon is too small.
        if (
            fiedler is not None
            and fiedler < self.fiedler_pivot_threshold
            and n_components >= 3
            and summary["n_clusters"] >= 3
        ):
            return TopologicalRegime.PIVOT

        # EXPLOIT: single stable cluster with high connectivity
        if summary["n_clusters"] <= 1 and summary["persistence_entropy_h0"] < 0.5:
            if fiedler is None or fiedler >= self.fiedler_exploit_threshold:
                return TopologicalRegime.EXPLOIT

        # EXPLORE: multiple clusters, high entropy, or low connectivity
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
    "SpectralFeatures",
    "TopologicalRegime",
    "TopologicalRouter",
]
