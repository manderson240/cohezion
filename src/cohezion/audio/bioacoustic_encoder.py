"""Bioacoustic Encoder for BirdCLEF 2026.
Integrates pre-computed Perch embeddings and Perch v2 TFLite backbones.
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn


class BioacousticEncoder(nn.Module):
    """
    Maps bioacoustic embeddings (Perch/BirdNET) to FLUME latent space.
    """

    def __init__(self, input_dim: int = 1536, latent_dim: int = 256):
        super().__init__()
        self.input_dim = input_dim
        self.latent_dim = latent_dim

        # Projection layer: 1536D (Perch) -> 256D (FLUME)
        self.projection = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.LayerNorm(512),
            nn.ReLU(),
            nn.Linear(512, latent_dim),
            nn.Tanh(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.projection(x)


class BirdCLEFDataProduct:
    """
    Interface for the pre-computed Perch embeddings dataset.
    """

    def __init__(self, parquet_path: str):
        self.path = parquet_path
        self.df: pd.DataFrame | None = None

    def load(self):
        """Load embeddings from parquet."""
        self.df = pd.read_parquet(self.path)
        print(f"Loaded {len(self.df)} bioacoustic embeddings.")

    def get_embeddings(self) -> np.ndarray:
        if self.df is None:
            self.load()
        # Assume 'embedding' column contains the vector
        return np.stack(self.df["embedding"].values)

    def get_labels(self) -> np.ndarray:
        if self.df is None:
            self.load()
        return self.df["primary_labels"].values
