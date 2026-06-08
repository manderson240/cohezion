"""Item 80: L3×L4 journey-novelty signal — report-only.

`journey_novelty(curvatures, allocentric_map)` flags a journey as a NOVELTY OUTLIER
when it is BOTH high-curvature (above-median L3) AND high-allocentric-distance
(above-median nearest-neighbour distance from item 79).

The conjunction (AND, not OR) is the discriminator:
- High curvature alone = a confused agent wandering within familiar territory (NOT novel).
- Far centroid alone   = a well-directed journey at a new position, same path (NOT novel).
- BOTH                 = genuine novel-region exploration (EVO-analogue signal).

Thresholds are MEDIAN-RELATIVE and STRICT (> not >=), computed fresh over the evaluated
set (the intersection of curvatures and the allocentric map). A journey absent from either
input or with no nearest-neighbour (solo) is excluded from the evaluated set.

Report-only: reads injected data; never mutates state; no I/O.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from cohezion.compound.journey_spatial import AllocentricMap


@dataclass(frozen=True)
class NoveltyReport:
    """Verdict of the L3×L4 novelty conjunction over a set of journeys.

    Attributes:
        novel: Sorted list of journey IDs that are strictly above the median on
               BOTH curvature (L3) AND nearest-neighbour distance (L4).  Empty
               when no journey satisfies both criteria.
    """

    novel: list[str]


def journey_novelty(
    curvatures: dict[str, float],
    allocentric_map: AllocentricMap,
) -> NoveltyReport:
    """Flag journeys that are genuinely novel: above-median curvature AND above-median nn-distance.

    A journey is a NOVELTY OUTLIER when it satisfies BOTH conditions (strict >):
    - **Above-median curvature**: the journey's L3 curvature exceeds the median over
      the evaluated set (journeys present in BOTH inputs with a known nearest-neighbour).
    - **Above-median nn-distance**: the journey's nearest-neighbour allocentric distance
      exceeds the median over the same evaluated set.

    Evaluation set: journeys in the INTERSECTION of ``curvatures`` and
    ``allocentric_map.nearest``, excluding solo journeys (``nearest == None``).
    Journeys absent from either input or solo are SKIPPED entirely (not imputed,
    not treated as at-median — absent).

    Thresholds are STRICT (``> median``, not ``>= median``).  A journey exactly at the
    median on either axis is NOT flagged.

    Args:
        curvatures:      ``{journey_id: L3_curvature_value}`` — injected; no live JEPA call.
        allocentric_map: item-79 :class:`~cohezion.compound.journey_spatial.AllocentricMap`.

    Returns:
        :class:`NoveltyReport` with ``novel`` containing sorted IDs of flagged journeys.
        Returns ``NoveltyReport(novel=[])`` for empty inputs, all-solo maps, or when no
        journey is strictly above both medians.

    Report-only: pure function — no I/O, no state mutation.
    """
    # --- Step 1: build the evaluated set ----------------------------------------
    # A journey must be in BOTH inputs AND must have a nearest-neighbour (not solo).
    qualifying: list[str] = []
    nn_distances: dict[str, float] = {}

    for j in curvatures:
        if j not in allocentric_map.nearest:
            continue  # absent from map → skip
        if allocentric_map.nearest[j] is None:
            continue  # solo journey — no nn-distance, excluded from ranking

        # Extract the nearest-neighbour distance.
        # `pairwise_distance` keys are in insertion order (outer-loop id comes first),
        # NOT sorted alphabetically.  Scan all pairs involving j and take the minimum
        # to be safe regardless of key orientation.
        nn_dist_values = [
            d for (a, b), d in allocentric_map.pairwise_distance.items() if j in (a, b)
        ]
        if not nn_dist_values:
            continue  # map has nearest entry but no pairwise record (should not occur)

        nn_distances[j] = min(nn_dist_values)
        qualifying.append(j)

    if not qualifying:
        return NoveltyReport(novel=[])

    # --- Step 2: compute medians over the evaluated set --------------------------
    curv_median = statistics.median(curvatures[j] for j in qualifying)
    dist_median = statistics.median(nn_distances[j] for j in qualifying)

    # --- Step 3: flag by strict conjunction (> not >=) ---------------------------
    novel_ids = [
        j for j in qualifying if curvatures[j] > curv_median and nn_distances[j] > dist_median
    ]

    return NoveltyReport(novel=sorted(novel_ids))


# ---------------------------------------------------------------------------
# ## FUTURE HOOKS
# ---------------------------------------------------------------------------
# 80b: Expose novelty signal via CompoundExecutor so the DRRGenerator can
#      annotate sessions with NOVELTY_OUTLIER labels for downstream research.
# 80c: Wire into RetrospectionEngine to trigger JEPA surprise re-evaluation
#      for novel journeys (high curvature + isolation = unexplored manifold).
# 80d: Add time-series variant: novelty_trend(windows, allocentric_maps) for
#      tracking novelty evolution across build-loop ticks.
