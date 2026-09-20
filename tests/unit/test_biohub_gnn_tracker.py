"""Unit tests for Biohub SpatiotemporalCellTracker and calibrated Hungarian matching."""

from __future__ import annotations

from cohezion.competitions.biohub_cell.spatiotemporal_gnn import SpatiotemporalCellTracker


class TestBiohubSpatiotemporalTracker:
    def test_default_second_daughter_penalty(self) -> None:
        tracker = SpatiotemporalCellTracker()
        assert tracker.second_daughter_penalty == 0.20
        assert tracker.search_radius_um == 30.0

    def test_single_cell_continuation(self) -> None:
        tracker = SpatiotemporalCellTracker(search_radius_um=20.0)
        c0 = [
            {"id": "cell_0", "centroid": [10.0, 10.0, 10.0], "volume": 100.0, "mean_intensity": 1.0}
        ]
        c1 = [
            {"id": "cell_1", "centroid": [11.0, 10.0, 10.0], "volume": 102.0, "mean_intensity": 1.0}
        ]

        tracks = tracker.resolve_lineage_matching(c0, c1)
        assert len(tracks) == 1
        assert tracks[0]["parent"] == "cell_0"
        assert tracks[0]["child"] == "cell_1"
        assert tracks[0]["type"] == "continuation"

    def test_mitosis_division_detection(self) -> None:
        tracker = SpatiotemporalCellTracker(search_radius_um=20.0, second_daughter_penalty=0.20)
        # One mother cell divides into two daughter cells nearby
        c0 = [
            {
                "id": "mother_0",
                "centroid": [10.0, 10.0, 10.0],
                "volume": 150.0,
                "mean_intensity": 1.0,
            }
        ]
        c1 = [
            {
                "id": "daughter_a",
                "centroid": [12.0, 10.0, 10.0],
                "volume": 75.0,
                "mean_intensity": 1.0,
            },
            {
                "id": "daughter_b",
                "centroid": [10.0, 12.0, 10.0],
                "volume": 75.0,
                "mean_intensity": 1.0,
            },
        ]

        tracks = tracker.resolve_lineage_matching(c0, c1)
        assert len(tracks) == 2
        types = [t["type"] for t in tracks]
        assert "continuation" in types
        assert "division" in types
        parents = {t["parent"] for t in tracks}
        assert parents == {"mother_0"}

    def test_out_of_radius_pruning(self) -> None:
        tracker = SpatiotemporalCellTracker(search_radius_um=5.0)
        c0 = [{"id": "cell_0", "centroid": [0.0, 0.0, 0.0]}]
        c1 = [{"id": "cell_far", "centroid": [50.0, 50.0, 50.0]}]

        tracks = tracker.resolve_lineage_matching(c0, c1)
        assert len(tracks) == 0
