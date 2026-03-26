"""Tests for EVO physics metrics (EVOPhysicsMetrics, CoherenceMetric, etc.)."""

from __future__ import annotations

import numpy as np
import pytest


class TestBootstrapResult:
    """Tests for BootstrapResult dataclass."""

    @pytest.mark.fast
    def test_creation(self):
        """Test BootstrapResult creation."""
        from cohezion.benchmarks.agentic_metrics import BootstrapResult

        result = BootstrapResult(
            mean=0.8,
            std=0.1,
            ci_lower=0.7,
            ci_upper=0.9,
            p_value=0.02,
            n_samples=1000,
            effect_size=0.5,
        )
        assert result.mean == 0.8
        assert result.std == 0.1
        assert result.ci_lower == 0.7
        assert result.ci_upper == 0.9
        assert result.p_value == 0.02
        assert result.n_samples == 1000
        assert result.effect_size == 0.5


class TestCoherenceMetric:
    """Tests for CoherenceMetric."""

    @pytest.mark.fast
    def test_compute_empty(self):
        """Test compute with empty list returns zeros."""
        from cohezion.benchmarks.agentic_metrics import CoherenceMetric

        metric = CoherenceMetric()
        result = metric.compute([])
        assert result.mean == 0.0

    @pytest.mark.fast
    def test_compute_with_data(self):
        """Test compute with coherence values."""
        from cohezion.benchmarks.agentic_metrics import CoherenceMetric

        metric = CoherenceMetric(target=0.5)
        result = metric.compute([0.8, 0.85, 0.75, 0.9])
        assert 0.0 <= result.mean <= 1.0
        assert result.std >= 0.0

    @pytest.mark.fast
    def test_compare(self):
        """Test compare between two groups."""
        from cohezion.benchmarks.agentic_metrics import CoherenceMetric

        metric = CoherenceMetric()
        comp = metric.compare([0.8, 0.85], [0.5, 0.55])
        assert hasattr(comp, "p_value")
        assert hasattr(comp, "u_statistic")


class TestTRIUNEBalanceMetric:
    """Tests for TRIUNEBalanceMetric."""

    @pytest.mark.fast
    def test_compute_empty(self):
        """Test compute with empty lists."""
        from cohezion.benchmarks.agentic_metrics import TRIUNEBalanceMetric

        metric = TRIUNEBalanceMetric()
        result = metric.compute([], [], [])
        assert result.mean == 1.0


class TestStabilityMetric:
    """Tests for StabilityMetric."""

    @pytest.mark.fast
    def test_compute(self):
        """Test stability computation."""
        from cohezion.benchmarks.agentic_metrics import StabilityMetric

        metric = StabilityMetric()
        coherences = [0.5, 0.51, 0.52, 0.5, 0.49]
        hiho_dists = [0.1, 0.09, 0.08, 0.1, 0.11]
        result = metric.compute(coherences, hiho_dists)
        assert 0.0 <= result.mean <= 1.0


class TestExoticChargeMetric:
    """Tests for ExoticChargeMetric."""

    @pytest.mark.fast
    def test_compute_empty(self):
        """Test compute with empty list."""
        from cohezion.benchmarks.agentic_metrics import ExoticChargeMetric

        metric = ExoticChargeMetric()
        result = metric.compute([])
        assert result.mean == 0.0

    @pytest.mark.fast
    def test_compute(self):
        """Test exotic charge computation."""
        from cohezion.benchmarks.agentic_metrics import ExoticChargeMetric

        metric = ExoticChargeMetric()
        result = metric.compute([0.8, 0.85, 0.9])
        assert 0.0 <= result.mean <= 1.0


class TestKordylewskiOrbitMetric:
    """Tests for KordylewskiOrbitMetric."""

    @pytest.mark.fast
    def test_compute(self):
        """Test Kordylewski orbit computation."""
        from cohezion.benchmarks.agentic_metrics import KordylewskiOrbitMetric

        metric = KordylewskiOrbitMetric()
        result = metric.compute([0.1, 0.2, 0.15])
        assert 0.0 <= result.mean <= 1.0


class TestSPINPhaseMetric:
    """Tests for SPINPhaseMetric."""

    @pytest.mark.fast
    def test_compute_empty(self):
        """Test compute with too few values."""
        from cohezion.benchmarks.agentic_metrics import SPINPhaseMetric

        metric = SPINPhaseMetric()
        result = metric.compute([1.0])
        assert result.mean == 0.0


class TestEVOPhysicsMetrics:
    """Tests for EVOPhysicsMetrics."""

    @pytest.mark.fast
    def test_initialization(self):
        """Test EVOPhysicsMetrics initializes all sub-metrics."""
        from cohezion.benchmarks.agentic_metrics import EVOPhysicsMetrics

        metrics = EVOPhysicsMetrics()
        assert metrics.coherence is not None
        assert metrics.triune_balance is not None
        assert metrics.stability is not None
        assert metrics.exotic_charge is not None
        assert metrics.kordylewski_orbit is not None
        assert metrics.spin_phase is not None

    @pytest.mark.fast
    def test_compute_all_empty(self):
        """Test compute_all with empty biography."""
        from cohezion.benchmarks.agentic_metrics import EVOPhysicsMetrics

        metrics = EVOPhysicsMetrics()
        results = metrics.compute_all([])
        assert "coherence" in results
        assert "exotic_charge" in results
        assert "stability" in results

    @pytest.mark.fast
    def test_compute_all_with_biography(self):
        """Test compute_all with a biography."""
        from cohezion.benchmarks.agentic_metrics import EVOPhysicsMetrics

        metrics = EVOPhysicsMetrics()
        bio = [
            {"coherence": 0.8, "exotic_charge_density": 0.9, "phase": 1.0},
            {"coherence": 0.85, "exotic_charge_density": 0.92, "phase": 1.1},
        ]
        results = metrics.compute_all(bio)
        assert "coherence" in results
        assert "exotic_charge" in results
        assert "stability" in results
        assert "spin_phase" in results
        assert "triune_balance" in results
        assert "kordylewski_orbit" in results

    @pytest.mark.fast
    def test_compare_biographies(self):
        """Test compare_biographies returns StatisticalComparisons."""
        from cohezion.benchmarks.agentic_metrics import EVOPhysicsMetrics

        metrics = EVOPhysicsMetrics()
        bio1 = [{"coherence": 0.8, "exotic_charge_density": 0.9, "phase": 1.0}]
        bio2 = [{"coherence": 0.5, "exotic_charge_density": 0.3, "phase": 0.5}]
        comparisons = metrics.compare_biographies(bio1, bio2)
        assert "coherence" in comparisons
        assert hasattr(comparisons["coherence"], "p_value")


class TestBonferroniCorrection:
    """Tests for BonferroniCorrection."""

    @pytest.mark.fast
    def test_correct(self):
        """Test Bonferroni correction."""
        from cohezion.benchmarks.agentic_metrics import BonferroniCorrection

        bc = BonferroniCorrection(n_tests=6, alpha=0.05)
        p_values = [0.01, 0.03, 0.1, 0.5, 0.001, 0.04]
        corrected = bc.correct(p_values)
        assert len(corrected) == 6
        assert all(0.0 <= p <= 1.0 for p in corrected)

    @pytest.mark.fast
    def test_significant_mask(self):
        """Test significant_mask."""
        from cohezion.benchmarks.agentic_metrics import BonferroniCorrection

        bc = BonferroniCorrection(n_tests=6, alpha=0.05)
        p_values = [0.001, 0.02, 0.1, 0.5, 0.001, 0.02]
        mask = bc.significant_mask(p_values)
        assert len(mask) == 6
        assert isinstance(mask[0], bool)


class TestMannWhitneyU:
    """Tests for _mann_whitney_u helper."""

    @pytest.mark.fast
    def test_identical_groups(self):
        """Test Mann-Whitney with identical groups."""
        from cohezion.benchmarks.agentic_metrics import _mann_whitney_u

        g1 = np.array([0.8, 0.85, 0.82])
        g2 = np.array([0.8, 0.85, 0.82])
        result = _mann_whitney_u(g1, g2)
        assert result.p_value >= 0.0
        assert result.effect_size == 0.0

    @pytest.mark.fast
    def test_different_groups(self):
        """Test Mann-Whitney with different groups."""
        from cohezion.benchmarks.agentic_metrics import _mann_whitney_u

        g1 = np.array([0.9, 0.92, 0.91])
        g2 = np.array([0.3, 0.32, 0.31])
        result = _mann_whitney_u(g1, g2)
        assert result.p_value >= 0.0
        assert result.p_value <= 1.0
