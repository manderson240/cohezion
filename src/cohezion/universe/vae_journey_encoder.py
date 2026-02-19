"""VAE Journey Encoder - Trajectory to 256D Latent Representation.

Serializes 12D trajectory sequences into text representations, then encodes
via FLUME VAE to produce 256D journey embeddings for similarity matching.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from cohezion.flume.vae_encoder import FlumeVAEEncoder
from cohezion.universe.engine import TrajectoryPoint


logger = logging.getLogger(__name__)


class VAEJourneyEncoder:
    """Encode trajectories to 256D latent representations via FLUME VAE."""

    def __init__(
        self,
        model_path: Path | None = None,
        fallback_to_hash: bool = True,
    ):
        """Initialize journey encoder.

        Args:
            model_path: Path to FLUME VAE checkpoint (default: uses FlumeVAEEncoder default)
            fallback_to_hash: If True, use hash encoding when VAE unavailable
        """
        self.vae_encoder = FlumeVAEEncoder(
            model_path=model_path,
            device="cpu",
            fallback_to_hash=fallback_to_hash,
        )

    def encode_trajectory(self, trajectory: list[TrajectoryPoint]) -> np.ndarray:
        """Encode trajectory to 256D embedding.

        Serializes trajectory points to structured text, then encodes via FLUME VAE.

        Args:
            trajectory: List of trajectory points

        Returns:
            256D numpy array (normalized)
        """
        # Serialize trajectory to text
        text = self._serialize_trajectory(trajectory)

        # Encode via FLUME VAE
        embedding = self.vae_encoder.encode(text)

        return embedding

    def _serialize_trajectory(self, trajectory: list[TrajectoryPoint]) -> str:
        """Serialize trajectory to structured text representation.

        Format: "step:N coherence:C action:A dims:d0,d1,...|step:N+1 coherence:C action:A dims:..."

        Args:
            trajectory: List of trajectory points

        Returns:
            Structured text representation
        """
        if not trajectory:
            return "empty_trajectory"

        parts = []
        for point in trajectory:
            # Extract key dimensions from axiomatic state
            dims = [
                point.axiomatic.spatial_x,
                point.axiomatic.spatial_y,
                point.axiomatic.spatial_z,
                point.axiomatic.physics,
                point.axiomatic.biology,
                point.axiomatic.logic,
            ]
            dims_str = ",".join(f"{d:.2f}" for d in dims)

            # Format: step:N coherence:C action:A dims:...
            part = (
                f"step:{point.step_number} "
                f"coherence:{point.coherence:.2f} "
                f"action:{point.action_taken} "
                f"dims:{dims_str}"
            )
            parts.append(part)

        # Join with separator
        return "|".join(parts)
