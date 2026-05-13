"""Manifold translation layer for the EcoResilience swarm.
Bridges the gap between FLUME 256D latent space and the 12D Unified Physics manifold.

Sensing -> FLUME (256D) -> Manifold Projection (12D) -> HIHO Stability Check.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from cohezion.flume.vae_encoder import FlumeVAEEncoder


class ManifoldProjection(BaseModel):
    """Observation result of a manifold projection.
    Represents the state of a biological or physical system in 12D coordinates.
    """

    model_config = {"arbitrary_types_allowed": True}

    coordinates: np.ndarray = Field(
        default_factory=lambda: np.zeros(12), description="12D state vector"
    )
    coherence: float = Field(default=0.0, description="HIHO coherence score (0.0-1.0)")
    stability: bool = Field(default=False, description="Whether the projected state is stable")

    def __repr__(self) -> str:
        return f"ManifoldProjection(coords={self.coordinates}, coherence={self.coherence:.3f}, stable={self.stability})"


class ManifoldTranslator:
    """Translates FLUME latents into 12D Unified Physics coordinates.

    This class implements the projection mapping: R^256 -> R^12.
    In a real-world scenario, this would be a trained linear projection or a small
    MLP. Here, we implement a deterministic projection based on the
    cohezion-flume latent structure.
    """

    def __init__(self, encoder: FlumeVAEEncoder | None = None):
        self.encoder = encoder
        # The projection matrix P is a fixed deterministic mapping for the 256D -> 12D projection.
        # We use a seed for reproducibility.
        np.random.seed(42)
        self._projection_matrix = np.random.randn(12, 256) * 0.1
        self._stability_threshold = 0.5  # HIHO stability floor

    def project(self, latent: np.ndarray) -> ManifoldProjection:
        """Projects a 256D FLUME latent vector into a 12D state coordinate.

        Args:
            latent: The 256D latent vector from the VAE encoder.
        """
        if latent.shape != (256,):
            raise ValueError(f"Expected 256D latent vector, got {latent.shape}")

        # Project to 12D
        coords = np.dot(self._projection_matrix, latent)

        # Calculate HIHO coherence (Simplified as a normalized energy function of the 12D projection)
        # In reality, this is the 12D manifold stability check.
        coherence = np.linalg.norm(coords) / (
            np.linalg.norm(self._projection_matrix) * np.linalg.norm(latent)
        )

        # Check stability
        stability = coherence >= self._stability_threshold

        return ManifoldProjection(coordinates=coords, coherence=coherence, stability=stability)

    def synthesize_to_latent(self, coords: np.ndarray) -> np.ndarray:
        """Reverse projection: Map 12D state coordinates back to a 256D FLUME latent.
        This is for the 'Steering' phase of the simulation.
        """
        # Use Moore-Penrose pseudo-inverse of the projection matrix
        projection_inv = np.linalg.pinv(self._projection_matrix)
        return np.dot(projection_inv, coords)

    async def encode_to_manifold(self, text: str) -> tuple[np.ndarray, ManifoldProjection]:
        """Helper method to encode text directly to a manifold projection.

        Args:
            text: The input text string.
        """
        if self.encoder is None:
            raise RuntimeError("VAEEncoder not initialized in ManifoldTranslator")

        latent = self.encoder.encode(text)
        projection = self.project(self.project(latent))  # Double projection for stability check

        return latent, projection

    def __repr__(self) -> str:
        return f"ManifoldTranslator(projection_matrix_shape={self._projection_matrix.shape})"
