# ruff: noqa: E501  # long lines: SQL/URLs/docstrings — wrapping reduces readability
import logging

import torch
import torch.nn as nn


logger = logging.getLogger(__name__)


class DomainAlignmentMLP(nn.Module):
    """Small MLP to map between latent manifold regions."""

    def __init__(self, z_dim: int = 256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(z_dim, z_dim * 2),
            nn.ReLU(),
            nn.Linear(z_dim * 2, z_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.net(x)  # Residual connection


class LatentAligner:
    """
    Bridges conceptual domains by mapping thought-vectors between different
    manifold sub-spaces (e.g., Physics ↔ Biology).
    """

    def __init__(self, z_dim: int = 256):
        self.z_dim = z_dim
        self.aligners: dict[str, DomainAlignmentMLP] = {}
        # Stores average vectors for each domain to compute base translations
        self.domain_centroids: dict[str, torch.Tensor] = {}

    def get_aligner(self, source_domain: str, target_domain: str) -> DomainAlignmentMLP:
        """Retrieves or creates a mapping module between two domains."""
        key = f"{source_domain}_to_{target_domain}"
        if key not in self.aligners:
            logger.info(f"✨ Initializing alignment bridge: {key}")
            self.aligners[key] = DomainAlignmentMLP(self.z_dim)
        return self.aligners[key]

    def align(self, vector: torch.Tensor, source_domain: str, target_domain: str) -> torch.Tensor:
        """
        Translates a thought-vector from source domain context to target domain context.
        """
        aligner = self.get_aligner(source_domain, target_domain)

        is_single = vector.dim() == 1
        if is_single:
            vector = vector.unsqueeze(0)

        with torch.no_grad():
            aligned_vector = aligner(vector)

        if is_single:
            return aligned_vector.squeeze(0)
        return aligned_vector

    def register_centroid(self, domain: str, vectors: torch.Tensor):
        """Update the known center of a domain's conceptual manifold."""
        if vectors.dim() == 1:
            vectors = vectors.unsqueeze(0)

        current_mean = vectors.mean(dim=0)
        if domain not in self.domain_centroids:
            self.domain_centroids[domain] = current_mean
        else:
            # Running average update (ema)
            self.domain_centroids[domain] = 0.9 * self.domain_centroids[domain] + 0.1 * current_mean

    def domain_shift(
        self, vector: torch.Tensor, source_domain: str, target_domain: str
    ) -> torch.Tensor:
        """
        Applies a simple centroid-based shift as a fast approximation of alignment.
        """
        if source_domain not in self.domain_centroids or target_domain not in self.domain_centroids:
            logger.warning(
                f"⚠️ Centroids missing for {source_domain} or {target_domain}. Returning original vector."
            )
            return vector

        shift = self.domain_centroids[target_domain] - self.domain_centroids[source_domain]
        return vector + shift
