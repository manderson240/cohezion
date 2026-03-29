"""Tests for the Fisher information metric — the Rosetta Stone."""

import numpy as np
import pytest

from cohezion.physics.information_geometry import (
    FisherInformationMetric,
    compute_vae_fisher_metric,
)


class TestGaussianFisher:
    """Verify Fisher metric from Gaussian parameters."""

    def test_diagonal_metric(self):
        """Gaussian Fisher metric is diagonal for independent dimensions."""
        fisher = FisherInformationMetric(dim=4)
        sigma = np.array([1.0, 0.5, 2.0, 0.1])
        g = fisher.compute_from_gaussian(np.zeros(4), sigma)
        # Off-diagonal should be zero
        off_diag = g - np.diag(np.diag(g))
        np.testing.assert_allclose(off_diag, 0.0, atol=1e-15)

    def test_smaller_sigma_larger_fisher(self):
        """Smaller σ → larger Fisher information (more informative)."""
        fisher = FisherInformationMetric(dim=2)
        sigma_tight = np.array([0.1, 0.1])
        sigma_wide = np.array([1.0, 1.0])
        g_tight = fisher.compute_from_gaussian(np.zeros(2), sigma_tight)
        g_wide = fisher.compute_from_gaussian(np.zeros(2), sigma_wide)
        assert g_tight[0, 0] > g_wide[0, 0]

    def test_positive_definite(self):
        """Fisher metric is positive semi-definite."""
        fisher = FisherInformationMetric(dim=10)
        sigma = np.random.uniform(0.1, 2.0, 10)
        g = fisher.compute_from_gaussian(np.zeros(10), sigma)
        eigenvalues = np.linalg.eigvalsh(g)
        assert np.all(eigenvalues >= -1e-14)


class TestEigendecomposition:
    """Verify Fisher metric eigendecomposition."""

    def test_eigenvalues_sorted_descending(self):
        fisher = FisherInformationMetric(dim=8)
        sigma = np.array([0.1, 0.2, 0.5, 1.0, 2.0, 0.3, 0.7, 1.5])
        fisher.compute_from_gaussian(np.zeros(8), sigma)
        eigenvalues, _ = fisher.compute_eigendecomposition()
        assert np.all(eigenvalues[:-1] >= eigenvalues[1:])

    def test_eigenvectors_orthonormal(self):
        fisher = FisherInformationMetric(dim=5)
        sigma = np.random.uniform(0.1, 2.0, 5)
        fisher.compute_from_gaussian(np.zeros(5), sigma)
        _, eigvecs = fisher.compute_eigendecomposition()
        identity = eigvecs.T @ eigvecs
        np.testing.assert_allclose(identity, np.eye(5), atol=1e-12)


class TestProjection:
    """Verify Fisher-optimal projection."""

    def test_projection_shape(self):
        fisher = FisherInformationMetric(dim=256)
        sigma = np.random.uniform(0.1, 2.0, 256)
        fisher.compute_from_gaussian(np.zeros(256), sigma)
        z = np.random.randn(256)
        projected = fisher.project_to_submanifold(z, target_dim=12)
        assert projected.shape == (12,)

    def test_batch_projection_shape(self):
        fisher = FisherInformationMetric(dim=64)
        sigma = np.random.uniform(0.1, 2.0, 64)
        fisher.compute_from_gaussian(np.zeros(64), sigma)
        batch = np.random.randn(10, 64)
        projected = fisher.project_to_submanifold(batch, target_dim=12)
        assert projected.shape == (10, 12)

    def test_information_content_monotonic(self):
        """More components = more information captured."""
        fisher = FisherInformationMetric(dim=20)
        sigma = np.random.uniform(0.1, 2.0, 20)
        fisher.compute_from_gaussian(np.zeros(20), sigma)
        ic5 = fisher.information_content(5)
        ic10 = fisher.information_content(10)
        ic20 = fisher.information_content(20)
        assert ic5 <= ic10 <= ic20
        assert ic20 == pytest.approx(1.0)

    def test_12d_captures_most_information_for_peaked_spectrum(self):
        """When eigenvalue spectrum is peaked, 12D captures most info."""
        fisher = FisherInformationMetric(dim=256)
        # Make first 12 dimensions much more informative
        sigma = np.ones(256)
        sigma[:12] = 0.01  # Very tight → very informative
        fisher.compute_from_gaussian(np.zeros(256), sigma)
        ic = fisher.information_content(12)
        assert ic > 0.9  # 12D should capture >90% of info


class TestGeodesicDistance:
    """Verify Fisher-Rao geodesic distance."""

    def test_distance_is_nonnegative(self):
        fisher = FisherInformationMetric(dim=4)
        fisher.compute_from_gaussian(np.zeros(4), np.ones(4))
        d = fisher.geodesic_distance(np.zeros(4), np.ones(4))
        assert d >= 0

    def test_distance_is_zero_for_same_point(self):
        fisher = FisherInformationMetric(dim=4)
        fisher.compute_from_gaussian(np.zeros(4), np.ones(4))
        z = np.array([0.5, 0.5, 0.5, 0.5])
        d = fisher.geodesic_distance(z, z)
        assert d == pytest.approx(0.0, abs=1e-14)

    def test_distance_symmetric(self):
        fisher = FisherInformationMetric(dim=4)
        fisher.compute_from_gaussian(np.zeros(4), np.ones(4))
        z1 = np.array([0.0, 0.0, 0.0, 0.0])
        z2 = np.array([1.0, 1.0, 1.0, 1.0])
        assert fisher.geodesic_distance(z1, z2) == pytest.approx(fisher.geodesic_distance(z2, z1))


class TestNaturalGradient:
    """Verify natural gradient computation."""

    def test_natural_gradient_shape(self):
        fisher = FisherInformationMetric(dim=4)
        fisher.compute_from_gaussian(np.zeros(4), np.ones(4))
        grad = np.array([1.0, 2.0, 3.0, 4.0])
        nat_grad = fisher.natural_gradient(grad)
        assert nat_grad.shape == (4,)

    def test_natural_gradient_rescales_by_metric(self):
        """Natural gradient is larger in directions with small Fisher info."""
        fisher = FisherInformationMetric(dim=2)
        sigma = np.array([0.1, 10.0])  # dim 0 very informative, dim 1 not
        fisher.compute_from_gaussian(np.zeros(2), sigma)
        grad = np.array([1.0, 1.0])
        nat_grad = fisher.natural_gradient(grad)
        # Natural gradient should be smaller in informative direction (dim 0)
        # and larger in uninformative direction (dim 1)
        assert abs(nat_grad[1]) > abs(nat_grad[0])


class TestRiemannianConversion:
    """Verify conversion to RiemannianMetric."""

    def test_to_riemannian_metric_shape(self):
        fisher = FisherInformationMetric(dim=64)
        sigma = np.random.uniform(0.1, 2.0, 64)
        fisher.compute_from_gaussian(np.zeros(64), sigma)
        metric = fisher.to_riemannian_metric(target_dim=12)
        g = metric.evaluate(np.zeros(12))
        assert g.shape == (12, 12)

    def test_projected_metric_positive_definite(self):
        fisher = FisherInformationMetric(dim=64)
        sigma = np.random.uniform(0.1, 2.0, 64)
        fisher.compute_from_gaussian(np.zeros(64), sigma)
        metric = fisher.to_riemannian_metric(target_dim=12)
        g = metric.evaluate(np.zeros(12))
        eigenvalues = np.linalg.eigvalsh(g)
        assert np.all(eigenvalues >= -1e-10)


class TestVAEConvenience:
    """Verify the VAE convenience function."""

    def test_compute_vae_fisher_metric(self):
        mu = np.zeros(256)
        logvar = np.zeros(256)  # σ = 1 everywhere
        fisher = compute_vae_fisher_metric(mu, logvar)
        ic = fisher.information_content(12)
        assert 0 <= ic <= 1
