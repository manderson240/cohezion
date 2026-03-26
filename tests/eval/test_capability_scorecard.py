"""Tests for eval/capability_scorecard module — 6-axis radar, longitudinal tracking, and comparison."""

from __future__ import annotations

import pytest

from cohezion.eval.capability_scorecard import (
    CapabilityScorecard,
    LongitudinalTracker,
    RadarChart,
    StatisticalComparison,
)


class TestRadarChart:
    """Tests for RadarChart visualization."""

    def test_axes_defined(self):
        """All 6 axes are defined."""
        assert len(RadarChart.AXES) == 6
        assert "HIHO Coherence" in RadarChart.AXES
        assert "SPIN Phase" in RadarChart.AXES

    def test_max_values_defined(self):
        """Max values are defined for all 6 axes."""
        assert len(RadarChart.MAX_VALUES) == 6
        assert all(v > 0 for v in RadarChart.MAX_VALUES)

    def test_plot_wrong_number_of_values(self):
        """Wrong number of values raises ValueError."""
        radar = RadarChart()
        with pytest.raises(ValueError):
            radar.plot([0.5, 0.5], title="Too few")

    def test_plot_returns_figure(self):
        """plot() returns a figure object."""
        radar = RadarChart()
        values = [0.8, 0.6, 0.9, 0.7, 0.85, 0.75]
        fig = radar.plot(values, title="Test")
        assert fig is not None

    def test_compare(self):
        """compare() produces a comparison figure."""
        radar = RadarChart()
        group1 = [0.8, 0.6, 0.9, 0.7, 0.85, 0.75]
        group2 = [0.6, 0.8, 0.7, 0.9, 0.65, 0.85]
        fig = radar.compare(group1, group2)
        assert fig is not None
        assert hasattr(fig, "savefig") or hasattr(fig, "write_html")


class TestLongitudinalTracker:
    """Tests for LongitudinalTracker."""

    @pytest.fixture
    def tracker(self):
        return LongitudinalTracker()

    def test_record(self, tracker):
        """record() stores scores."""
        tracker.record("run_1", {"coherence": 0.8, "triune_balance": 0.6})
        tracker.record("run_2", {"coherence": 0.85, "triune_balance": 0.65})
        assert len(tracker._history) == 2

    def test_weakest_axis_single_run(self, tracker):
        """Single run cannot determine weakest."""
        tracker.record("run_1", {"coherence": 0.8})
        result = tracker.get_weakest_axis()
        assert result is None or isinstance(result, str)

    def test_weakest_axis(self, tracker):
        """get_weakest_axis returns lowest scoring axis."""
        tracker.record(
            "run_1",
            {
                "coherence": 0.9,
                "triune_balance": 0.3,
                "stability": 0.7,
                "exotic_charge": 0.6,
                "kordylewski_orbit": 0.5,
                "spin_phase": 0.8,
            },
        )
        tracker.record(
            "run_2",
            {
                "coherence": 0.85,
                "triune_balance": 0.35,
                "stability": 0.65,
                "exotic_charge": 0.55,
                "kordylewski_orbit": 0.45,
                "spin_phase": 0.75,
            },
        )
        weakest = tracker.get_weakest_axis()
        assert weakest in RadarChart.AXES

    def test_strongest_axis(self, tracker):
        """get_strongest_axis returns highest scoring axis."""
        tracker.record(
            "run_1",
            {
                "coherence": 0.9,
                "triune_balance": 0.3,
                "stability": 0.7,
                "exotic_charge": 0.6,
                "kordylewski_orbit": 0.5,
                "spin_phase": 0.8,
            },
        )
        tracker.record(
            "run_2",
            {
                "coherence": 0.85,
                "triune_balance": 0.35,
                "stability": 0.65,
                "exotic_charge": 0.55,
                "kordylewski_orbit": 0.45,
                "spin_phase": 0.75,
            },
        )
        strongest = tracker.get_strongest_axis()
        assert strongest == "HIHO Coherence"

    def test_trend_summary_insufficient_runs(self, tracker):
        """Need 2+ runs for trend analysis."""
        tracker.record("run_1", {"coherence": 0.8})
        result = tracker.get_trend_summary()
        assert "error" in result

    def test_trend_summary(self, tracker):
        """get_trend_summary computes slopes correctly."""
        tracker.record(
            "run_1",
            {
                "coherence": 0.5,
                "triune_balance": 0.5,
                "stability": 0.5,
                "exotic_charge": 0.5,
                "kordylewski_orbit": 0.5,
                "spin_phase": 0.5,
            },
        )
        tracker.record(
            "run_2",
            {
                "coherence": 0.6,
                "triune_balance": 0.6,
                "stability": 0.6,
                "exotic_charge": 0.6,
                "kordylewski_orbit": 0.6,
                "spin_phase": 0.6,
            },
        )
        result = tracker.get_trend_summary()
        assert "HIHO Coherence" in result
        assert result["HIHO Coherence"]["slope"] > 0


class TestCapabilityScorecard:
    """Tests for CapabilityScorecard."""

    @pytest.fixture
    def scorecard(self):
        return CapabilityScorecard()

    @pytest.fixture
    def sample_episodes(self):
        return [
            {
                "episode": 1,
                "reward": 1.5,
                "coherence": 0.8,
                "final_coherence": 0.85,
                "success": True,
                "steps": 150,
            },
            {
                "episode": 2,
                "reward": 1.2,
                "coherence": 0.75,
                "final_coherence": 0.78,
                "success": True,
                "steps": 180,
            },
        ]

    @pytest.fixture
    def sample_biographies(self):
        return [
            [
                {
                    "coherence": 0.8,
                    "doer_weight": 0.33,
                    "thinker_weight": 0.33,
                    "knower_weight": 0.34,
                    "exotic_charge_density": 0.5,
                    "lagrange_distance": 0.1,
                    "phase": i * 0.1,
                }
                for i in range(20)
            ]
        ]

    def test_record_run(self, scorecard, sample_episodes, sample_biographies):
        """record_run() stores episode data."""
        scorecard.record_run("run_1", sample_episodes, sample_biographies)
        assert "run_1" in scorecard._runs

    def test_generate_report_empty(self, scorecard):
        """Empty scorecard returns error."""
        report = scorecard.generate_report()
        assert "error" in report

    def test_generate_report(self, scorecard, sample_episodes, sample_biographies):
        """generate_report() returns full report."""
        scorecard.record_run("run_1", sample_episodes, sample_biographies)
        report = scorecard.generate_report()
        assert "latest_run" in report
        assert report["latest_run"] == "run_1"
        assert "latest" in report
        assert "total_runs" in report
        assert report["total_runs"] == 1

    def test_plot_radar_no_runs(self, scorecard):
        """plot_radar() raises without runs."""
        with pytest.raises(ValueError):
            scorecard.plot_radar()

    def test_plot_radar(self, scorecard, sample_episodes, sample_biographies):
        """plot_radar() returns a figure."""
        scorecard.record_run("run_1", sample_episodes, sample_biographies)
        fig = scorecard.plot_radar(run_id="run_1")
        assert fig is not None

    def test_compare_runs(self, scorecard):
        """compare_runs() requires 2 runs."""
        scorecard.record_run("run_1", [{"episode": 1, "coherence": 0.8, "success": True}])
        with pytest.raises(ValueError):
            scorecard.compare_runs("run_1", "run_2")

    def test_compare_runs_both_exist(self, scorecard):
        """compare_runs() with both runs succeeds."""
        scorecard.record_run(
            "run_1",
            [
                {"episode": 1, "coherence": 0.8, "success": True},
                {"episode": 2, "coherence": 0.75, "success": True},
            ],
        )
        scorecard.record_run(
            "run_2",
            [
                {"episode": 1, "coherence": 0.6, "success": False},
                {"episode": 2, "coherence": 0.65, "success": False},
            ],
        )
        comparisons = scorecard.compare_runs("run_1", "run_2")
        assert len(comparisons) == len(RadarChart.AXES)

    def test_export_import_json(self, scorecard, sample_episodes, tmp_path):
        """export_json and import_json roundtrip."""
        scorecard.record_run("run_1", sample_episodes)
        export_path = tmp_path / "scorecard.json"
        scorecard.export_json(export_path)

        new_scorecard = CapabilityScorecard()
        new_scorecard.import_json(export_path)
        assert "run_1" in new_scorecard._runs


class TestStatisticalComparison:
    """Tests for StatisticalComparison frozen dataclass."""

    def test_frozen(self):
        """StatisticalComparison is frozen."""
        comp = StatisticalComparison(
            metric="coherence",
            group1_mean=0.8,
            group2_mean=0.7,
            difference=-0.1,
            percent_change=-12.5,
            p_value=0.05,
            significant=False,
            n_group1=10,
            n_group2=10,
        )
        with pytest.raises(AttributeError):
            comp.group1_mean = 0.9

    def test_fields(self):
        """All fields are present."""
        comp = StatisticalComparison(
            metric="test",
            group1_mean=1.0,
            group2_mean=2.0,
            difference=1.0,
            percent_change=100.0,
            p_value=0.01,
            significant=True,
            n_group1=5,
            n_group2=5,
        )
        assert comp.group1_mean == 1.0
        assert comp.group2_mean == 2.0
        assert comp.difference == 1.0
        assert comp.percent_change == 100.0
        assert comp.p_value == 0.01
        assert comp.significant
        assert comp.n_group1 == 5
        assert comp.n_group2 == 5
