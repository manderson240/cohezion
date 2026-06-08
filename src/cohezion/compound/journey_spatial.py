"""Spatial awareness over agentic journeys (user insight 2026-06-06; OVO-S-Bench L4) — report-only.

Agentic journeys ARE captured as spatial trajectories in cohezion's manifold (JourneyTracker's 12D
FLUME trajectories; FLUME journey_encoder; the 256D latent). The OVO-S-Bench (arXiv 2606.03890)
hierarchical spatial-reasoning taxonomy maps onto them:
  L1 instantaneous position   → a journey's current FLUME/12D point
  L2 spatiotemporal tracking  → JourneyTracker's recorded 12D trajectory
  L3 spatial simulation       → JEPA ``measure_temporal_straightening`` (trajectory curvature)
  L4 ALLOCENTRIC mapping      → THIS — the global geometry of where ALL journeys live relative to
                                 each other (the gap; nothing computed it before).

This is the substrate for novel-physics research on how agents move through the agentic universe.
Report-only and pure: operates on injected trajectory vectors (no live tracker, no SurrealDB).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from statistics import median

import numpy as np


@dataclass(frozen=True)
class AllocentricMap:
    """The L4 global map of journey-space. All views are report-only."""

    centroids: dict[str, list[float]]  # journey id -> centroid (mean position of its trajectory)
    pairwise_distance: dict[tuple[str, str], float]  # (a, b) a<b -> centroid distance
    nearest: dict[str, str | None]  # journey id -> nearest OTHER journey (None if alone)


def _centroid(trajectory: list) -> np.ndarray:
    return np.asarray([np.asarray(p, dtype=float) for p in trajectory]).mean(axis=0)


def journey_allocentric_map(trajectories: dict[str, list]) -> AllocentricMap:
    """L4 allocentric map: the global geometry of agentic journeys in the manifold (report-only).

    Each non-empty journey → its centroid (mean trajectory position); pairwise centroid distances
    (Euclidean); each journey's nearest OTHER journey. A journey with no recorded positions is
    excluded; a solo journey has no neighbour (``None``). Pure — no I/O, no live tracker.
    """
    ids = [j for j, traj in trajectories.items() if traj]
    centroids = {j: _centroid(trajectories[j]) for j in ids}

    pairwise: dict[tuple[str, str], float] = {}
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            pairwise[(a, b)] = float(np.linalg.norm(centroids[a] - centroids[b]))

    nearest: dict[str, str | None] = {}
    for j in ids:
        others = [(k, float(np.linalg.norm(centroids[j] - centroids[k]))) for k in ids if k != j]
        nearest[j] = min(others, key=lambda t: t[1])[0] if others else None

    return AllocentricMap(
        centroids={j: centroids[j].tolist() for j in ids},
        pairwise_distance=pairwise,
        nearest=nearest,
    )


def _nearest_distance(journey: str, amap: AllocentricMap) -> float | None:
    """The centroid distance from ``journey`` to its nearest OTHER journey (None if it is alone)."""
    neighbour = amap.nearest.get(journey)
    if neighbour is None:
        return None
    pair = (journey, neighbour) if journey < neighbour else (neighbour, journey)
    return amap.pairwise_distance.get(pair)


def journey_novelty(curvatures: Mapping[str, float], allocentric_map: AllocentricMap) -> list[str]:
    """Journeys that are NOVELTY OUTLIERS — high L3 curvature AND high L4 allocentric distance (item 80).

    Composes item-79's :class:`AllocentricMap` (allocentric drift) with an injected per-journey L3
    ``curvatures`` map (egocentric trajectory non-straightness). A journey is flagged NOVEL only when
    it is high on BOTH axes relative to the candidate set's MEDIAN: its curvature ``>`` the median
    curvature (wandering, not straight) AND its nearest-neighbour centroid distance ``>`` the median
    distance (exploring where no other journey sits). The CONJUNCTION is the discriminator — high
    curvature alone = a confused agent; far centroid alone = a translated-but-parallel journey; BOTH =
    genuine novel-region exploration.

    Only journeys present in BOTH ``curvatures`` AND the map (with a computable nearest distance — not
    alone) are candidates; the medians are taken over that candidate set, so a skipped journey never
    shifts the threshold. Empty inputs / no candidates → ``[]``. Report-only — PROPOSES outliers,
    never prunes a journey. Pure (no I/O, no live JEPA).
    """
    nn_distance: dict[str, float] = {}
    for journey in curvatures:
        distance = _nearest_distance(journey, allocentric_map)
        if distance is not None:
            nn_distance[journey] = distance
    if not nn_distance:
        return []
    median_curvature = median(curvatures[j] for j in nn_distance)
    median_distance = median(nn_distance.values())
    return sorted(
        j
        for j in nn_distance
        if curvatures[j] > median_curvature and nn_distance[j] > median_distance
    )
