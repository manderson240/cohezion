"""Discriminating tests for allocentric journey mapping (user insight 2026-06-06; OVO-S-Bench L4).

`journey_allocentric_map(trajectories)` is the missing L4 of cohezion's agentic-journey spatial
hierarchy: L1 (instantaneous position) / L2 (JourneyTracker 12D trajectory) / L3 (JEPA curvature) exist;
L4 — the GLOBAL geometry of where all journeys live relative to each other in the manifold — did not.
Report-only; operates on injected trajectory vectors (no live tracker, deterministic). The substrate
for novel-physics research on how agents move through the 12D/256D universe.

Each test fails a plausible wrong impl:
  - centroid is not the trajectory mean → test_centroid_is_mean,
  - nearest journey is wrong → test_similar_journeys_are_nearest,
  - a similar pair is farther than a divergent pair → test_pairwise_distance_orders_by_similarity,
  - a single/empty journey crashes or fabricates a neighbour → test_single_and_empty.
"""

from __future__ import annotations

from cohezion.compound.journey_spatial import journey_allocentric_map


def test_centroid_is_mean() -> None:
    m = journey_allocentric_map({"A": [[0.0, 0.0], [2.0, 4.0]]})
    assert m.centroids["A"] == [1.0, 2.0]  # mean of the two positions


def test_similar_journeys_are_nearest() -> None:
    traj = {
        "A": [[0.0, 0.0], [0.0, 0.1]],
        "B": [[0.0, 0.05], [0.0, 0.05]],  # near A
        "C": [[10.0, 10.0], [10.0, 10.0]],  # far
    }
    m = journey_allocentric_map(traj)
    assert m.nearest["A"] == "B"
    assert m.nearest["B"] == "A"
    assert m.nearest["C"] in {"A", "B"}  # C's nearest is one of the cluster, not itself


def test_pairwise_distance_orders_by_similarity() -> None:
    traj = {
        "A": [[0.0, 0.0]],
        "B": [[0.0, 0.1]],  # near A
        "C": [[10.0, 10.0]],  # far from A
    }
    m = journey_allocentric_map(traj)
    ab = m.pairwise_distance[("A", "B")]
    ac = m.pairwise_distance[("A", "C")]
    assert ab < ac  # a similar pair is geometrically closer than a divergent one


def test_single_and_empty() -> None:
    solo = journey_allocentric_map({"A": [[1.0, 1.0]]})
    assert solo.pairwise_distance == {}
    assert solo.nearest["A"] is None  # no other journey → no fabricated neighbour

    empty = journey_allocentric_map({})
    assert empty.centroids == {} and empty.pairwise_distance == {} and empty.nearest == {}


def test_empty_trajectory_journey_skipped() -> None:
    # A journey with NO recorded positions has no centroid → excluded.
    m = journey_allocentric_map({"A": [[1.0]], "B": []})
    assert "B" not in m.centroids
    assert m.nearest["A"] is None
