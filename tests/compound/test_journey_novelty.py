"""Discriminating tests for journey_novelty (backlog item 80, 2026-06-08).

`journey_novelty(curvatures, allocentric_map)` flags a journey as a NOVELTY OUTLIER only when it is
high on BOTH axes relative to the candidate-set median: L3 curvature (wandering) AND L4 allocentric
nearest-neighbour distance (exploring novel regions). The CONJUNCTION is the discriminator. Report-
only, pure over an injected curvature map + item-79 AllocentricMap.

Each test fails a plausible wrong impl:
  - an impl that ORs / sums the two axes flags single-axis journeys → test_conjunction_not_or,
  - an impl using only curvature → test_conjunction_not_or (E would be flagged),
  - an impl using only distance → test_conjunction_not_or (A would be flagged),
  - an impl that counts a journey absent from one input → test_absent_journey_skipped.
"""

from __future__ import annotations

from collections.abc import Mapping

from cohezion.compound.journey_spatial import AllocentricMap, journey_novelty


def _map(nn_distance: Mapping[str, float]) -> AllocentricMap:
    # Build an AllocentricMap whose each journey's nearest distance is exactly nn_distance[j].
    # Pair every journey with a shared sentinel "_anchor" at the desired distance.
    nearest: dict[str, str | None] = dict.fromkeys(nn_distance, "_anchor")
    nearest["_anchor"] = next(iter(nn_distance), None)
    pairwise: dict[tuple[str, str], float] = {}
    for j, d in nn_distance.items():
        pair = (j, "_anchor") if j < "_anchor" else ("_anchor", j)
        pairwise[pair] = d
    return AllocentricMap(centroids={}, pairwise_distance=pairwise, nearest=nearest)


def test_conjunction_not_or() -> None:
    # 6 journeys; curvature and distance are inversely correlated EXCEPT F which is high on both.
    # medians (over A..F): curvature 3.5, distance 3.5.
    curvatures = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}
    nn = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1, "F": 6}
    out = journey_novelty(curvatures, _map(nn))
    # Only F is above the median on BOTH axes. E (high curv, low dist) and A (low curv, high dist)
    # are each high on only ONE axis → an OR/sum or single-axis impl would wrongly include them.
    assert out == ["F"]


def test_high_curvature_alone_not_flagged() -> None:
    # E: highest curvature but lowest distance → not novel (confused agent, not explorer).
    curvatures = {"A": 1, "B": 2, "E": 9}
    nn = {"A": 9, "B": 2, "E": 1}  # E has the LOWEST distance
    assert "E" not in journey_novelty(curvatures, _map(nn))


def test_far_centroid_alone_not_flagged() -> None:
    # A: farthest centroid but lowest curvature → translated-but-parallel, not novel.
    curvatures = {"A": 1, "B": 5, "C": 9}
    nn = {"A": 99, "B": 5, "C": 1}
    assert "A" not in journey_novelty(curvatures, _map(nn))


def test_absent_journey_skipped() -> None:
    # A journey in curvatures but NOT in the map (no nearest) is skipped and does not shift medians.
    curvatures = {"A": 1, "B": 2, "F": 6, "GHOST": 100}  # GHOST absent from the map
    nn = {"A": 2, "B": 1, "F": 6}
    out = journey_novelty(curvatures, _map(nn))
    assert "GHOST" not in out
    # Over candidates {A,B,F}: median curv 2, median dist 2 → F (6>2 and 6>2) flagged.
    assert out == ["F"]


def test_alone_journey_skipped() -> None:
    # A journey whose nearest is None (alone) has no computable distance → skipped.
    amap = AllocentricMap(centroids={}, pairwise_distance={}, nearest={"solo": None})
    assert journey_novelty({"solo": 99.0}, amap) == []


def test_empty_inputs() -> None:
    empty = AllocentricMap(centroids={}, pairwise_distance={}, nearest={})
    assert journey_novelty({}, empty) == []


def test_single_journey_not_flagged() -> None:
    # One candidate → its own value is the median → not strictly greater → not flagged.
    out = journey_novelty({"only": 5.0}, _map({"only": 5.0}))
    assert out == []
