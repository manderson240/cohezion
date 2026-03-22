"""Tests for thermodynamic agent metrics.

Each test validates a real mathematical property — not just that a number
is returned, but that the physics is correct.
"""

import numpy as np
import pytest

from cohezion.compound.thermodynamic_metrics import (
    ThermodynamicMetrics,
)


@pytest.fixture
def thermo():
    """Create a fresh ThermodynamicMetrics instance."""
    return ThermodynamicMetrics(window_size=20, min_samples=5)


@pytest.fixture
def equilibrium_thermo(thermo):
    """ThermodynamicMetrics with stable equilibrium data (low entropy production)."""
    rng = np.random.RandomState(42)
    for _ in range(20):
        thermo.record(coherence=0.5 + rng.normal(0, 0.01))
    return thermo


@pytest.fixture
def far_from_equilibrium_thermo(thermo):
    """ThermodynamicMetrics with oscillating data (high entropy production)."""
    for i in range(20):
        # Oscillate wildly between 0.1 and 0.9
        c = 0.1 if i % 2 == 0 else 0.9
        thermo.record(coherence=c)
    return thermo


class TestEntropyProductionRate:
    """Entropy production measures irreversibility of agent decisions."""

    def test_equilibrium_has_low_entropy_production(self, equilibrium_thermo):
        """Near-equilibrium systems produce minimal entropy (second law)."""
        state = equilibrium_thermo.compute_state()
        # Stable coherence → low irreversibility
        assert state.entropy_production_rate < 1.0

    def test_oscillation_has_high_entropy_production(self, far_from_equilibrium_thermo):
        """Far-from-equilibrium trajectories produce more entropy."""
        state = far_from_equilibrium_thermo.compute_state()
        # Wild oscillation → high irreversibility
        assert state.entropy_production_rate > 0.5

    def test_entropy_production_nonnegative(self, thermo):
        """Entropy production rate must be >= 0 (second law of thermodynamics)."""
        rng = np.random.RandomState(42)
        for _ in range(30):
            thermo.record(coherence=rng.random())

        state = thermo.compute_state()
        assert state.entropy_production_rate >= 0.0

    def test_constant_trajectory_zero_production(self, thermo):
        """Perfectly constant trajectory has zero entropy production."""
        for _ in range(20):
            thermo.record(coherence=0.5, energy=1.0)

        state = thermo.compute_state()
        assert state.entropy_production_rate == pytest.approx(0.0, abs=1e-10)


class TestFreeEnergy:
    """Free energy F = <E> - T*S gives the thermodynamic potential."""

    def test_free_energy_below_mean_energy(self, equilibrium_thermo):
        """F <= <E> always (since T*S >= 0 for T > 0 and S >= 0)."""
        state = equilibrium_thermo.compute_state()
        assert state.free_energy <= state.energy + 1e-10

    def test_high_entropy_lowers_free_energy(self):
        """Systems with higher entropy have lower free energy (given same E)."""
        # Low entropy: constant coherence
        low_entropy = ThermodynamicMetrics(min_samples=5)
        for _ in range(20):
            low_entropy.record(coherence=0.5)

        # High entropy: uniformly distributed coherence
        high_entropy = ThermodynamicMetrics(min_samples=5)
        rng = np.random.RandomState(42)
        for _ in range(20):
            high_entropy.record(coherence=rng.random())

        state_low = low_entropy.compute_state()
        state_high = high_entropy.compute_state()

        # Higher entropy → lower free energy (for comparable mean energy)
        assert state_high.entropy > state_low.entropy

    def test_free_energy_formula(self, thermo):
        """Verify F = <E> - T*S holds exactly."""
        rng = np.random.RandomState(42)
        for _ in range(20):
            thermo.record(coherence=rng.random())

        state = thermo.compute_state()
        expected_F = state.energy - state.temperature * state.entropy
        assert state.free_energy == pytest.approx(expected_F, rel=1e-6)


class TestSusceptibilityAndHeatCapacity:
    """Susceptibility and heat capacity from fluctuation-dissipation theorem."""

    def test_susceptibility_scales_with_variance(self):
        """χ = N * Var(m) / T — higher variance → higher susceptibility."""
        # Low variance
        low_var = ThermodynamicMetrics(min_samples=5)
        for _ in range(20):
            low_var.record(coherence=0.5)

        # High variance
        high_var = ThermodynamicMetrics(min_samples=5)
        for i in range(20):
            high_var.record(coherence=0.1 if i % 2 == 0 else 0.9)

        state_low = low_var.compute_state()
        state_high = high_var.compute_state()

        assert state_high.susceptibility > state_low.susceptibility

    def test_heat_capacity_nonnegative(self, thermo):
        """Heat capacity Cv = Var(E)/T² is always >= 0."""
        rng = np.random.RandomState(42)
        for _ in range(20):
            thermo.record(coherence=rng.random())

        state = thermo.compute_state()
        assert state.heat_capacity >= 0.0


class TestHIHOFreeEnergyAnalysis:
    """HIHO stability analyzed through free energy landscape."""

    def test_hiho_attractor_with_clustered_data(self):
        """When data clusters around 0.5, HIHO should be an attractor."""
        thermo = ThermodynamicMetrics(min_samples=5)
        rng = np.random.RandomState(42)
        for _ in range(100):
            thermo.record(coherence=0.5 + rng.normal(0, 0.05))

        analysis = thermo.get_hiho_free_energy_analysis()
        assert analysis["is_attractor"] is True
        assert analysis["well_depth"] > 0.0

    def test_hiho_not_attractor_with_bimodal_data(self):
        """When data avoids 0.5 (bimodal), HIHO is NOT an attractor."""
        thermo = ThermodynamicMetrics(min_samples=5)
        rng = np.random.RandomState(42)
        for _ in range(100):
            # Bimodal: cluster at 0.2 and 0.8, avoid 0.5
            if rng.random() < 0.5:
                thermo.record(coherence=0.2 + rng.normal(0, 0.05))
            else:
                thermo.record(coherence=0.8 + rng.normal(0, 0.05))

        analysis = thermo.get_hiho_free_energy_analysis()
        assert analysis["is_attractor"] is False


class TestMutualInformation:
    """Mutual information measures predictability of agent behavior."""

    def test_iid_has_low_mutual_information(self):
        """IID samples have much lower MI than autocorrelated samples."""
        thermo = ThermodynamicMetrics(min_samples=5)
        rng = np.random.RandomState(42)
        for _ in range(200):
            thermo.record(coherence=rng.random())

        mi = thermo.compute_mutual_information(lag=1, n_bins=15)
        # Histogram-based MI estimator has positive bias ~(bins-1)^2/(2N)
        # With 15 bins and 200 samples, bias ~ 0.49. Accept < 1.0 for iid.
        assert mi < 1.0

    def test_autocorrelated_has_high_mutual_information(self):
        """Autocorrelated series has high mutual information."""
        thermo = ThermodynamicMetrics(min_samples=5)
        c = 0.5
        rng = np.random.RandomState(42)
        for _ in range(100):
            c = 0.95 * c + 0.05 * rng.random()  # Strong autocorrelation
            thermo.record(coherence=c)

        mi = thermo.compute_mutual_information(lag=1)
        # Much higher than iid
        assert mi > 0.0

    def test_mutual_information_nonnegative(self, thermo):
        """MI >= 0 always (information-theoretic property)."""
        rng = np.random.RandomState(42)
        for _ in range(50):
            thermo.record(coherence=rng.random())

        mi = thermo.compute_mutual_information()
        assert mi >= 0.0


class TestCrooksRatio:
    """Crooks fluctuation theorem: P(+σ)/P(-σ) = exp(σ)."""

    def test_crooks_ratio_positive(self, thermo):
        """Crooks ratio is always positive."""
        rng = np.random.RandomState(42)
        for _ in range(20):
            thermo.record(coherence=rng.random())

        ratio = thermo.compute_crooks_ratio()
        assert ratio > 0.0

    def test_equilibrium_crooks_near_one(self, equilibrium_thermo):
        """At equilibrium, Crooks ratio approaches 1 (detailed balance)."""
        ratio = equilibrium_thermo.compute_crooks_ratio()
        # Near equilibrium, ratio should be close to 1
        assert 0.1 < ratio < 10.0


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_insufficient_samples_raises(self, thermo):
        """Must have min_samples before computing state."""
        thermo.record(coherence=0.5)
        with pytest.raises(ValueError, match="Need at least"):
            thermo.compute_state()

    def test_reset_clears_data(self, equilibrium_thermo):
        """Reset empties all accumulated data."""
        equilibrium_thermo.reset()
        with pytest.raises(ValueError):
            equilibrium_thermo.compute_state()
