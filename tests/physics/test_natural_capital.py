"""Tests for InVEST-inspired natural capital valuation on the 12D manifold."""

import numpy as np
import pytest

from cohezion.physics.natural_capital import (
    SEVENTH_GENERATION_HORIZON,
    NaturalCapitalValuation,
)


class TestHabitatQuality:
    """Habitat quality = 1 - 2|δ| where δ = coherence - 0.5."""

    def test_hiho_perfect_habitat(self):
        """At coherence=0.5 (HIHO), habitat quality is 1.0."""
        ncv = NaturalCapitalValuation()
        state = np.full(12, 0.5)
        result = ncv.evaluate(state, coherence=0.5)
        assert result.habitat_quality == pytest.approx(1.0)

    def test_zero_coherence_zero_habitat(self):
        """At coherence=0 or 1, habitat quality is 0.0."""
        ncv = NaturalCapitalValuation()
        state = np.full(12, 0.5)
        result = ncv.evaluate(state, coherence=0.0)
        assert result.habitat_quality == pytest.approx(0.0)
        result = ncv.evaluate(state, coherence=1.0)
        assert result.habitat_quality == pytest.approx(0.0)

    def test_partial_coherence_partial_habitat(self):
        ncv = NaturalCapitalValuation()
        state = np.full(12, 0.5)
        result = ncv.evaluate(state, coherence=0.3)
        assert 0.0 < result.habitat_quality < 1.0


class TestEcosystemServices:
    """Verify all 5 ecosystem service metrics."""

    def test_all_metrics_nonnegative(self):
        ncv = NaturalCapitalValuation()
        state = np.random.default_rng(42).normal(0.5, 0.1, 12)
        result = ncv.evaluate(state, coherence=0.5, connectivity=0.5)
        assert result.habitat_quality >= 0
        assert result.carbon_storage >= 0
        assert result.water_yield >= 0
        assert result.pollination >= 0
        assert result.sediment_retention >= 0
        assert result.total_natural_capital >= 0

    def test_flat_gauge_high_retention(self):
        """Zero gauge curvature → maximum sediment retention."""
        ncv = NaturalCapitalValuation()
        state = np.full(12, 0.5)
        result = ncv.evaluate(state, coherence=0.5, gauge_curvature=0.0)
        assert result.sediment_retention == pytest.approx(1.0)

    def test_high_curvature_low_retention(self):
        """High gauge curvature → low sediment retention."""
        ncv = NaturalCapitalValuation()
        state = np.full(12, 0.5)
        result = ncv.evaluate(state, coherence=0.5, gauge_curvature=100.0)
        assert result.sediment_retention < 0.05

    def test_total_capital_is_weighted_sum(self):
        ncv = NaturalCapitalValuation()
        state = np.full(12, 0.5)
        result = ncv.evaluate(state, coherence=0.5, connectivity=1.0, spore_density=1.0)
        expected = (
            0.3 * result.habitat_quality
            + 0.2 * result.carbon_storage
            + 0.2 * result.water_yield
            + 0.15 * result.pollination
            + 0.15 * result.sediment_retention
        )
        assert result.total_natural_capital == pytest.approx(expected)


class TestSeventhGeneration:
    """Verify the Haudenosaunee Seventh Generation projection."""

    def test_horizon_is_175(self):
        assert SEVENTH_GENERATION_HORIZON == 175

    def test_growing_capital_is_sustainable(self):
        ncv = NaturalCapitalValuation()
        state = np.full(12, 0.5)
        # Simulate growing capital (improving coherence over time)
        for c in np.linspace(0.3, 0.5, 20):
            ncv.evaluate(state, coherence=c)
        proj = ncv.seventh_generation_projection()
        assert proj.is_sustainable
        assert proj.projected_capital >= proj.current_capital
        assert proj.generations_until_depletion is None

    def test_declining_capital_unsustainable(self):
        ncv = NaturalCapitalValuation()
        state = np.full(12, 0.5)
        # Simulate declining capital (coherence drifting from HIHO)
        for c in np.linspace(0.5, 0.1, 20):
            ncv.evaluate(state, coherence=c)
        proj = ncv.seventh_generation_projection()
        assert not proj.is_sustainable
        assert proj.generations_until_depletion is not None

    def test_empty_history_returns_zero(self):
        ncv = NaturalCapitalValuation()
        proj = ncv.seventh_generation_projection()
        assert proj.current_capital == 0.0
        assert not proj.is_sustainable


class TestSerialization:
    def test_metrics_to_dict(self):
        ncv = NaturalCapitalValuation()
        state = np.full(12, 0.5)
        result = ncv.evaluate(state, coherence=0.5)
        data = result.to_dict()
        assert "habitat_quality" in data
        assert "total_natural_capital" in data

    def test_projection_to_dict(self):
        ncv = NaturalCapitalValuation()
        state = np.full(12, 0.5)
        ncv.evaluate(state, coherence=0.5)
        proj = ncv.seventh_generation_projection()
        data = proj.to_dict()
        assert "is_sustainable" in data
        assert "growth_rate" in data
