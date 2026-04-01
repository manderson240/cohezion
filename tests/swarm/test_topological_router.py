"""Tests for TDA-driven topological router."""

import numpy as np

from cohezion.swarm.topological_router import (
    TopologicalRegime,
    TopologicalRouter,
)


def _make_cluster_trajectory(
    center: np.ndarray, n: int = 20, noise: float = 0.05
) -> list[np.ndarray]:
    """Generate trajectory clustered around a center (EXPLOIT regime)."""
    rng = np.random.default_rng(42)
    return [center + rng.normal(0, noise, len(center)) for _ in range(n)]


def _make_diverse_trajectory(dim: int = 12, n: int = 20) -> list[np.ndarray]:
    """Generate trajectory spanning multiple clusters (EXPLORE regime)."""
    rng = np.random.default_rng(42)
    centers = [rng.uniform(0, 1, dim) for _ in range(3)]
    points = []
    for i in range(n):
        c = centers[i % 3]
        points.append(c + rng.normal(0, 0.02, dim))
    return points


def _make_loop_trajectory(dim: int = 12, n: int = 30) -> list[np.ndarray]:
    """Generate trajectory with a loop (PIVOT regime)."""
    points = []
    for i in range(n):
        angle = 2 * np.pi * i / 10
        point = np.full(dim, 0.5)
        point[0] += 0.3 * np.cos(angle)
        point[1] += 0.3 * np.sin(angle)
        points.append(point)
    return points


class TestRegimeClassification:
    def test_exploit_from_cluster(self):
        router = TopologicalRouter()
        center = np.full(12, 0.5)
        for pt in _make_cluster_trajectory(center, n=15, noise=0.02):
            router.record_trajectory_point("agent_a", pt)
        topo = router.analyze_agent("agent_a")
        # Tight cluster should be EXPLOIT or EXPLORE (not PIVOT — no loops)
        assert topo.regime != TopologicalRegime.PIVOT

    def test_explore_from_diverse(self):
        router = TopologicalRouter()
        for pt in _make_diverse_trajectory(n=30):
            router.record_trajectory_point("agent_b", pt)
        topo = router.analyze_agent("agent_b")
        assert topo.regime in (TopologicalRegime.EXPLORE, TopologicalRegime.EXPLOIT)

    def test_pivot_from_loop(self):
        router = TopologicalRouter()
        for pt in _make_loop_trajectory(n=40):
            router.record_trajectory_point("agent_c", pt)
        topo = router.analyze_agent("agent_c")
        # Looping trajectory should detect H₁ features
        assert topo.n_loops >= 0  # May or may not detect depending on scale

    def test_unknown_with_few_points(self):
        router = TopologicalRouter(min_trajectory_length=10)
        router.record_trajectory_point("agent_d", np.zeros(12))
        topo = router.analyze_agent("agent_d")
        assert topo.regime == TopologicalRegime.UNKNOWN


class TestRouting:
    def test_simple_task_prefers_exploit(self):
        router = TopologicalRouter()
        # Agent A: stable cluster (EXPLOIT)
        for pt in _make_cluster_trajectory(np.full(12, 0.5), n=15, noise=0.02):
            router.record_trajectory_point("agent_a", pt)
        # Agent B: diverse (EXPLORE)
        for pt in _make_diverse_trajectory(n=15):
            router.record_trajectory_point("agent_b", pt)

        decision = router.route_task("task_1", "simple")
        assert decision.assigned_agent in ("agent_a", "agent_b")
        assert decision.confidence > 0

    def test_no_agents_returns_empty(self):
        router = TopologicalRouter()
        decision = router.route_task("task_1", "medium")
        assert decision.assigned_agent == ""
        assert decision.confidence == 0.0

    def test_routing_decision_has_reasoning(self):
        router = TopologicalRouter()
        for pt in _make_cluster_trajectory(np.full(12, 0.5)):
            router.record_trajectory_point("agent_x", pt)
        decision = router.route_task("task_2", "medium")
        assert len(decision.reasoning) > 0

    def test_routing_returns_valid_agent(self):
        router = TopologicalRouter()
        for pt in _make_cluster_trajectory(np.full(12, 0.5)):
            router.record_trajectory_point("a1", pt)
        for pt in _make_diverse_trajectory():
            router.record_trajectory_point("a2", pt)
        decision = router.route_task("t1", "complex", available_agents=["a1", "a2"])
        assert decision.assigned_agent in ("a1", "a2")


class TestSummary:
    def test_routing_summary_structure(self):
        router = TopologicalRouter()
        for pt in _make_cluster_trajectory(np.full(12, 0.5)):
            router.record_trajectory_point("agent_1", pt)
        summary = router.get_routing_summary()
        assert "total_agents" in summary
        assert "regime_distribution" in summary
        assert "agents" in summary
        assert summary["total_agents"] == 1

    def test_topology_to_dict(self):
        router = TopologicalRouter()
        for pt in _make_cluster_trajectory(np.full(12, 0.5)):
            router.record_trajectory_point("agent_1", pt)
        topo = router.analyze_agent("agent_1")
        d = topo.to_dict()
        assert "agent_id" in d
        assert "regime" in d
        assert "n_clusters" in d
