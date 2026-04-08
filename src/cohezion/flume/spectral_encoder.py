"""Spectral-Symphony Encoder for the EcoResilience swarm.
Bypasses the text-bottleneck by mapping Copernicus spectral indices
directly into the FLUME latent space (R^256).
"""

from __future__ import annotations

import logging
import numpy as np
from typing import Any, Dict, Tuple
from pydantic import BaseModel

from cohezion.compound.copernicus_bridge import CopernicusState
from cohezion.flume.vae_encoder import FlumeVAEEncoder

logger = logging.getLogger(__name__)


class SpectralEncoder:
    """
    Maps raw spectral data from Copernicus to a 256D FLUME latent vector.
    EnsTures that the 'Sensing' regime is grounded in biophysical reality
    without the noise of textual translation.
    """

    def __init__(self, encoder: FlumeVAEEncoder):
        self.encoder = encoder
        # Deterministic projection matrix for spectral indices -> latent space
        # we use a seed to ensure the mapping is consistent across the swarm
        np.random.seed(1337)
        self._projection_matrix = np.random.randn(256, 5) * 0.1  # 5 indices: NDVI, NDWI, SALI, etc.

    def encode_spectral_state(self, state: CopernicusState) -> np.ndarray:
        """
        Directly projects Copernicus spectral indices into the FLUME latent space.
        """
        # Extract the core indices
        indices = state.spectral_indices
        # We use a fixed-order vector for the projection: [NDVI, NDWI, SALI, Cloud, resolution]
        input_vector = np.array(
            [
                indices.get("NDVI", 0.0),
                indices.get("NDWI", 0.0),
                indices.get("SALI", 0.0),
                state.cloud_cover / 100.0,
                1.0 if state.raw_metadata.get("resolution") == "10m" else 0.5,
            ],
            dtype=np.float32,
        )

        # Project to 256D
        latent = np.dot(self._projection_matrix, input_vector)

        # Normalize to unit length to match FLUME's expected distribution
        norm = np.linalg.norm(latent)
        if norm > 0:
            latent /= norm

        return latent

    def integrate_with_text(
        self, text_latent: np.ndarray, spectral_latent: np.ndarray
    ) -> np.ndarray:
        """
        Fuses text-based TEK latents with spectral-based ground truth.
        Symphonic Fusion = (Text_Latent + Spectral_Latent) / 2
        """
        fused = (text_latent + spectral_latent) / 2.0
        norm = np.linalg.norm(fused)
        if norm > 0:
            fused /= norm
        return fused
