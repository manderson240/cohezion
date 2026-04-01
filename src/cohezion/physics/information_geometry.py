"""Information geometry — the Fisher metric bridge.

The Fisher information metric is the Rosetta Stone connecting:
  1. FLUME's 256D latent space (natural geometry of the VAE)
  2. The 12D axiomatic manifold (Riemannian metric for dynamics)
  3. Thermodynamic space (F, S, T, χ, Cv are metric-derived quantities)
  4. The 256D → 12D projection (Fisher-optimal dimensionality reduction)

The Fisher metric on a statistical manifold parameterized by θ:
    g_ij(θ) = E[(∂ log p(x|θ)/∂θ_i)(∂ log p(x|θ)/∂θ_j)]

For a VAE with Gaussian posterior q(z|x) = N(μ(x), σ²(x)):
    g_ij = (∂μ/∂θ_i)(∂μ/∂θ_j) / σ² + ½(∂log σ²/∂θ_i)(∂log σ²/∂θ_j)

The natural gradient (Amari, 1998) is:
    θ_new = θ - η · g⁻¹(θ) · ∇L

References:
    - Amari (1998): Natural gradient works efficiently in learning
    - Crooks (2007): Measuring thermodynamic length
    - Ay et al. (2017): Information Geometry
"""

from __future__ import annotations

import logging

import numpy as np

from cohezion.physics.riemannian_metric import RiemannianMetric


logger = logging.getLogger(__name__)


class FisherInformationMetric:
    """Fisher-Rao metric on the statistical manifold.

    Provides the principled bridge between high-dimensional latent spaces
    and the 12D axiomatic manifold. The Fisher metric is the UNIQUE
    Riemannian metric (up to scaling) that is invariant under sufficient
    statistics — it captures exactly the information that matters.

    Parameters
    ----------
    dim : int
        Dimension of the parameter space.
    """

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim
        self._cached_metric: np.ndarray | None = None
        self._cached_eigenvalues: np.ndarray | None = None
        self._cached_eigenvectors: np.ndarray | None = None

    def compute_from_gaussian(self, mu: np.ndarray, sigma: np.ndarray) -> np.ndarray:
        """Compute diagonal Fisher metric from Gaussian parameters.

        For q(z|x) = N(μ, diag(σ²)):
            g_ii = 1/σ_i² + 2/σ_i²  (from mean + variance terms)
            g_ij = 0 for i ≠ j      (diagonal due to independence)

        Parameters
        ----------
        mu : np.ndarray, shape (dim,)
            Mean vector of the Gaussian.
        sigma : np.ndarray, shape (dim,)
            Standard deviation vector (NOT variance).

        Returns
        -------
        np.ndarray, shape (dim, dim)
            Diagonal Fisher information matrix.
        """
        sigma_sq = np.maximum(sigma**2, 1e-10)
        # Fisher for Gaussian: g_ii = 1/σ² (from mean) + 1/(2σ⁴) * 2σ² = 1/σ² + 1/σ²
        # Simplified: g_ii = 2/σ²
        diag_values = 2.0 / sigma_sq
        self._cached_metric = np.diag(diag_values)
        self._invalidate_eigen_cache()
        return self._cached_metric

    def compute_from_jacobian(self, jacobian: np.ndarray, sigma: np.ndarray) -> np.ndarray:
        """Compute Fisher metric from encoder Jacobian.

        g_ij = (J^T J)_ij / σ² where J = ∂μ/∂θ

        Parameters
        ----------
        jacobian : np.ndarray, shape (latent_dim, param_dim)
            Jacobian of the encoder mean: J_ij = ∂μ_i/∂θ_j.
        sigma : np.ndarray, shape (latent_dim,)
            Standard deviations of the posterior.

        Returns
        -------
        np.ndarray, shape (param_dim, param_dim)
            Fisher information matrix.
        """
        sigma_sq = np.maximum(sigma**2, 1e-10)
        # Weight each row of the Jacobian by 1/σ_i
        weighted_J = jacobian / sigma_sq[:, np.newaxis]
        self._cached_metric = jacobian.T @ weighted_J
        self._invalidate_eigen_cache()
        return self._cached_metric

    def compute_eigendecomposition(self) -> tuple[np.ndarray, np.ndarray]:
        """Eigendecompose the Fisher metric: g = UΛU^T.

        Returns eigenvalues (sorted descending) and eigenvectors.
        The top-k eigenvectors define the Fisher-optimal subspace.
        """
        if self._cached_metric is None:
            raise ValueError(
                "Compute metric first via compute_from_gaussian or compute_from_jacobian"
            )

        if self._cached_eigenvalues is None:
            eigenvalues, eigenvectors = np.linalg.eigh(self._cached_metric)
            # Sort descending
            idx = np.argsort(eigenvalues)[::-1]
            self._cached_eigenvalues = eigenvalues[idx]
            self._cached_eigenvectors = eigenvectors[:, idx]

        return self._cached_eigenvalues, self._cached_eigenvectors

    def project_to_submanifold(self, z: np.ndarray, target_dim: int = 12) -> np.ndarray:
        """Fisher-optimal projection from high-D to target_dim.

        Projects z onto the top-k eigenvectors of the Fisher metric.
        This preserves the most statistically informative directions.

        Parameters
        ----------
        z : np.ndarray, shape (dim,) or (batch, dim)
            Point(s) in the full latent space.
        target_dim : int
            Target dimension for projection.

        Returns
        -------
        np.ndarray, shape (target_dim,) or (batch, target_dim)
        """
        eigenvalues, eigenvectors = self.compute_eigendecomposition()
        # Take top target_dim eigenvectors
        projection_matrix = eigenvectors[:, :target_dim]  # (dim, target_dim)

        if z.ndim == 1:
            return z @ projection_matrix
        return z @ projection_matrix

    def information_content(self, n_components: int | None = None) -> float:
        """Fraction of total Fisher information captured by top-n components.

        Parameters
        ----------
        n_components : int or None
            Number of components. Default: 12 (axiomatic dim).

        Returns
        -------
        float in [0, 1]. 1.0 = all information captured.
        """
        eigenvalues, _ = self.compute_eigendecomposition()
        if n_components is None:
            n_components = min(12, len(eigenvalues))

        total = np.sum(np.abs(eigenvalues))
        if total < 1e-15:
            return 0.0

        captured = np.sum(np.abs(eigenvalues[:n_components]))
        return float(captured / total)

    def geodesic_distance(self, z1: np.ndarray, z2: np.ndarray) -> float:
        """Compute Fisher-Rao geodesic distance between two points.

        For diagonal Fisher metric, this has a closed form:
        d(z1, z2) = sqrt(Σ_i g_ii * (z1_i - z2_i)²)

        This is the thermodynamic distance — the minimum work required
        to transform state z1 into state z2.
        """
        if self._cached_metric is None:
            raise ValueError("Compute metric first")

        diff = z1 - z2
        return float(np.sqrt(diff @ self._cached_metric @ diff))

    def natural_gradient(self, gradient: np.ndarray) -> np.ndarray:
        """Compute the natural gradient: g⁻¹ · ∇L.

        The natural gradient is the steepest descent direction on the
        statistical manifold — coordinate-invariant, unlike ordinary gradients.
        Converges faster and avoids pathological curvature.

        Parameters
        ----------
        gradient : np.ndarray
            Ordinary (Euclidean) gradient ∇L.

        Returns
        -------
        np.ndarray
            Natural gradient g⁻¹∇L.
        """
        if self._cached_metric is None:
            raise ValueError("Compute metric first")

        g_inv = np.linalg.inv(self._cached_metric + 1e-8 * np.eye(len(self._cached_metric)))
        return g_inv @ gradient

    def to_riemannian_metric(self, target_dim: int = 12) -> RiemannianMetric:
        """Convert the Fisher metric to a RiemannianMetric for Lagrangian dynamics.

        Projects the full Fisher metric to target_dim and wraps it
        as a constant RiemannianMetric.
        """
        eigenvalues, eigenvectors = self.compute_eigendecomposition()
        # Project Fisher metric to target_dim
        P = eigenvectors[:, :target_dim]  # (dim, target_dim)
        projected_g = P.T @ self._cached_metric @ P  # (target_dim, target_dim)
        return RiemannianMetric(target_dim, projected_g)

    def _invalidate_eigen_cache(self) -> None:
        self._cached_eigenvalues = None
        self._cached_eigenvectors = None


def compute_vae_fisher_metric(
    mu: np.ndarray,
    logvar: np.ndarray,
) -> FisherInformationMetric:
    """Create a Fisher metric from VAE encoder outputs.

    Convenience function that takes the standard VAE outputs
    (μ, log σ²) and computes the diagonal Fisher metric.

    Parameters
    ----------
    mu : np.ndarray, shape (dim,)
        Encoder mean.
    logvar : np.ndarray, shape (dim,)
        Encoder log-variance.

    Returns
    -------
    FisherInformationMetric with computed diagonal metric.
    """
    sigma = np.exp(0.5 * logvar)
    fisher = FisherInformationMetric(dim=len(mu))
    fisher.compute_from_gaussian(mu, sigma)
    return fisher


__all__ = [
    "FisherInformationMetric",
    "compute_vae_fisher_metric",
]
