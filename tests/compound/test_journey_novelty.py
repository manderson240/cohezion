"""Item 80: journey novelty signal (report-only, TDD red->green).

`journey_novelty(curvatures, allocentric_map)` flags a journey as a NOVELTY OUTLIER
when it is BOTH high-curvature (above-median L3) AND high-allocentric-distance
(above-median nearest-neighbour distance from item 79).

Each test fails a plausible wrong impl:
  - high-curv-only OR high-dist-only flagged   -> test_conjunction_not_or (main discriminator)
  - journey absent from either input included  -> test_absent_from_curvatures_skipped
  - solo journey (None nn) included            -> test_solo_journey_excluded
  - at-median = above-median                   -> test_at_median_not_flagged
  - empty inputs crash or produce results      -> test_empty_inputs_empty
"""

from __future__ import annotations

from cohezion.compound.journey_spatial import AllocentricMap, journey_allocentric_map
from cohezion.compound.journey_novelty import NoveltyReport, journey_novelty


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _map_from_points(points: dict[str, list[float]]) -> AllocentricMap:
    """Build an AllocentricMap from {id -> [x, y]} single-point trajectories."""
    return journey_allocentric_map({j: [coords] for j, coords in points.items()})


# ---------------------------------------------------------------------------
# Core geometry for the 4-journey discriminating test
#
#   X at (0,0),  Y at (10,0),  Z at (10.1,0),  W at (0,10)
#
#   Nearest-neighbor distances:
#     nn(X)=10.0 (Y or W, HIGH)  nn(Y)=0.1 (Z, LOW)
#     nn(Z)=0.1  (Y, LOW)        nn(W)=10.0 (X, HIGH)
#
#   Curvatures assigned so ONLY X is flagged (conjunction not OR):
#     X=3.0 HIGH,  Y=3.0 HIGH,  Z=1.0 LOW,  W=1.0 LOW
#
#   Medians: curv_median=2.0, dist_median=5.05
#   Flags:   X: curv>med AND dist>med -> YES (only one)
#            Y: curv>med BUT dist<=med -> NO  (kills OR-on-curv impl)
#            Z: curv<=med             -> NO
#            W: curv<=med             -> NO  (kills OR-on-dist impl)
# ---------------------------------------------------------------------------

_FOUR_POINTS = {"X": [0.0, 0.0], "Y": [10.0, 0.0], "Z": [10.1, 0.0], "W": [0.0, 10.0]}
_FOUR_CURVATURES = {"X": 3.0, "Y": 3.0, "Z": 1.0, "W": 1.0}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConjunctionNotOR:
    """The MAIN discriminating test: only the AND conjunction fires, not OR."""

    def test_conjunction_not_or_four_journeys(self) -> None:
        """Only X is high on BOTH axes; Y/Z/W each fail one criterion.

        An OR/sum impl flags X+Y or X+W; the conjunction flags only X.
        """
        almap = _map_from_points(_FOUR_POINTS)
        result = journey_novelty(_FOUR_CURVATURES, almap)
        assert isinstance(result, NoveltyReport)
        assert result.novel == ["X"], (
            f"only X satisfies both high-curvature AND high-nn-distance; got {result.novel}"
        )

    def test_high_curvature_only_not_flagged(self) -> None:
        """A journey with high curvature but below-median nn-distance is not novel."""
        almap = _map_from_points(_FOUR_POINTS)
        result = journey_novelty(_FOUR_CURVATURES, almap)
        assert "Y" not in result.novel, "Y has high curv but low nn-dist; must not be flagged"

    def test_high_nn_distance_only_not_flagged(self) -> None:
        """A journey with high nn-distance but below-median curvature is not novel."""
        almap = _map_from_points(_FOUR_POINTS)
        result = journey_novelty(_FOUR_CURVATURES, almap)
        assert "W" not in result.novel, "W has high nn-dist but low curv; must not be flagged"


class TestThresholds:
    """Strict-greater-than-median semantics."""

    def test_at_median_not_flagged(self) -> None:
        """A journey exactly at the median on either axis is NOT flagged (strict >)."""
        # Two journeys: A far apart, B close. curv_median = 2.5 (mean of 5,0).
        # With only 2 journeys each is the other's nn; nn_dist_median = the common distance.
        # Set A curv=5.0, B curv=0.0 -> median=2.5; neither is strictly above 2.5.
        # Wait -- for 2 journeys only 1 can be 'above median'; let's use 4 again.
        # We want a journey whose curvature == median: use symmetric assignment.
        points = {"A": [0.0, 0.0], "B": [1.0, 0.0], "C": [10.0, 0.0], "D": [11.0, 0.0]}
        almap = _map_from_points(points)
        # curv values: A=3, B=2, C=2, D=3 -> median=(2+2+3+3)/2 median of [2,2,3,3]=2.5?
        # Actually median([2,2,3,3]) = (2+3)/2 = 2.5 -- B and C are below, A and D are above.
        # B and C are AT or below, not "strictly above". nn-dists: nn(A)=1.0,nn(B)=1.0,nn(C)=1.0,nn(D)=1.0
        # nn_median=1.0; nobody is strictly above 1.0.
        curvatures = {"A": 3.0, "B": 2.0, "C": 2.0, "D": 3.0}
        result = journey_novelty(curvatures, almap)
        # All have nn_dist=1.0 which equals median 1.0 -- not strictly above
        assert result.novel == [], (
            f"at-median nn-distance must not fire (strict >); got {result.novel}"
        )

    def test_identical_inputs_empty(self) -> None:
        """When every journey has identical curvature and nn-distance, none is above median."""
        points = {"A": [0.0, 0.0], "B": [1.0, 0.0], "C": [2.0, 0.0]}
        almap = _map_from_points(points)
        curvatures = {"A": 1.0, "B": 1.0, "C": 1.0}
        result = journey_novelty(curvatures, almap)
        assert result.novel == [], f"all-equal -> none strictly above median: {result.novel}"


class TestSkipping:
    """Journeys absent from either input are excluded."""

    def test_absent_from_curvatures_skipped(self) -> None:
        """A journey in the map but not in curvatures is skipped (no imputed curvature)."""
        almap = _map_from_points(_FOUR_POINTS)
        # Omit X from curvatures entirely
        curvatures_without_x = {k: v for k, v in _FOUR_CURVATURES.items() if k != "X"}
        result = journey_novelty(curvatures_without_x, almap)
        assert "X" not in result.novel, "X absent from curvatures must be skipped, not imputed"

    def test_absent_from_map_skipped(self) -> None:
        """A journey in curvatures but not in the allocentric map is skipped."""
        almap = _map_from_points({"A": [0.0, 0.0], "B": [10.0, 0.0]})
        # Z is in curvatures but NOT in the map
        curvatures = {"A": 3.0, "B": 1.0, "Z": 99.0}
        result = journey_novelty(curvatures, almap)
        assert "Z" not in result.novel, "Z absent from map must be skipped"

    def test_solo_journey_excluded(self) -> None:
        """A journey with no nearest-neighbor (None) is excluded from ranking."""
        # Single-journey map -> it is solo (nearest=None)
        almap = _map_from_points({"solo": [5.0, 5.0]})
        result = journey_novelty({"solo": 99.0}, almap)
        assert result.novel == [], "solo journey has no nn-distance; must be excluded"


class TestEdgeCases:
    """Empty and trivial inputs."""

    def test_empty_curvatures_empty(self) -> None:
        almap = _map_from_points({"A": [0.0, 0.0], "B": [1.0, 0.0]})
        assert journey_novelty({}, almap).novel == []

    def test_empty_map_empty(self) -> None:
        result = journey_novelty(
            {"A": 1.0}, AllocentricMap(centroids={}, pairwise_distance={}, nearest={})
        )
        assert result.novel == []

    def test_result_sorted(self) -> None:
        """Novel journey IDs are returned in sorted order."""
        # Two outliers: B (alphabetically after A)
        points = {"A": [0.0, 0.0], "B": [0.5, 0.0], "C": [10.0, 0.0], "D": [20.0, 0.0]}
        almap = _map_from_points(points)
        # C and D are far (high nn-dist); A and B are close
        # D-C distance: 10.0; C-D nearest; A-B distance: 0.5; A-B nearest
        # nn-dists: A=0.5, B=0.5, C=10.0, D=10.0; median=5.25
        # Need C and D to have HIGH curvature to be flagged
        curvatures = {"A": 1.0, "B": 1.0, "C": 3.0, "D": 3.0}
        result = journey_novelty(curvatures, almap)
        # Verify sorted (C before D)
        assert result.novel == sorted(result.novel)
