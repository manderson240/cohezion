"""Tests for CapabilityScorecard, RadarChart, and LongitudinalTracker."""

from __future__ import annotations

import pytest


class TestRadarChart:
    """Tests for RadarChart."""

    @pytest.mark.fast
    def test_initialization(self):
        """Test RadarChart initializes with correct axes."""
        from cohezion.eval.capability_scorecard import RadarChart

        chart = RadarChart()
        assert len(chart.AXES) == 6
        assert "HIHO Coherence" in chart.AXES
        assert "TRIUNE Balance" in chart.AXES
        assert len(chart.MAX_VALUES) == 6

    @pytest.mark.fast
    def test_plot_with_wrong_number_of_values(self):
        """Test plot raises ValueError with wrong number of values."""
        from cohezion.eval.capability_scorecard import RadarChart

        chart = RadarChart()
        with pytest.raises(ValueError):
            chart.plot([0.5, 0.6])

    @pytest.mark.fast
    def test_plot_with_six_values(self):
        """Test plot works with six values."""
        from cohezion.eval.capability_scorecard import RadarChart

        chart = RadarChart()
        result = chart.plot([0.8, 0.7, 0.9, 0.6, 0.85, 0.75])
        assert result is not None


class TestLongitudinalTracker:
    """Tests for LongitudinalTracker."""

    @pytest.mark.fast
    def test_initialization(self):
        """Test LongitudinalTracker initializes empty."""
        from cohezion.eval.capability_scorecard import LongitudinalTracker

        tracker = LongitudinalTracker()
        summary = tracker.get_trend_summary()
        assert "error" in summary

    @pytest.mark.fast
    def test_record(self):
        """Test recording a run."""
        from cohezion.eval.capability_scorecard import LongitudinalTracker

        tracker = LongitudinalTracker()
        tracker.record("run_1", {"coherence": 0.8, "stability": 0.7})
        summary = tracker.get_trend_summary()
        assert "error" in summary

    @pytest.mark.fast
    def test_record_multiple(self):
        """Test recording multiple runs for trend."""
        from cohezion.eval.capability_scorecard import LongitudinalTracker

        tracker = LongitudinalTracker()
        tracker.record("run_1", {"coherence": 0.8, "stability": 0.7})
        tracker.record("run_2", {"coherence": 0.85, "stability": 0.72})
        summary = tracker.get_trend_summary()
        assert "error" not in summary

    @pytest.mark.fast
    def test_get_weakest_axis_single_run(self):
        """Test get_weakest_axis with single run."""
        from cohezion.eval.capability_scorecard import LongitudinalTracker

        tracker = LongitudinalTracker()
        tracker.record("run_1", {"coherence": 0.8})
        weakest = tracker.get_weakest_axis()
        assert weakest == "coherence"

    @pytest.mark.fast
    def test_get_strongest_axis_single_run(self):
        """Test get_strongest_axis with single run."""
        from cohezion.eval.capability_scorecard import LongitudinalTracker

        tracker = LongitudinalTracker()
        tracker.record("run_1", {"coherence": 0.8})
        strongest = tracker.get_strongest_axis()
        assert strongest == "coherence"


class TestCapabilityScorecard:
    """Tests for CapabilityScorecard."""

    @pytest.mark.fast
    def test_initialization(self):
        """Test CapabilityScorecard initializes correctly."""
        from cohezion.eval.capability_scorecard import CapabilityScorecard

        scorecard = CapabilityScorecard()
        report = scorecard.generate_report()
        assert "error" in report

    @pytest.mark.fast
    def test_record_run(self):
        """Test recording a run."""
        from cohezion.eval.capability_scorecard import CapabilityScorecard

        scorecard = CapabilityScorecard()
        scorecard.record_run(
            "run_1",
            [{"coherence": 0.8, "reward": 1.0, "success": True}],
            [],
        )
        report = scorecard.generate_report()
        assert "latest_run" in report
        assert report["total_runs"] == 1

    @pytest.mark.fast
    def test_record_run_with_biography(self):
        """Test recording a run with biography data."""
        from cohezion.eval.capability_scorecard import CapabilityScorecard

        scorecard = CapabilityScorecard()
        bio = [
            {
                "biography": [
                    {"coherence": 0.8, "exotic_charge_density": 0.9, "phase": 1.0},
                    {"coherence": 0.85, "exotic_charge_density": 0.92, "phase": 1.1},
                ]
            }
        ]
        scorecard.record_run(
            "run_1",
            [{"coherence": 0.8, "reward": 1.0, "success": True}],
            bio,
        )
        report = scorecard.generate_report()
        assert report["total_runs"] == 1

    @pytest.mark.fast
    def test_generate_report(self):
        """Test generate_report."""
        from cohezion.eval.capability_scorecard import CapabilityScorecard

        scorecard = CapabilityScorecard()
        scorecard.record_run(
            "run_1",
            [
                {"coherence": 0.8, "reward": 1.0, "success": True},
                {"coherence": 0.75, "reward": 0.8, "success": False},
            ],
            [],
        )
        report = scorecard.generate_report()
        assert "latest_run" in report
        assert report["total_runs"] == 1
        assert "latest" in report
        assert "longitudinal" in report

    @pytest.mark.fast
    def test_plot_radar(self):
        """Test plot_radar."""
        from cohezion.eval.capability_scorecard import CapabilityScorecard

        scorecard = CapabilityScorecard()
        scorecard.record_run(
            "run_1",
            [{"coherence": 0.8, "reward": 1.0, "success": True}],
            [],
        )
        fig = scorecard.plot_radar("run_1")
        assert fig is not None

    @pytest.mark.fast
    def test_compare_runs(self):
        """Test compare_runs."""
        from cohezion.eval.capability_scorecard import CapabilityScorecard

        scorecard = CapabilityScorecard()
        scorecard.record_run(
            "run_1",
            [
                {"coherence": 0.8, "reward": 1.0, "success": True},
                {"coherence": 0.85, "reward": 1.0, "success": True},
            ],
            [],
        )
        scorecard.record_run(
            "run_2",
            [
                {"coherence": 0.6, "reward": 0.5, "success": False},
                {"coherence": 0.65, "reward": 0.6, "success": False},
            ],
            [],
        )
        comparisons = scorecard.compare_runs("run_1", "run_2")
        assert len(comparisons) == 6

    @pytest.mark.fast
    def test_compare_runs_not_found(self):
        """Test compare_runs raises on missing run IDs."""
        from cohezion.eval.capability_scorecard import CapabilityScorecard

        scorecard = CapabilityScorecard()
        with pytest.raises(ValueError):
            scorecard.compare_runs("nonexistent_1", "nonexistent_2")

    @pytest.mark.fast
    def test_export_json(self, tmp_path):
        """Test export_json and import_json."""
        from cohezion.eval.capability_scorecard import CapabilityScorecard

        scorecard = CapabilityScorecard()
        scorecard.record_run(
            "run_1",
            [{"coherence": 0.8, "reward": 1.0, "success": True}],
            [],
        )
        export_path = tmp_path / "scorecard.json"
        scorecard.export_json(export_path)
        assert export_path.exists()

    @pytest.mark.fast
    def test_import_json(self, tmp_path):
        """Test import_json."""
        from cohezion.eval.capability_scorecard import CapabilityScorecard

        scorecard = CapabilityScorecard()
        scorecard.record_run(
            "run_1",
            [{"coherence": 0.8, "reward": 1.0, "success": True}],
            [],
        )
        export_path = tmp_path / "scorecard.json"
        scorecard.export_json(export_path)

        new_scorecard = CapabilityScorecard()
        new_scorecard.import_json(export_path)
        report = new_scorecard.generate_report()
        assert report["total_runs"] == 1
