r"""FLUME VAE — Fluid Latent Understanding through Manifold Encoding Engine
========================================================================
Implements FLUME Variational Autoencoder operating over 2048D Poincaré space,
encoding 2048D states into 256D latent distributions (mu, log_var) and decoding back
to the hyperbolic manifold.

Formulation:
  - Encoder: q_\phi(z | x) -> (\mu_z, \log \sigma^2_z)
  - Reparameterization: z = \mu + \sigma \odot \epsilon,  \epsilon ~ N(0, I)
  - Decoder: p_\theta(x | z) -> \hat{x} \in B^{2048}
  - Loss: L_{FLUME} = ||x - \hat{x}||^2 + \beta * D_{KL}(q(z|x) || p(z))
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from cohezion.contracts import PoincarePoint
from cohezion.physics.poincare_manifold import PoincareManifoldND


@dataclass(frozen=True, slots=True)
class FLUMEEncoding:
    mu: tuple[float, ...]  # 256D mean vector
    log_var: tuple[float, ...]  # 256D log variance vector
    latent_z: tuple[float, ...]  # 256D sampled latent point
    kl_divergence: float


@dataclass(frozen=True, slots=True)
class FLUMEReconstruction:
    reconstructed_point: PoincarePoint
    reconstruction_loss: float
    total_flume_loss: float


class FLUMEVAE:
    """FLUME Variational Autoencoder over Poincaré Manifold States."""

    def __init__(self, state_dim: int = 2048, latent_dim: int = 256, beta: float = 0.1) -> None:
        self.state_dim = state_dim
        self.latent_dim = latent_dim
        self.beta = beta
        self.stride = state_dim // latent_dim

    def encode(self, soul_point: PoincarePoint) -> FLUMEEncoding:
        """Encode 2048D Poincaré state into 256D latent Gaussian distribution (mu, log_var)."""
        if soul_point.dim != self.state_dim:
            raise ValueError(f"Expected {self.state_dim}D Poincaré state, got {soul_point.dim}D")

        mu_list = []
        logvar_list = []

        for i in range(self.latent_dim):
            chunk = soul_point.coords[i * self.stride : (i + 1) * self.stride]
            mean_val = sum(chunk) / self.stride
            var_val = sum((x - mean_val) ** 2 for x in chunk) / self.stride
            log_var = math.log(max(1e-6, var_val))

            mu_list.append(mean_val)
            logvar_list.append(log_var)

        mu = tuple(mu_list)
        log_var = tuple(logvar_list)

        # Reparameterization trick (deterministic proxy epsilon = 0.1)
        eps = 0.1
        latent_z = tuple(m + (math.exp(0.5 * lv) * eps) for m, lv in zip(mu, log_var, strict=True))

        # KL Divergence D_KL = -0.5 * sum(1 + log_var - mu^2 - exp(log_var))
        kl = (
            -0.5
            * sum(1.0 + lv - (m**2) - math.exp(lv) for m, lv in zip(mu, log_var, strict=True))
            / self.latent_dim
        )

        return FLUMEEncoding(mu=mu, log_var=log_var, latent_z=latent_z, kl_divergence=round(kl, 4))

    def decode(self, encoding: FLUMEEncoding, original_point: PoincarePoint) -> FLUMEReconstruction:
        """Decode 256D latent z back to 2048D Poincaré space."""
        reconstructed_coords = []
        for z_val in encoding.latent_z:
            reconstructed_coords.extend([z_val] * self.stride)

        rec_point = PoincareManifoldND.project(reconstructed_coords, target_dim=self.state_dim)

        # Compute Reconstruction Loss ||x - \hat{x}||^2
        rec_loss = (
            sum(
                (x - x_hat) ** 2
                for x, x_hat in zip(original_point.coords, rec_point.coords, strict=True)
            )
            / self.state_dim
        )

        total_loss = rec_loss + (self.beta * encoding.kl_divergence)

        return FLUMEReconstruction(
            reconstructed_point=rec_point,
            reconstruction_loss=round(rec_loss, 6),
            total_flume_loss=round(total_loss, 6),
        )
