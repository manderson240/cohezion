"""Tests for agentic_metrics module — EVO physics metric families, bootstrap, and statistics."""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.benchmarks.agentic_metrics import (
    BonferroniCorrection,
    BootstrapResult,
    CoherenceMetric,
    EVOPhysicsMetrics,
    ExoticChargeMetric,
    KordylewskiOrbitMetric,
    SPINPhaseMetric,
    StabilityMetric,
    StatisticalComparison,
    TRIUNEBalanceMetric,
    _bootstrap_mean_ci,
    _mann_whitney_u,
)


class TestBootstrapResult:
    """Tests for BootstrapResult dataclass."""

    def test_frozen(self):
        """BootstrapResult is frozen (immutable)."""
        result = BootstrapResult(mean=0.5, std=0.1, ci_lower=0.4, ci_upper=0.6, p_value=0.05)
        with pytest.raises(AttributeError):
            result.mean = 0.6

    def test_defaults(self):
        """Default n_samples is N_BOOTSTRAP."""
        result = BootstrapResult(mean=0.5, std=0.1, ci_lower=0.4, ci_upper=0.6, p_value=0.05)
        assert result.n_samples == 1000


class TestBonferroniCorrection:
    """Tests for Bonferroni correction."""

    def test_correct_basic(self):
        """Corrected p-values are capped at 1.0."""
        correction = BonferroniCorrection(n_tests=3, alpha=0.05)
        p_values = [0.01, 0.02, 0.03]
        corrected = correction.correct(p_values)
        assert corrected[0] == pytest.approx(0.03)
        assert corrected[1] == pytest.approx(0.06)
        assert corrected[2] == pytest.approx(0.09)
        assert all(p <= 1.0 for p in corrected)

    def test_correct_capped(self):
        """P-values exceeding 1/n are capped at 1.0."""
        correction = BonferroniCorrection(n_tests=2, alpha=0.05)
        p_values = [0.6, 0.7]
        corrected = correction.correct(p_values)
        assert corrected[0] == 1.0
        assert corrected[1] == 1.0

    def test_significant_mask(self):
        """significant_mask returns bool list."""
        correction = BonferroniCorrection(n_tests=5, alpha=0.05)
        p_values = [0.001, 0.005, 0.009, 0.05, 0.1]
        mask = correction.significant_mask(p_values)
        assert mask == [True, True, True, False, False]

    def test_corrected_alpha(self):
        """corrected_alpha = alpha / n_tests."""
        correction = BonferroniCorrection(n_tests=4, alpha=0.05)
        assert correction.corrected_alpha == 0.0125


class TestBootstrapMeanCI:
    """Tests for bootstrap mean CI function."""

    def test_empty_data(self):
        """Empty data returns zeros."""
        ci_lower, ci_upper, p_value = _bootstrap_mean_ci(np.array([]))
        assert ci_lower == 0.0
        assert ci_upper == 0.0
        assert p_value == 1.0

    def test_single_value(self):
        """Single value returns that value."""
        data = np.array([0.5])
        ci_lower, ci_upper, p_value = _bootstrap_mean_ci(data)
        assert ci_lower == 0.5
        assert ci_upper == 0.5

    def test_positive_mean_nonzero_pvalue(self):
        """Positive mean vs H0=0 should give low p-value."""
        data = np.array([0.8, 0.85, 0.9, 0.75, 0.95])
        _, _, p_value = _bootstrap_mean_ci(data)
        assert p_value < 0.1


class TestMannWhitneyU:
    """Tests for Mann-Whitney U test."""

    def test_identical_groups(self):
        """Identical groups should not be significant."""
        group1 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        group2 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = _mann_whitney_u(group1, group2)
        assert result.p_value > 0.05
        assert not result.significant

    def test_different_groups(self):
        """Different groups should be significant."""
        group1 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        group2 = np.array([10.0, 11.0, 12.0, 13.0, 14.0])
        result = _mann_whitney_u(group1, group2)
        assert result.p_value < 0.05
        assert result.significant

    def test_empty_groups(self):
        """Empty groups return default."""
        result = _mann_whitney_u(np.array([]), np.array([1.0, 2.0]))
        assert result.u_statistic == 0.0
        assert result.p_value <= 1.0


class TestCoherenceMetric:
    """Tests for CoherenceMetric."""

    @pytest.fixture
    def metric(self):
        return CoherenceMetric(target=0.5)

    def test_high_coherence(self, metric):
        """High coherence near target gives good score."""
        coherences = [0.8, 0.85, 0.9, 0.82, 0.88]
        result = metric.compute(coherences)
        assert result.mean == pytest.approx(0.85)
        assert result.std == pytest.approx(np.std(coherences, ddof=1), rel=1e-3)
        assert 0.0 <= result.ci_lower <= result.mean <= result.ci_upper <= 1.0

    def test_low_coherence(self, metric):
        """Low coherence is penalized."""
        coherences = [0.1, 0.15, 0.12, 0.08, 0.11]
        result = metric.compute(coherences)
        assert result.mean == pytest.approx(np.mean(coherences))

    def test_nan_filtering(self, metric):
        """NaN values are filtered out."""
        coherences = [0.5, float("nan"), 0.6, float("nan"), 0.55]
        result = metric.compute(coherences)
        assert np.isfinite(result.mean)
        assert result.std >= 0.0  # finite std

    def test_compare(self, metric):
        """compare returns StatisticalComparison."""
        result = metric.compare([0.5, 0.6, 0.7], [0.3, 0.4, 0.5])
        assert isinstance(result, StatisticalComparison)
        assert "u_statistic" in result.__dict__ or hasattr(result, "u_statistic")


class TestTRIUNEBalanceMetric:
    """Tests for TRIUNEBalanceMetric."""

    @pytest.fixture
    def metric(self):
        return TRIUNEBalanceMetric()

    def test_balanced_weights(self, metric):
        """Perfect balance (1/3 each) gives score 0."""
        doer = [0.33] * 10
        thinker = [0.33] * 10
        knower = [0.34] * 10
        result = metric.compute(doer, thinker, knower)
        assert result.mean < 0.1

    def test_imbalanced_weights(self, metric):
        """Dominant pole gives high imbalance score."""
        doer = [0.9] * 10
        thinker = [0.05] * 10
        knower = [0.05] * 10
        result = metric.compute(doer, thinker, knower)
        assert result.mean > 0.5

    def test_empty_weights(self, metric):
        """Empty weights return default."""
        result = metric.compute([], [], [])
        assert result.mean == 1.0


class TestStabilityMetric:
    """Tests for StabilityMetric."""

    @pytest.fixture
    def metric(self):
        return StabilityMetric()

    def test_stable_episode(self, metric):
        """Stable episode (low variance) gives high stability."""
        coherences = [0.5, 0.51, 0.49, 0.50, 0.50]
        hiho_distances = [0.0, 0.01, 0.01, 0.0, 0.0]
        result = metric.compute(coherences, hiho_distances)
        assert result.mean > 0.5

    def test_unstable_episode(self, metric):
        """Unstable episode (high variance) gives low stability."""
        coherences = [0.1, 0.9, 0.2, 0.8, 0.3]
        hiho_distances = [0.4, 0.4, 0.3, 0.3, 0.2]
        result = metric.compute(coherences, hiho_distances)
        assert result.mean < 0.5


class TestExoticChargeMetric:
    """Tests for ExoticChargeMetric."""

    @pytest.fixture
    def metric(self):
        return ExoticChargeMetric()

    def test_high_charge(self, metric):
        """High charge accumulation is measured."""
        trajectory = [0.5, 0.6, 0.7, 0.8, 0.9]
        result = metric.compute(trajectory)
        assert result.mean == pytest.approx(0.7)

    def test_empty_trajectory(self, metric):
        """Empty trajectory returns default."""
        result = metric.compute([])
        assert result.mean == 0.0


class TestKordylewskiOrbitMetric:
    """Tests for KordylewskiOrbitMetric."""

    @pytest.fixture
    def metric(self):
        return KordylewskiOrbitMetric()

    def test_stable_orbit(self, metric):
        """Short Lagrange distances give high orbit stability."""
        distances = [0.01, 0.02, 0.015, 0.01, 0.02]
        result = metric.compute(distances)
        assert result.mean > 0.9

    def test_unstable_orbit(self, metric):
        """Large Lagrange distances give low orbit stability."""
        distances = [1.0, 2.0, 1.5, 2.2, 1.8]
        result = metric.compute(distances)
        assert result.mean < 0.5


class TestSPINPhaseMetric:
    """Tests for SPINPhaseMetric."""

    @pytest.fixture
    def metric(self):
        return SPINPhaseMetric()

    def test_monotonic_phase(self, metric):
        """Monotonic phase accumulation (~0.1 rad/step)."""
        phase = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
        result = metric.compute(phase)
        assert result.mean == pytest.approx(0.1, rel=0.1)

    def test_single_phase(self, metric):
        """Single phase value returns zeros."""
        result = metric.compute([1.0])
        assert result.mean == 0.0

    def test_empty_phase(self, metric):
        """Empty phase returns default."""
        result = metric.compute([])
        assert result.mean == 0.0


class TestEVOPhysicsMetrics:
    """Tests for EVOPhysicsMetrics aggregator."""

    @pytest.fixture
    def metrics_engine(self):
        return EVOPhysicsMetrics()

    @pytest.fixture
    def sample_biography(self):
        return [
            {
                "coherence": 0.8,
                "doer_weight": 0.33,
                "thinker_weight": 0.33,
                "knower_weight": 0.34,
                "exotic_charge_density": 0.5,
                "lagrange_distance": 0.1,
                "phase": i * 0.1,
            }
            for i in range(50)
        ]

    def test_compute_all(self, metrics_engine, sample_biography):
        """compute_all returns all 6 metric families."""
        results = metrics_engine.compute_all(sample_biography)
        assert set(results.keys()) == {
            "coherence",
            "triune_balance",
            "stability",
            "exotic_charge",
            "kordylewski_orbit",
            "spin_phase",
        }
        for key, result in results.items():
            assert isinstance(result, BootstrapResult)

    def test_compare_biographies(self, metrics_engine, sample_biography):
        """compare_biographies returns all metric comparisons."""
        bio2 = [
            {
                "coherence": 0.6 + i * 0.005,
                "doer_weight": 0.4,
                "thinker_weight": 0.3,
                "knower_weight": 0.3,
                "exotic_charge_density": 0.4 + i * 0.01,
                "lagrange_distance": 0.2,
                "phase": i * 0.1,
            }
            for i in range(50)
        ]
        comparisons = metrics_engine.compare_biographies(sample_biography, bio2)
        assert set(comparisons.keys()) == {
            "coherence",
            "triune_balance",
            "stability",
            "exotic_charge",
            "kordylewski_orbit",
            "spin_phase",
        }
        for key, comp in comparisons.items():
            assert isinstance(comp, StatisticalComparison)

    def test_summary_report(self, metrics_engine, sample_biography):
        """summary_report generates string output."""
        results = metrics_engine.compute_all(sample_biography)
        report = metrics_engine.summary_report(results)
        assert "FLUME EVO Physics Benchmark" in report
        assert "COHERENCE" in report
        assert "p-value" in report

    def test_empty_biography(self, metrics_engine):
        """Empty biography handles gracefully."""
        results = metrics_engine.compute_all([])
        assert len(results) == 6
