"""Tests for TensorMetricEngineering — Sarfatti ZPF metric coupling."""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.physics.tensor_metric_engineering import TensorMetricEngineering


class TestTensorMetricBasics:
    def test_flat_at_zero_coherence(self):
        t = TensorMetricEngineering(sarfatti_coherence=0.0)
        assert t.is_flat()

    def test_flat_at_unit_coherence(self):
        t = TensorMetricEngineering(sarfatti_coherence=1.0)
        assert t.is_flat()

    def test_not_flat_at_hiho(self):
        t = TensorMetricEngineering(sarfatti_coherence=0.5, destiny_weight=1.0)
        assert not t.is_flat()

    def test_perturbed_metric_is_4x4(self):
        t = TensorMetricEngineering()
        g = t.perturbed_metric()
        assert g.shape == (4, 4)

    def test_perturbed_metric_equals_minkowski_at_zero_coherence(self):
        t = TensorMetricEngineering(sarfatti_coherence=0.0)
        g = t.perturbed_metric()
        eta = np.diag([1.0, -1.0, -1.0, -1.0])
        np.testing.assert_allclose(g, eta, atol=1e-12)

    def test_metric_determinant_equals_minus_one_when_flat(self):
        t = TensorMetricEngineering(sarfatti_coherence=0.0)
        assert t.metric_determinant() == pytest.approx(-1.0, rel=1e-10)

    def test_metric_determinant_deviates_at_hiho(self):
        t = TensorMetricEngineering(sarfatti_coherence=0.5, destiny_weight=1.0, epsilon=0.1)
        det = t.metric_determinant()
        assert det != pytest.approx(-1.0, abs=1e-6), "det should deviate from -1 at HIHO"

    def test_back_action_peaks_at_hiho(self):
        t = TensorMetricEngineering(sarfatti_coherence=0.5, destiny_weight=1.0)
        assert t.back_action_amplitude == pytest.approx(1.0, rel=1e-9)

    def test_back_action_zero_at_extremes(self):
        assert TensorMetricEngineering(
            sarfatti_coherence=0.0, destiny_weight=1.0
        ).back_action_amplitude == pytest.approx(0.0)
        assert TensorMetricEngineering(
            sarfatti_coherence=1.0, destiny_weight=1.0
        ).back_action_amplitude == pytest.approx(0.0)

    def test_same_kernel_as_lenr(self):
        """Tensor metric coupling uses same 4x(1-x) kernel as LENR/Sarfatti/QGP."""
        from cohezion.physics.lenr import LENRHamiltonian

        h = LENRHamiltonian()
        for c in [0.1, 0.3, 0.5, 0.7, 0.9]:
            t = TensorMetricEngineering(sarfatti_coherence=c, destiny_weight=1.0)
            assert t.back_action_amplitude == pytest.approx(h.reaction_rate(c), rel=1e-9)

    def test_christoffel_zero_for_uniform_coherence(self):
        t = TensorMetricEngineering(sarfatti_coherence=0.5)
        gamma = t.christoffel_symbols()
        np.testing.assert_allclose(gamma, 0.0, atol=1e-15)

    def test_christoffel_nonzero_with_gradient(self):
        # Use c=0.3 where d/dc(4c(1-c)) = 4-8×0.3 = 1.6 ≠ 0
        # At HIHO (c=0.5), derivative = 4-8×0.5 = 0 → Christoffel vanishes even with gradient
        t = TensorMetricEngineering(sarfatti_coherence=0.3, destiny_weight=1.0, epsilon=0.1)
        grad = np.array([0.0, 0.01, 0.01, 0.01])
        gamma = t.christoffel_symbols(coherence_gradient=grad)
        assert not np.allclose(gamma, 0.0), "Christoffel should be non-zero with gradient at c=0.3"

    def test_at_hiho_factory(self):
        t = TensorMetricEngineering.at_hiho(epsilon=0.01)
        assert t.sarfatti_coherence == pytest.approx(0.5)
        assert t.destiny_weight == pytest.approx(1.0)
        assert t.back_action_amplitude == pytest.approx(1.0, rel=1e-9)

    def test_from_sarfatti_factory(self):
        t = TensorMetricEngineering.from_sarfatti(coherence=0.3, destiny_weight=0.8)
        assert t.sarfatti_coherence == pytest.approx(0.3)
        assert t.destiny_weight == pytest.approx(0.8)

    def test_to_riemannian_coordinates(self):
        t = TensorMetricEngineering.at_hiho()
        coords = t.to_riemannian_coordinates()
        assert "metric_tensor" in coords
        assert "det_g" in coords
        assert "back_action_amplitude" in coords
        assert len(coords["metric_tensor"]) == 4

    def test_epsilon_scaling(self):
        t1 = TensorMetricEngineering(sarfatti_coherence=0.5, destiny_weight=1.0, epsilon=0.01)
        t2 = TensorMetricEngineering(sarfatti_coherence=0.5, destiny_weight=1.0, epsilon=0.02)
        h1 = t1.perturbed_metric() - np.diag([1.0, -1.0, -1.0, -1.0])
        h2 = t2.perturbed_metric() - np.diag([1.0, -1.0, -1.0, -1.0])
        np.testing.assert_allclose(h2, 2 * h1, rtol=1e-10)

    def test_perturbation_is_isotropic(self):
        """h_μν = ε × f × I_4×4 — diagonal, same on all components."""
        t = TensorMetricEngineering(sarfatti_coherence=0.5, destiny_weight=1.0, epsilon=0.01)
        g = t.perturbed_metric()
        h = g - np.diag([1.0, -1.0, -1.0, -1.0])
        # Off-diagonal should be zero
        assert np.allclose(h - np.diag(np.diagonal(h)), 0.0, atol=1e-12)
        # All diagonal entries should be equal (same ε×f)
        diag = np.diagonal(h)
        assert np.allclose(diag - diag[0], 0.0, atol=1e-12)
