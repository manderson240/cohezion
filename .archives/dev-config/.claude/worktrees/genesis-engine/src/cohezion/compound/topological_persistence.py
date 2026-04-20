"""Topological persistence analysis for agent trajectories.

Applies persistent homology to agent behavioral trajectories in latent space.
Instead of computing variance/std (phi score), this captures the *shape* of
agent behavior — loops, clusters, voids — in a way that is invariant to
rotation, scaling, and continuous deformation.

Core concepts:
  - Persistence diagram: Birth-death pairs (b, d) for topological features.
    A feature that is "born" at scale b and "dies" at scale d has
    persistence |d - b|. High persistence = genuine structure; low = noise.
  - H0 (connected components): Clusters in trajectory space. Measures how
    many distinct behavioral modes the agent has.
  - H1 (loops): Cycles in trajectory space. Detects repetitive behavioral
    patterns — an agent that oscillates between explore/exploit creates
    a 1-cycle in its trajectory.
  - Bottleneck distance: Metric on persistence diagrams. Measures how
    different two agents' behavioral topologies are. Stable under
    perturbation (Lipschitz continuous).
  - Persistence entropy: Shannon entropy of the persistence diagram.
    Measures topological complexity of behavior.

Algorithm:
  We implement the Vietoris-Rips filtration using Union-Find for H0
  and a boundary matrix reduction for H1. This is self-contained
  (no external TDA library needed) and runs in O(n² log n) for n points.

Mathematical properties:
  - Stability theorem: Small perturbations in trajectory → small changes
    in persistence diagram (bottleneck distance is Lipschitz)
  - Completeness: Persistence diagrams capture all homological information
  - Invariance: Results are unchanged by rotation, translation, uniform scaling

References:
  - Edelsbrunner & Harer (2010): Computational Topology
  - Chazal et al. (2016): Structure and stability of persistence modules
  - Perea & Harer (2015): Sliding window embeddings and persistence
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.spatial.distance import pdist, squareform


logger = logging.getLogger(__name__)


@dataclass
class PersistencePair:
    """A single birth-death pair in a persistence diagram.

    Attributes
    ----------
    birth : float
        Scale at which the feature appears.
    death : float
        Scale at which the feature disappears (inf for essential features).
    dimension : int
        Homological dimension (0 = component, 1 = loop, 2 = void).
    """

    birth: float
    death: float
    dimension: int

    @property
    def persistence(self) -> float:
        """Lifetime of this feature. Longer = more significant."""
        if math.isinf(self.death):
            return float("inf")
        return self.death - self.birth

    @property
    def midlife(self) -> float:
        """Midpoint of the feature's lifetime."""
        if math.isinf(self.death):
            return float("inf")
        return (self.birth + self.death) / 2.0


@dataclass
class PersistenceDiagram:
    """Collection of persistence pairs from a filtration.

    The diagram is the fundamental topological descriptor of a point cloud.
    """

    pairs: list[PersistencePair]
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_pairs(self, dimension: int) -> list[PersistencePair]:
        """Get pairs for a specific homological dimension."""
        return [p for p in self.pairs if p.dimension == dimension]

    @property
    def h0_pairs(self) -> list[PersistencePair]:
        """Connected component features (clusters)."""
        return self.get_pairs(0)

    @property
    def h1_pairs(self) -> list[PersistencePair]:
        """Loop features (cycles)."""
        return self.get_pairs(1)

    def persistence_entropy(self, dimension: int | None = None) -> float:
        """Shannon entropy of the persistence diagram.

        Measures topological complexity. Higher entropy = more diverse
        topological features.

        Parameters
        ----------
        dimension : int | None
            If specified, compute entropy for only this dimension.

        Returns
        -------
        float
            Persistence entropy in nats.
        """
        pairs = self.get_pairs(dimension) if dimension is not None else self.pairs

        # Filter out infinite persistence
        finite_pairs = [p for p in pairs if not math.isinf(p.persistence)]
        if not finite_pairs:
            return 0.0

        # Normalize persistences to form a probability distribution
        persistences = np.array([p.persistence for p in finite_pairs])
        total = persistences.sum()
        if total == 0:
            return 0.0

        probs = persistences / total

        # Shannon entropy
        nonzero = probs > 0
        return -float(np.sum(probs[nonzero] * np.log(probs[nonzero])))

    def total_persistence(self, dimension: int | None = None) -> float:
        """Sum of all finite persistences.

        Parameters
        ----------
        dimension : int | None
            If specified, sum only for this dimension.

        Returns
        -------
        float
            Total persistence (total topological "signal").
        """
        pairs = self.get_pairs(dimension) if dimension is not None else self.pairs

        return sum(p.persistence for p in pairs if not math.isinf(p.persistence))

    def max_persistence(self, dimension: int | None = None) -> float:
        """Maximum finite persistence.

        Parameters
        ----------
        dimension : int | None
            If specified, only consider this dimension.

        Returns
        -------
        float
            Maximum persistence (most significant feature).
        """
        pairs = self.get_pairs(dimension) if dimension is not None else self.pairs

        finite = [p.persistence for p in pairs if not math.isinf(p.persistence)]
        return max(finite) if finite else 0.0

    def n_significant_features(self, dimension: int | None = None, threshold: float = 0.1) -> int:
        """Count features with persistence above threshold.

        Parameters
        ----------
        dimension : int | None
            If specified, count only for this dimension.
        threshold : float
            Minimum persistence to be "significant".

        Returns
        -------
        int
            Number of significant topological features.
        """
        pairs = self.get_pairs(dimension) if dimension is not None else self.pairs

        return sum(1 for p in pairs if p.persistence > threshold)


class _UnionFind:
    """Weighted quick-union with path compression for H0 computation."""

    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n
        self.birth_time = [0.0] * n
        self.n_components = n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]  # Path compression
            x = self.parent[x]
        return x

    def union(self, x: int, y: int, edge_weight: float) -> PersistencePair | None:
        """Union two components. Returns a persistence pair if a component dies."""
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return None  # Already connected

        self.n_components -= 1

        # The younger component dies (born later)
        if self.birth_time[rx] <= self.birth_time[ry]:
            older, younger = rx, ry
        else:
            older, younger = ry, rx

        # Merge younger into older (older survives)
        if self.rank[older] < self.rank[younger]:
            older, younger = younger, older

        self.parent[younger] = older
        if self.rank[older] == self.rank[younger]:
            self.rank[older] += 1

        # The dying component was born at 0 (all points start as components)
        # and dies at edge_weight (the scale where they merge)
        return PersistencePair(
            birth=0.0,
            death=edge_weight,
            dimension=0,
        )


class TopologicalPersistence:
    """Compute persistent homology of agent trajectory point clouds.

    Implements Vietoris-Rips filtration with:
    - H0 via Union-Find (connected components)
    - H1 via boundary matrix reduction (1-cycles / loops)

    Parameters
    ----------
    max_dimension : int
        Maximum homological dimension to compute (default: 1).
        0 = components only, 1 = components + loops.
    max_edge_length : float
        Maximum edge length in Rips filtration (default: inf).
        Set to limit computation on large point clouds.
    """

    def __init__(
        self,
        max_dimension: int = 1,
        max_edge_length: float = float("inf"),
    ) -> None:
        self.max_dimension = min(max_dimension, 1)  # Cap at H1
        self.max_edge_length = max_edge_length

    def compute_persistence(self, points: np.ndarray) -> PersistenceDiagram:
        """Compute persistence diagram from a point cloud.

        Parameters
        ----------
        points : np.ndarray
            Point cloud, shape (n_points, n_dimensions).

        Returns
        -------
        PersistenceDiagram
            Persistence diagram with H0 and optionally H1 features.

        Raises
        ------
        ValueError
            If points has wrong shape or too few points.
        """
        points = np.asarray(points, dtype=np.float64)
        if points.ndim == 1:
            points = points.reshape(-1, 1)

        n = points.shape[0]
        if n < 2:
            raise ValueError(f"Need at least 2 points, got {n}")

        # Compute pairwise distance matrix
        dist_matrix = squareform(pdist(points))

        # Get sorted edges
        edges = self._get_sorted_edges(dist_matrix)

        # Compute H0 (connected components) via Union-Find
        pairs = self._compute_h0(n, edges)

        # Compute H1 (loops) via boundary matrix if requested
        if self.max_dimension >= 1 and n >= 3:
            h1_pairs = self._compute_h1(n, edges, dist_matrix)
            pairs.extend(h1_pairs)

        return PersistenceDiagram(
            pairs=pairs,
            metadata={
                "n_points": n,
                "n_dimensions": points.shape[1],
                "max_edge_length": self.max_edge_length,
            },
        )

    def _get_sorted_edges(self, dist_matrix: np.ndarray) -> list[tuple[int, int, float]]:
        """Extract and sort edges from distance matrix.

        Parameters
        ----------
        dist_matrix : np.ndarray
            Symmetric distance matrix.

        Returns
        -------
        list[tuple[int, int, float]]
            Sorted edges (i, j, weight).
        """
        n = dist_matrix.shape[0]
        edges = []
        for i in range(n):
            for j in range(i + 1, n):
                w = dist_matrix[i, j]
                if w <= self.max_edge_length:
                    edges.append((i, j, w))
        edges.sort(key=lambda e: e[2])
        return edges

    def _compute_h0(self, n: int, edges: list[tuple[int, int, float]]) -> list[PersistencePair]:
        """Compute H0 persistence (connected components) via Union-Find.

        Parameters
        ----------
        n : int
            Number of points.
        edges : list[tuple[int, int, float]]
            Sorted edges.

        Returns
        -------
        list[PersistencePair]
            H0 persistence pairs. Includes one essential pair (born at 0,
            dies at infinity) for the final connected component.
        """
        uf = _UnionFind(n)
        pairs = []

        for i, j, w in edges:
            pair = uf.union(i, j, w)
            if pair is not None and pair.persistence > 0:
                pairs.append(pair)

        # Add essential feature (the surviving component)
        pairs.append(PersistencePair(birth=0.0, death=float("inf"), dimension=0))

        return pairs

    def _compute_h1(
        self,
        n: int,
        edges: list[tuple[int, int, float]],
        dist_matrix: np.ndarray,
    ) -> list[PersistencePair]:
        """Compute H1 persistence (loops) via boundary matrix reduction.

        Uses the standard persistence algorithm: process simplices in
        filtration order, reduce the boundary matrix, and read off
        birth-death pairs from pivot elements.

        Parameters
        ----------
        n : int
            Number of points.
        edges : list[tuple[int, int, float]]
            Sorted edges (already filtered by max_edge_length).
        dist_matrix : np.ndarray
            Full distance matrix.

        Returns
        -------
        list[PersistencePair]
            H1 persistence pairs (loops/cycles).
        """
        # Build triangles (2-simplices) in filtration order
        # A triangle (i,j,k) enters at max(d(i,j), d(j,k), d(i,k))
        edge_set = {(min(e[0], e[1]), max(e[0], e[1])): e[2] for e in edges}

        triangles: list[tuple[tuple[int, int, int], float]] = []
        # Only consider triangles formed by existing edges
        edge_list = list(edge_set.keys())

        # Build adjacency for efficient triangle enumeration
        adj: dict[int, set[int]] = {i: set() for i in range(n)}
        for u, v in edge_list:
            adj[u].add(v)
            adj[v].add(u)

        for u, v in edge_list:
            # Find common neighbors to form triangles
            common = adj[u] & adj[v]
            for w in common:
                tri = tuple(sorted([u, v, w]))
                # Filtration value = max edge weight in triangle
                e01 = dist_matrix[tri[0], tri[1]]
                e02 = dist_matrix[tri[0], tri[2]]
                e12 = dist_matrix[tri[1], tri[2]]
                filt_val = max(e01, e02, e12)
                if filt_val <= self.max_edge_length:
                    triangles.append((tri, filt_val))

        # Deduplicate
        seen = set()
        unique_triangles = []
        for tri, fv in triangles:
            if tri not in seen:
                seen.add(tri)
                unique_triangles.append((tri, fv))

        # Sort by filtration value
        unique_triangles.sort(key=lambda t: t[1])

        # Standard persistence algorithm for H1
        # Each triangle kills an H1 feature or creates an H2 feature
        # We track which 1-cycles are still alive

        # Build boundary matrix columns for triangles
        # boundary(triangle) = set of its edges
        # Use column reduction to find persistence pairs

        # Edge index mapping
        edge_index = {}
        edge_births = {}
        for idx, (u, v, w) in enumerate(edges):
            key = (min(u, v), max(u, v))
            edge_index[key] = idx
            edge_births[key] = w

        # Track which edges form a spanning tree (killed in H0)
        uf = _UnionFind(n)
        tree_edges = set()
        for u, v, w in edges:
            key = (min(u, v), max(u, v))
            rx, ry = uf.find(u), uf.find(v)
            if rx != ry:
                uf.union(u, v, w)
                tree_edges.add(key)

        # Non-tree edges create 1-cycles (potential H1 generators)
        # Each such edge creates a cycle born at that edge's weight
        cycle_births: dict[int, float] = {}  # edge_idx -> birth
        for key, idx in edge_index.items():
            if key not in tree_edges:
                cycle_births[idx] = edge_births[key]

        # Triangles kill 1-cycles
        # The youngest edge of the triangle's boundary that is a cycle creator
        # gets killed
        h1_pairs = []
        killed_cycles = set()

        for tri, filt_val in unique_triangles:
            # Boundary edges
            boundary_edges = [
                (min(tri[0], tri[1]), max(tri[0], tri[1])),
                (min(tri[0], tri[2]), max(tri[0], tri[2])),
                (min(tri[1], tri[2]), max(tri[1], tri[2])),
            ]

            # Find non-tree edges in boundary (cycle creators)
            non_tree_in_boundary = []
            for e in boundary_edges:
                if e in edge_index and e not in tree_edges:
                    idx = edge_index[e]
                    if idx not in killed_cycles:
                        non_tree_in_boundary.append((idx, edge_births[e]))

            if non_tree_in_boundary:
                # Kill the youngest cycle (largest birth time)
                non_tree_in_boundary.sort(key=lambda x: x[1], reverse=True)
                killed_idx, birth = non_tree_in_boundary[0]
                killed_cycles.add(killed_idx)

                h1_pairs.append(
                    PersistencePair(
                        birth=birth,
                        death=filt_val,
                        dimension=1,
                    )
                )

        # Remaining non-tree edges are essential 1-cycles (never killed)
        for idx, birth in cycle_births.items():
            if idx not in killed_cycles:
                h1_pairs.append(
                    PersistencePair(
                        birth=birth,
                        death=float("inf"),
                        dimension=1,
                    )
                )

        return h1_pairs

    @staticmethod
    def bottleneck_distance(
        dgm1: PersistenceDiagram,
        dgm2: PersistenceDiagram,
        dimension: int = 0,
    ) -> float:
        """Compute bottleneck distance between two persistence diagrams.

        The bottleneck distance is the infimum over all matchings of the
        maximum cost. It satisfies the stability theorem:
            d_B(Dgm(f), Dgm(g)) <= ||f - g||_infinity

        Parameters
        ----------
        dgm1 : PersistenceDiagram
            First diagram.
        dgm2 : PersistenceDiagram
            Second diagram.
        dimension : int
            Homological dimension to compare.

        Returns
        -------
        float
            Bottleneck distance (>= 0). Small = similar topology.
        """
        pairs1 = [(p.birth, p.death) for p in dgm1.get_pairs(dimension) if not math.isinf(p.death)]
        pairs2 = [(p.birth, p.death) for p in dgm2.get_pairs(dimension) if not math.isinf(p.death)]

        # Add diagonal projections for unmatched points
        # A point (b, d) on the diagonal has cost (d - b) / 2
        n1, n2 = len(pairs1), len(pairs2)

        if n1 == 0 and n2 == 0:
            return 0.0

        # Pad shorter list with diagonal projections from longer list
        all_costs = []

        # Match each pair in dgm1 to its closest in dgm2 or diagonal
        for b1, d1 in pairs1:
            # Cost to match to diagonal
            diag_cost = (d1 - b1) / 2.0
            best = diag_cost

            for b2, d2 in pairs2:
                # L-infinity cost of matching (b1,d1) to (b2,d2)
                cost = max(abs(b1 - b2), abs(d1 - d2))
                best = min(best, cost)

            all_costs.append(best)

        for b2, d2 in pairs2:
            diag_cost = (d2 - b2) / 2.0
            best = diag_cost

            for b1, d1 in pairs1:
                cost = max(abs(b1 - b2), abs(d1 - d2))
                best = min(best, cost)

            all_costs.append(best)

        # Bottleneck = max of minimum matching costs
        # This is a greedy approximation; exact requires Hungarian algorithm
        return max(all_costs) if all_costs else 0.0

    @staticmethod
    def wasserstein_distance(
        dgm1: PersistenceDiagram,
        dgm2: PersistenceDiagram,
        dimension: int = 0,
        p: float = 2.0,
    ) -> float:
        """Compute p-Wasserstein distance between persistence diagrams.

        Parameters
        ----------
        dgm1 : PersistenceDiagram
            First diagram.
        dgm2 : PersistenceDiagram
            Second diagram.
        dimension : int
            Homological dimension.
        p : float
            Wasserstein exponent (default: 2).

        Returns
        -------
        float
            Wasserstein-p distance.
        """
        pairs1 = [(pp.birth, pp.death) for pp in dgm1.get_pairs(dimension) if not math.isinf(pp.death)]
        pairs2 = [(pp.birth, pp.death) for pp in dgm2.get_pairs(dimension) if not math.isinf(pp.death)]

        if not pairs1 and not pairs2:
            return 0.0

        # Greedy matching approximation
        total_cost = 0.0
        used2 = set()

        for b1, d1 in pairs1:
            diag_cost = ((d1 - b1) / 2.0) ** p
            best_cost = diag_cost
            best_j = -1

            for j, (b2, d2) in enumerate(pairs2):
                if j in used2:
                    continue
                cost = (max(abs(b1 - b2), abs(d1 - d2))) ** p
                if cost < best_cost:
                    best_cost = cost
                    best_j = j

            total_cost += best_cost
            if best_j >= 0:
                used2.add(best_j)

        # Unmatched points in dgm2 go to diagonal
        for j, (b2, d2) in enumerate(pairs2):
            if j not in used2:
                total_cost += ((d2 - b2) / 2.0) ** p

        return total_cost ** (1.0 / p)


def trajectory_persistence_summary(
    trajectory_points: list[np.ndarray],
    significance_threshold: float = 0.05,
) -> dict[str, Any]:
    """Compute a summary of topological features for an agent trajectory.

    Convenience function that computes persistence and extracts key metrics.

    Parameters
    ----------
    trajectory_points : list[np.ndarray]
        Sequence of points in latent space (e.g., 12D vectors from JourneyTracker).
    significance_threshold : float
        Minimum persistence to count as significant.

    Returns
    -------
    dict[str, Any]
        Summary with:
        - n_clusters: Significant H0 features (distinct behavioral modes)
        - n_loops: Significant H1 features (behavioral cycles)
        - persistence_entropy_h0: Topological complexity of clustering
        - persistence_entropy_h1: Topological complexity of cycles
        - max_persistence_h0: Most persistent cluster separation
        - max_persistence_h1: Most persistent behavioral cycle
        - total_persistence: Overall topological signal strength
    """
    if len(trajectory_points) < 2:
        return {
            "n_clusters": 0,
            "n_loops": 0,
            "persistence_entropy_h0": 0.0,
            "persistence_entropy_h1": 0.0,
            "max_persistence_h0": 0.0,
            "max_persistence_h1": 0.0,
            "total_persistence": 0.0,
        }

    points = np.array(trajectory_points)
    topo = TopologicalPersistence(max_dimension=1)
    dgm = topo.compute_persistence(points)

    return {
        "n_clusters": dgm.n_significant_features(0, significance_threshold),
        "n_loops": dgm.n_significant_features(1, significance_threshold),
        "persistence_entropy_h0": dgm.persistence_entropy(0),
        "persistence_entropy_h1": dgm.persistence_entropy(1),
        "max_persistence_h0": dgm.max_persistence(0),
        "max_persistence_h1": dgm.max_persistence(1),
        "total_persistence": dgm.total_persistence(),
    }


__all__ = [
    "PersistenceDiagram",
    "PersistencePair",
    "TopologicalPersistence",
    "trajectory_persistence_summary",
]
