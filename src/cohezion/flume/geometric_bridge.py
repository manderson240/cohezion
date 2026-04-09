"""Geometric Latent Bridge - Bridging FLUME VAE and Mereon Topology.

This module provides the mapping between the high-dimensional latent space of
FLUME VAE (256D) and the lower-dimensional topological regimes of the
Mereon system (S3/R3).

The goal is to allow the agent to 'reason' about its latent state using
exceptional symmetry regimes (E6, E7, E8), enabling more precise
self-distillation and skill evolution.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from cohezion.physics.mereon_projector import MereonProjector


class GeometricLatentBridge:
    """
    Maps FLUME's 256D latent vectors to Mereon topological regimes.
    """

    def __init__(self, projector: MereonProjector | None = None, weights_path: str | None = None):
        self.projector = projector or MereonProjector()
        self.weights_path = weights_path
        # Projection matrix to reduce 256D -> 4D (quaternion/S3)
        if weights_path and Path(weights_path).exists():
            self.projection_weight = torch.load(weights_path, weights_only=True)
        else:
            # In a production system, this would be a learned linear layer
            # For now, we use a deterministic pseudo-random projection
            # seeded by the symmetry of the 600-cell.
            self.projection_weight = self._init_symmetry_projection()

    def save_weights(self, path: str):
        """Save current projection weights for persistence or optimization."""
        torch.save(self.projection_weight, path)

    def _init_symmetry_projection(self) -> torch.Tensor:
        """Initialize a projection matrix that aligns with Mereon shells."""
        torch.manual_seed(42)
        # 4D projection for S3 lift
        weight = torch.randn(4, 256)
        # Normalize rows to avoid scaling artifacts
        weight = torch.nn.functional.normalize(weight, p=2, dim=1)
        return weight

    def map_to_regime(self, latent_vec: torch.Tensor) -> str:
        """
        Maps a 256D latent vector to a Mereon regime (A, B, C, Inner).

        Process:
        1. 256D -> 4D Projection
        2. 4D -> S3 Lift (Unit Quaternions)
        3. Identify Vertex Type via MereonProjector
        """
        # Ensure we are working with a 1D vector for the projector
        if latent_vec.ndim > 1:
            latent_vec = latent_vec.view(-1)[:256]

        # Project to 4D
        q = torch.matmul(self.projection_weight, latent_vec).squeeze()  # (4,)

        # Convert to numpy for MereonProjector
        q_np = q.detach().cpu().numpy()

        # Lift to S3 perspective
        lift = self.projector.lift(q_np)

        # The Vertex Type (A, B, C, Inner) corresponds to the topological regime
        return lift.vertex_type

    def project_to_coordinates(self, latent_vec: torch.Tensor) -> np.ndarray:
        """Maps latent vector to R3 coordinates via stereographic projection."""
        if latent_vec.ndim > 1:
            latent_vec = latent_vec.view(-1)[:256]

        q = torch.matmul(self.projection_weight, latent_vec).squeeze()
        q_np = q.detach().cpu().numpy()

        # Stereographic projection S3 -> R3
        return self.projector.project(q_np)

    def get_coherence_score(self, latent_vec: torch.Tensor, target_regime: str) -> float:
        """Measures how well a latent vector aligns with a target topological regime."""
        regime = self.map_to_regime(latent_vec)
        return 1.0 if regime == target_regime else 0.0
