"""Tests for Agentic Metrics - EVO Physics-based benchmark metrics.

TDD tests for 6 EVO physics-based metrics with statistical rigor:
- Bootstrap CIs (1000 samples)
- Mann-Whitney U (non-parametric)
- Bonferroni correction
- Power analysis
"""

from __future__ import annotations

import numpy as np
import pytest


class TestAgenticResults:
    """[P0] Tests for AgenticResults dataclass."""

    def test_creation_with_all_fields(self):
        """[P0] Should create AgenticResults with all required fields."""
        from cohezion.benchmarks.agentic_metrics import AgenticResults

        result = AgenticResults(
            evo_coherence_amplitude=0.85,
            phase_locking_rate=0.72,
            exotic_charge_lifetime=150.0,
            kordylewski_orbit_quality=0.91,
            triune_balance_index=0.88,
            recovery_basin_radius=0.65,
            composite_score=0.78,
            confidence_intervals={
                "evo_coherence_amplitude": (0.80, 0.90),
                "phase_locking_rate": (0.65, 0.79),
            },
            statistical_tests={
                "mann_whitney": {"u_stat": 45.0, "p_value": 0.03},
                "bonferroni": {"adjusted_alpha": 0.0083},
            },
        )

        assert result.evo_coherence_amplitude == 0.85
        assert result.phase_locking_rate == 0.72
        assert result.exotic_charge_lifetime == 150.0
        assert result.kordylewski_orbit_quality == 0.91
        assert result.triune_balance_index == 0.88
        assert result.recovery_basin_radius == 0.65
        assert result.composite_score == 0.78
        assert "evo_coherence_amplitude" in result.confidence_intervals
        assert "mann_whitney" in result.statistical_tests

    def test_default_confidence_intervals(self):
        """[P1] Should handle empty confidence intervals."""
        from cohezion.benchmarks.agentic_metrics import AgenticResults

        result = AgenticResults(
            evo_coherence_amplitude=0.5,
            phase_locking_rate=0.5,
            exotic_charge_lifetime=0.0,
            kordylewski_orbit_quality=0.5,
            triune_balance_index=0.5,
            recovery_basin_radius=0.5,
            composite_score=0.5,
            confidence_intervals={},
            statistical_tests={},
        )

        assert result.confidence_intervals == {}
        assert result.statistical_tests == {}


class TestEVOCoherenceAmplitude:
    """[P0] Tests for EVO Coherence Amplitude metric."""

    def test_peak_coherence_over_journey(self):
        """[P0] Should compute peak coherence over journey trajectory."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journey = {
            "trajectory": [
                {"coherence": 0.3, "hiho_distance": 0.2},
                {"coherence": 0.5, "hiho_distance": 0.1},
                {"coherence": 0.8, "hiho_distance": 0.3},
                {"coherence": 0.6, "hiho_distance": 0.15},
            ]
        }

        amplitude = metrics._compute_evo_coherence_amplitude(journey)
        assert amplitude == 0.8  # Peak coherence

    def test_empty_trajectory_returns_zero(self):
        """[P1] Should return 0 for empty trajectory."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journey = {"trajectory": []}

        amplitude = metrics._compute_evo_coherence_amplitude(journey)
        assert amplitude == 0.0

    def test_single_step_journey(self):
        """[P1] Should handle single step journey."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journey = {"trajectory": [{"coherence": 0.7}]}

        amplitude = metrics._compute_evo_coherence_amplitude(journey)
        assert amplitude == 0.7


class TestPhaseLockingRate:
    """[P0] Tests for Phase Locking Rate metric."""

    def test_spin_precession_alignment(self):
        """[P0] Should compute % steps where SPIN aligns with precession."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journey = {
            "trajectory": [
                {"spin": 0.0, "precession": 0.1},  # Aligned
                {"spin": 0.5, "precession": 0.4},  # Aligned
                {"spin": 1.0, "precession": 0.95},  # Aligned
            ]
        }

        rate = metrics._compute_phase_locking_rate(journey)
        assert rate == 1.0  # All aligned within threshold

    def test_no_phase_locking(self):
        """[P1] Should return 0 when no phase alignment."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journey = {
            "trajectory": [
                {"spin": 0.0, "precession": 0.3},
                {"spin": 0.5, "precession": 0.8},
                {"spin": 1.0, "precession": 0.6},
            ]
        }

        rate = metrics._compute_phase_locking_rate(journey)
        assert rate == pytest.approx(0.0, abs=0.01)

    def test_missing_spin_or_precession(self):
        """[P1] Should handle missing spin or precession fields."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journey = {"trajectory": [{"coherence": 0.5}]}

        rate = metrics._compute_phase_locking_rate(journey)
        assert rate == 0.0


class TestExoticChargeLifetime:
    """[P0] Tests for Exotic Charge Lifetime metric (survival analysis)."""

    def test_steps_before_exotic_charge_decay(self):
        """[P0] Should compute steps before exotic_charge_density > 0.95."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journey = {
            "trajectory": [
                {"exotic_charge_density": 0.2},
                {"exotic_charge_density": 0.5},
                {"exotic_charge_density": 0.8},
                {"exotic_charge_density": 0.97},  # Crosses threshold here
                {"exotic_charge_density": 0.99},
            ]
        }

        lifetime = metrics._compute_exotic_charge_lifetime(journey)
        assert lifetime == 3  # Steps before crossing threshold

    def test_exotic_charge_never_exceeds_threshold(self):
        """[P1] Should return trajectory length if threshold never crossed."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journey = {
            "trajectory": [
                {"exotic_charge_density": 0.2},
                {"exotic_charge_density": 0.5},
                {"exotic_charge_density": 0.8},
            ]
        }

        lifetime = metrics._compute_exotic_charge_lifetime(journey)
        assert lifetime == 3  # Full trajectory length

    def test_empty_trajectory(self):
        """[P1] Should return 0 for empty trajectory."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journey = {"trajectory": []}

        lifetime = metrics._compute_exotic_charge_lifetime(journey)
        assert lifetime == 0.0


class TestKordylewskiOrbitQuality:
    """[P0] Tests for Kordylewski Orbit Quality metric."""

    def test_orbit_radius_variance_ratio(self):
        """[P0] Should compute 1 - (orbit_radius_variance / baseline_variance)."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journey = {
            "trajectory": [
                {"orbit_radius": 1.0},
                {"orbit_radius": 1.1},
                {"orbit_radius": 0.9},
                {"orbit_radius": 1.05},
            ],
            "baseline_orbit_variance": 0.5,
        }

        quality = metrics._compute_kordylewski_orbit_quality(journey)
        orbit_var = np.var([1.0, 1.1, 0.9, 1.05])
        expected = 1.0 - (orbit_var / 0.5)
        assert abs(quality - expected) < 0.01

    def test_no_baseline_returns_half(self):
        """[P1] Should return 0.5 when no baseline provided."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journey = {"trajectory": [{"orbit_radius": 1.0}]}

        quality = metrics._compute_kordylewski_orbit_quality(journey)
        assert quality == 0.5


class TestTriuneBalanceIndex:
    """[P0] Tests for TRIUNE Balance Index metric."""

    def test_balance_from_doer_thinker_knower(self):
        """[P0] Should compute 1 - std(doer/thinker/knower activation)."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journey = {
            "trajectory": [
                {"doer_activation": 0.8, "thinker_activation": 0.8, "knower_activation": 0.8},
            ]
        }

        balance = metrics._compute_triune_balance_index(journey)
        assert balance == pytest.approx(1.0, abs=0.01)

    def test_unbalanced_returns_low_score(self):
        """[P1] Should return low score for unbalanced activations."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journey = {
            "trajectory": [
                {"doer_activation": 1.0, "thinker_activation": 0.0, "knower_activation": 0.0},
            ]
        }

        balance = metrics._compute_triune_balance_index(journey)
        assert 0.4 < balance < 0.6

    def test_missing_triune_fields(self):
        """[P1] Should handle missing activation fields."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journey = {"trajectory": [{"coherence": 0.5}]}

        balance = metrics._compute_triune_balance_index(journey)
        assert balance == 0.0


class TestRecoveryBasinRadius:
    """[P0] Tests for Recovery Basin Radius metric."""

    def test_max_hiho_distance_with_recovery(self):
        """[P0] Should compute max HIHO distance with successful recovery."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journey = {
            "trajectory": [
                {"hiho_distance": 0.1, "recovered": True},
                {"hiho_distance": 0.3, "recovered": True},
                {"hiho_distance": 0.5, "recovered": True},
                {"hiho_distance": 0.8, "recovered": False},  # Failed recovery
            ]
        }

        radius = metrics._compute_recovery_basin_radius(journey)
        assert radius == 0.5  # Last successful recovery distance

    def test_all_recoveries_fail(self):
        """[P1] Should return 0 when all recoveries fail."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journey = {
            "trajectory": [
                {"hiho_distance": 0.1, "recovered": False},
                {"hiho_distance": 0.2, "recovered": False},
            ]
        }

        radius = metrics._compute_recovery_basin_radius(journey)
        assert radius == 0.0

    def test_no_recovery_data(self):
        """[P1] Should handle missing recovery field."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journey = {"trajectory": [{"hiho_distance": 0.3}]}

        radius = metrics._compute_recovery_basin_radius(journey)
        assert radius == 0.0


class TestBootstrapConfidenceIntervals:
    """[P0] Tests for bootstrap confidence intervals."""

    def test_bootstrap_ci_computation(self):
        """[P0] Should compute 95% bootstrap CI using 1000 samples."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        data = [0.8, 0.85, 0.75, 0.9, 0.82, 0.88, 0.78, 0.92, 0.81, 0.87]

        lower, upper = metrics._compute_bootstrap_ci(data, n_bootstrap=1000, ci=0.95)

        assert lower < upper
        assert 0.7 < lower < 0.9
        assert 0.8 < upper < 1.0

    def test_bootstrap_ci_small_sample(self):
        """[P1] Should handle small samples gracefully."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        data = [0.8, 0.9]

        lower, upper = metrics._compute_bootstrap_ci(data, n_bootstrap=100, ci=0.95)

        assert lower < upper

    def test_bootstrap_ci_single_value(self):
        """[P1] Should return NaN bounds for single value."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        data = [0.8]

        lower, upper = metrics._compute_bootstrap_ci(data, n_bootstrap=100, ci=0.95)

        assert np.isnan(lower) or lower == upper


class TestMannWhitneyU:
    """[P0] Tests for Mann-Whitney U test (non-parametric)."""

    def test_mann_whitney_u_computation(self):
        """[P0] Should compute Mann-Whitney U test."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        group1 = [0.8, 0.85, 0.75, 0.9]
        group2 = [0.5, 0.55, 0.45, 0.6]

        result = metrics._compute_mann_whitney_u(group1, group2)

        assert "u_stat" in result
        assert "p_value" in result
        assert result["u_stat"] > 0
        assert 0.0 <= result["p_value"] <= 1.0

    def test_mann_whitney_identical_groups(self):
        """[P1] Should handle identical groups (p_value near 1.0)."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        group1 = [0.5, 0.6, 0.7]
        group2 = [0.5, 0.6, 0.7]

        result = metrics._compute_mann_whitney_u(group1, group2)

        assert result["p_value"] > 0.5  # Should not be significant


class TestBonferroniCorrection:
    """[P0] Tests for Bonferroni correction."""

    def test_bonferroni_alpha_adjustment(self):
        """[P0] Should adjust alpha for multiple comparisons."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        n_comparisons = 6
        original_alpha = 0.05

        adjusted = metrics._bonferroni_correction(original_alpha, n_comparisons)

        assert adjusted == pytest.approx(0.05 / 6, abs=0.001)

    def test_bonferroni_with_task_archetypes(self):
        """[P1] Should handle N task archetype comparisons."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        n_metrics = 6
        n_archetypes = 3
        original_alpha = 0.05

        adjusted = metrics._bonferroni_correction(original_alpha, n_metrics * n_archetypes)

        assert adjusted == pytest.approx(0.05 / 18, abs=0.001)


class TestPowerAnalysis:
    """[P0] Tests for power analysis (minimum detectable effect size)."""

    def test_minimum_detectable_effect_size(self):
        """[P0] Should compute minimum detectable effect size."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)

        mde = metrics._compute_minimum_detectable_effect(alpha=0.05, power=0.8, n1=30, n2=30)

        assert mde == pytest.approx(0.511, abs=0.01)
        assert 0.0 < mde < 1.0

    def test_mde_with_unbalanced_samples(self):
        """[P1] Should handle unbalanced sample sizes."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)

        mde = metrics._compute_minimum_detectable_effect(alpha=0.05, power=0.8, n1=20, n2=40)

        assert mde > 0.0


class TestComputeAllMetrics:
    """[P0] Integration tests for compute_all_metrics."""

    def test_compute_all_metrics(self):
        """[P0] Should compute all 6 metrics with bootstrap CIs."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journeys = [
            {
                "trajectory": [
                    {
                        "coherence": 0.5,
                        "hiho_distance": 0.1,
                        "spin": 0.5,
                        "precession": 0.5,
                        "exotic_charge_density": 0.3,
                        "orbit_radius": 1.0,
                        "doer_activation": 0.8,
                        "thinker_activation": 0.7,
                        "knower_activation": 0.75,
                        "recovered": True,
                    },
                    {
                        "coherence": 0.7,
                        "hiho_distance": 0.2,
                        "spin": 0.6,
                        "precession": 0.6,
                        "exotic_charge_density": 0.6,
                        "orbit_radius": 1.1,
                        "doer_activation": 0.85,
                        "thinker_activation": 0.8,
                        "knower_activation": 0.82,
                        "recovered": True,
                    },
                ],
                "baseline_orbit_variance": 0.5,
            }
        ]

        results = metrics.compute_all_metrics(journeys, n_bootstrap=100)

        assert results.evo_coherence_amplitude == 0.7
        assert results.phase_locking_rate == 1.0
        assert results.exotic_charge_lifetime == 2.0
        assert 0.0 <= results.kordylewski_orbit_quality <= 1.0
        assert 0.0 <= results.triune_balance_index <= 1.0
        assert results.recovery_basin_radius == 0.2
        assert 0.0 <= results.composite_score <= 1.0
        assert "evo_coherence_amplitude" in results.confidence_intervals
        assert "mann_whitney" in results.statistical_tests

    def test_empty_journeys_returns_zeros(self):
        """[P1] Should return zero values for empty journeys."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        results = metrics.compute_all_metrics([])

        assert results.evo_coherence_amplitude == 0.0
        assert results.phase_locking_rate == 0.0
        assert results.exotic_charge_lifetime == 0.0
        assert results.composite_score == 0.0


class TestCompositeScore:
    """[P0] Tests for composite score computation."""

    def test_composite_score_weights(self):
        """[P0] Should compute weighted composite score."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)

        score = metrics._compute_composite_score(
            evo_coherence_amplitude=0.8,
            phase_locking_rate=0.7,
            exotic_charge_lifetime=100.0,
            kordylewski_orbit_quality=0.9,
            triune_balance_index=0.85,
            recovery_basin_radius=0.6,
        )

        # Verify it's a weighted combination
        assert 0.0 <= score <= 1.0

    def test_composite_score_normalization(self):
        """[P1] Should normalize exotic_charge_lifetime to [0,1]."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)

        # Normalize exotic_charge_lifetime relative to some baseline
        score1 = metrics._compute_composite_score(
            evo_coherence_amplitude=0.8,
            phase_locking_rate=0.7,
            exotic_charge_lifetime=50.0,  # Low
            kordylewski_orbit_quality=0.9,
            triune_balance_index=0.85,
            recovery_basin_radius=0.6,
        )

        score2 = metrics._compute_composite_score(
            evo_coherence_amplitude=0.8,
            phase_locking_rate=0.7,
            exotic_charge_lifetime=200.0,  # High
            kordylewski_orbit_quality=0.9,
            triune_balance_index=0.85,
            recovery_basin_radius=0.6,
        )

        # Higher exotic_charge_lifetime should contribute more to composite
        # (assuming normalized to 0-1 scale)
        assert score1 != score2


class TestCompareTaskArchetypes:
    """[P1] Tests for comparing across task archetypes."""

    def test_compare_task_archetypes(self):
        """[P1] Should compute metrics grouped by task archetype."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journeys = [
            {
                "task_archetype": "exploration",
                "trajectory": [
                    {"coherence": 0.6, "hiho_distance": 0.1, "spin": 0.5, "precession": 0.5},
                ],
            },
            {
                "task_archetype": "exploitation",
                "trajectory": [
                    {"coherence": 0.7, "hiho_distance": 0.2, "spin": 0.6, "precession": 0.6},
                ],
            },
        ]

        archetype_metrics = metrics.compare_task_archetypes(journeys)

        assert "exploration" in archetype_metrics
        assert "exploitation" in archetype_metrics
        assert isinstance(archetype_metrics["exploration"], dict)

    def test_archetype_mann_whitney_comparison(self):
        """[P1] Should run Mann-Whitney U across archetypes."""
        from cohezion.benchmarks.agentic_metrics import AgenticMetrics

        metrics = AgenticMetrics(random_state=42)
        journeys = [
            {
                "task_archetype": "A",
                "trajectory": [
                    {"coherence": 0.6, "hiho_distance": 0.1, "spin": 0.5, "precession": 0.5},
                ],
            },
            {
                "task_archetype": "B",
                "trajectory": [
                    {"coherence": 0.7, "hiho_distance": 0.2, "spin": 0.6, "precession": 0.6},
                ],
            },
        ]

        archetype_metrics = metrics.compare_task_archetypes(journeys)

        assert "bonferroni" in archetype_metrics
        assert archetype_metrics["bonferroni"]["adjusted_alpha"] is not None
        assert archetype_metrics["bonferroni"]["adjusted_alpha"] == pytest.approx(0.05 / (2 * 6), abs=0.001)
