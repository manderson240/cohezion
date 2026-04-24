# ruff: noqa: E402  # deferred imports for circular-dep workarounds
"""FLUME Grid Encoder for ARC-AGI style grid patterns.

Specialized encoder/decoder for 2D matrices (0-9) representing color grids.
Maps grids to 256D FLUME latent space for semantic reasoning and trajectory tracking.
"""

import numpy as np
import torch
import torch.nn as nn


class ARCGridEncoder(nn.Module):
    """
    Encoder for ARC-AGI grids.
    Uses a simple CNN or MLP to project 2D grids into 256D.
    """

    def __init__(self, latent_dim: int = 256, max_grid_size: int = 30):
        super().__init__()
        self.latent_dim = latent_dim
        self.max_grid_size = max_grid_size

        # Flattened input size (max_grid_size * max_grid_size)
        # We use padding for smaller grids
        self.input_dim = max_grid_size * max_grid_size

        self.encoder = nn.Sequential(
            nn.Linear(self.input_dim, 512),
            nn.ReLU(),
            nn.Linear(512, 512),
            nn.ReLU(),
            nn.Linear(512, latent_dim),
        )

        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 512),
            nn.ReLU(),
            nn.Linear(512, 512),
            nn.ReLU(),
            nn.Linear(512, self.input_dim),
            nn.Sigmoid(),  # Output normalized probabilities/intensities for 0-9
        )

    def preprocess_grid(self, grid: list[list[int]]) -> torch.Tensor:
        """Pad and flatten grid for encoding."""
        rows = len(grid)
        cols = len(grid[0]) if rows > 0 else 0

        flat_grid = np.zeros((self.max_grid_size, self.max_grid_size), dtype=np.float32)

        # Fill existing grid into top-left
        for r in range(min(rows, self.max_grid_size)):
            for c in range(min(cols, self.max_grid_size)):
                # Normalize color 0-9 to 0.0-0.9
                flat_grid[r, c] = grid[r][c] / 10.0

        return torch.from_numpy(flat_grid.flatten()).unsqueeze(0)

    def encode(self, grid: list[list[int]]) -> torch.Tensor:
        """Encode 2D grid to latent vector."""
        x = self.preprocess_grid(grid)
        return self.encoder(x)

    def decode(self, z: torch.Tensor, original_shape: tuple[int, int]) -> list[list[int]]:
        """Decode latent vector back to 2D grid of specific shape."""
        x_hat = self.decoder(z)
        x_hat = x_hat.view(self.max_grid_size, self.max_grid_size).detach().cpu().numpy()

        rows, cols = original_shape
        grid = []
        for r in range(rows):
            row = []
            for c in range(cols):
                # Denormalize and round to nearest integer 0-9
                val = round(x_hat[r, c] * 10.0)
                row.append(max(0, min(9, val)))
            grid.append(row)
        return grid


class FlumeGridHarness:
    """
    Harness for integrating Grid Encoding into the FLUME evaluation loop.
    """

    def __init__(self, device: str = "cpu"):
        self.device = device
        self.model = ARCGridEncoder().to(device)
        self.model.eval()

    def get_grid_embedding(self, grid_str: str) -> np.ndarray:
        """
        Parses a grid string (e.g. "[[1,2],[3,4]]") and returns its 256D embedding.
        """
        try:
            grid = json.loads(grid_str)
            with torch.no_grad():
                z = self.model.encode(grid)
                return z.squeeze(0).cpu().numpy()
        except Exception:
            # Fallback to zero vector or hash if parsing fails
            return np.zeros(256, dtype=np.float32)


import json
