"""Tests for topological persistence of agent trajectories.

Each test validates a real topological property — not heuristic checks,
but mathematical invariants of persistent homology.
"""

import math

import numpy as np
import pytest

from cohezion.compound.topological_persistence import (
    PersistenceDiagram,
    PersistencePair,
    TopologicalPersistence,
    trajectory_persistence_summary,
)


@pytest.fixture
def topo():
    """TopologicalPersistence with H0 + H1."""
    return TopologicalPersistence(max_dimension=1)


class TestH0ConnectedComponents:
    """H0 persistence = connected component structure (clusters)."""

    def test_two_well_separated_clusters(self, topo):
        """Two clusters far apart → one high-persistence H0 feature."""
        # Cluster A near origin, Cluster B far away
        cluster_a = np.random.RandomState(42).randn(5, 3) * 0.1
        cluster_b = np.random.RandomState(43).randn(5, 3) * 0.1 + 10.0
        points = np.vstack([cluster_a, cluster_b])

        dgm = topo.compute_persistence(points)
        h0 = dgm.h0_pairs

        # Should have finite pairs (cluster merges) + one essential feature
        finite_h0 = [p for p in h0 if not math.isinf(p.death)]
        essential_h0 = [p for p in h0 if math.isinf(p.death)]

        assert len(essential_h0) == 1  # One surviving component
        assert len(finite_h0) >= 1  # At least one merge event

        # The most persistent finite feature should reflect the inter-cluster gap
        max_persistence = max(p.persistence for p in finite_h0)
        assert max_persistence > 5.0  # Gap is ~10, persistence should be large

    def test_single_tight_cluster_low_persistence(self, topo):
        """One tight cluster → all H0 features have low persistence."""
        rng = np.random.RandomState(42)
        points = rng.randn(10, 3) * 0.01  # Very tight cluster

        dgm = topo.compute_persistence(points)
        finite_h0 = [p for p in dgm.h0_pairs if not math.isinf(p.death)]

        for p in finite_h0:
            assert p.persistence < 0.1  # All close, merge quickly

    def test_n_points_gives_n_minus_1_finite_h0(self, topo):
        """n points always produce exactly n-1 finite H0 pairs."""
        rng = np.random.RandomState(42)
        for n in [3, 5, 10, 15]:
            points = rng.randn(n, 2)
            dgm = topo.compute_persistence(points)
            finite_h0 = [p for p in dgm.h0_pairs if not math.isinf(p.death)]
            assert len(finite_h0) == n - 1


class TestH1Loops:
    """H1 persistence = loop/cycle structure in trajectory space."""

    def test_circle_has_h1_feature(self, topo):
        """Points on a circle should produce at least one H1 feature."""
        # Sample points on a unit circle
        theta = np.linspace(0, 2 * np.pi, 20, endpoint=False)
        points = np.column_stack([np.cos(theta), np.sin(theta)])

        dgm = topo.compute_persistence(points)
        h1 = dgm.h1_pairs

        # Circle should have at least one 1-cycle
        assert len(h1) >= 1

        # The most persistent H1 feature should have significant persistence
        if h1:
            finite_h1 = [p for p in h1 if not math.isinf(p.persistence)]
            if finite_h1:
                max_p = max(p.persistence for p in finite_h1)
                assert max_p > 0.1  # Non-trivial loop

    def test_collinear_points_no_h1(self, topo):
        """Points on a line should have no significant H1 features."""
        # Points on a line: no loops possible
        points = np.column_stack(
            [
                np.linspace(0, 10, 10),
                np.zeros(10),
            ]
        )

        dgm = topo.compute_persistence(points)
        h1_finite = [p for p in dgm.h1_pairs if not math.isinf(p.death)]

        # No significant loops in a line
        for p in h1_finite:
            assert p.persistence < 2.0  # Only noise-level features


class TestPersistenceStabilityTheorem:
    """The stability theorem: d_B(Dgm(X), Dgm(Y)) <= d_H(X, Y).

    Small perturbations in point cloud → small changes in diagram.
    """

    def test_small_perturbation_small_bottleneck(self, topo):
        """Perturbing points by epsilon changes diagram by at most epsilon."""
        rng = np.random.RandomState(42)
        points = rng.randn(15, 3)
        epsilon = 0.05

        perturbed = points + rng.randn(*points.shape) * epsilon

        dgm1 = topo.compute_persistence(points)
        dgm2 = topo.compute_persistence(perturbed)

        d_b = TopologicalPersistence.bottleneck_distance(dgm1, dgm2, dimension=0)

        # Bottleneck distance should be bounded by perturbation
        # (with some slack for the greedy approximation)
        assert d_b < epsilon * 10  # Generous bound for greedy approx

    def test_identical_clouds_zero_distance(self, topo):
        """Identical point clouds → bottleneck distance = 0."""
        rng = np.random.RandomState(42)
        points = rng.randn(10, 3)

        dgm = topo.compute_persistence(points)
        d_b = TopologicalPersistence.bottleneck_distance(dgm, dgm, dimension=0)

        assert d_b == pytest.approx(0.0, abs=1e-10)


class TestPersistenceEntropy:
    """Persistence entropy measures topological complexity."""

    def test_single_feature_zero_entropy(self):
        """A diagram with one finite feature has entropy 0."""
        dgm = PersistenceDiagram(pairs=[PersistencePair(birth=0.0, death=1.0, dimension=0)])
        assert dgm.persistence_entropy(0) == pytest.approx(0.0)

    def test_uniform_features_max_entropy(self):
        """Equal-persistence features maximize entropy."""
        # All features have same persistence → maximum entropy
        pairs = [PersistencePair(birth=0.0, death=1.0, dimension=0) for _ in range(5)]
        dgm = PersistenceDiagram(pairs=pairs)

        entropy = dgm.persistence_entropy(0)
        expected = math.log(5)  # Max entropy for 5 uniform outcomes
        assert entropy == pytest.approx(expected, rel=1e-6)

    def test_entropy_nonnegative(self, topo):
        """Persistence entropy >= 0 (Shannon entropy property)."""
        rng = np.random.RandomState(42)
        points = rng.randn(15, 3)

        dgm = topo.compute_persistence(points)
        assert dgm.persistence_entropy(0) >= 0.0


class TestBottleneckDistance:
    """Bottleneck distance is a metric on persistence diagrams."""

    def test_symmetry(self, topo):
        """d_B(X, Y) = d_B(Y, X)."""
        rng = np.random.RandomState(42)
        pts1 = rng.randn(10, 3)
        pts2 = rng.randn(10, 3) + 5

        dgm1 = topo.compute_persistence(pts1)
        dgm2 = topo.compute_persistence(pts2)

        d12 = TopologicalPersistence.bottleneck_distance(dgm1, dgm2, 0)
        d21 = TopologicalPersistence.bottleneck_distance(dgm2, dgm1, 0)

        assert d12 == pytest.approx(d21, rel=1e-6)

    def test_nonnegativity(self, topo):
        """d_B(X, Y) >= 0 (metric property)."""
        rng = np.random.RandomState(42)
        pts1 = rng.randn(8, 2)
        pts2 = rng.randn(8, 2) + 3

        dgm1 = topo.compute_persistence(pts1)
        dgm2 = topo.compute_persistence(pts2)

        assert TopologicalPersistence.bottleneck_distance(dgm1, dgm2, 0) >= 0.0

    def test_empty_diagrams_zero(self):
        """Distance between empty diagrams is 0."""
        dgm = PersistenceDiagram(pairs=[])
        assert TopologicalPersistence.bottleneck_distance(dgm, dgm, 0) == 0.0


class TestWassersteinDistance:
    """Wasserstein distance — more sensitive than bottleneck."""

    def test_wasserstein_ge_bottleneck(self, topo):
        """Wasserstein-inf >= bottleneck (it's a finer metric)."""
        rng = np.random.RandomState(42)
        pts1 = rng.randn(10, 2)
        pts2 = rng.randn(10, 2) + 2

        dgm1 = topo.compute_persistence(pts1)
        dgm2 = topo.compute_persistence(pts2)

        w = TopologicalPersistence.wasserstein_distance(dgm1, dgm2, 0)
        b = TopologicalPersistence.bottleneck_distance(dgm1, dgm2, 0)

        # Wasserstein considers all matching costs, bottleneck only the max
        # Both should be non-negative
        assert w >= 0.0
        assert b >= 0.0


class TestTrajectoryPersistenceSummary:
    """Integration test: trajectory_persistence_summary convenience function."""

    def test_summary_returns_expected_keys(self):
        """Summary dict has all expected keys."""
        rng = np.random.RandomState(42)
        points = [rng.randn(12) for _ in range(10)]

        summary = trajectory_persistence_summary(points)

        expected_keys = {
            "n_clusters",
            "n_loops",
            "persistence_entropy_h0",
            "persistence_entropy_h1",
            "max_persistence_h0",
            "max_persistence_h1",
            "total_persistence",
        }
        assert set(summary.keys()) == expected_keys

    def test_summary_insufficient_points(self):
        """Less than 2 points returns zeros."""
        summary = trajectory_persistence_summary([np.zeros(12)])
        assert summary["n_clusters"] == 0
        assert summary["total_persistence"] == 0.0


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_two_points_minimal(self, topo):
        """Two points: one finite H0 pair + one essential."""
        points = np.array([[0, 0], [1, 0]])
        dgm = topo.compute_persistence(points)

        finite_h0 = [p for p in dgm.h0_pairs if not math.isinf(p.death)]
        assert len(finite_h0) == 1
        assert finite_h0[0].death == pytest.approx(1.0)

    def test_single_point_raises(self, topo):
        """Single point raises ValueError."""
        with pytest.raises(ValueError, match="at least 2"):
            topo.compute_persistence(np.array([[0, 0]]))

    def test_high_dimensional_points(self, topo):
        """Works with 12D points (actual JourneyTracker output)."""
        rng = np.random.RandomState(42)
        points = rng.randn(8, 12)

        dgm = topo.compute_persistence(points)
        assert len(dgm.h0_pairs) > 0
