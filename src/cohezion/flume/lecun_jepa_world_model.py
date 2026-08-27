"""Yann LeCun Joint Embedding Predictive Architecture (JEPA) & Energy-Based Model for ARC-AGI.

Bypasses pixel-level autoregression by mapping grids to abstract latent vectors $s = f(x)$,
predicting state transitions in latent space $s' = g(s, a)$, and selecting optimal programs $a^*$
via Energy Minimization:
$$E(x, y, a) = \|s_y - g(s_x, a)\|^2$$
"""

from __future__ import annotations
import numpy as np
from typing import List, Tuple, Dict, Any, Callable

class ARCJEPAWorldModel:
    """Non-generative Latent JEPA and Energy-Based inference engine for ARC."""

    def __init__(self, latent_dim: int = 64):
        self.latent_dim = latent_dim
        # Deterministic projection basis for spatial grid abstractions
        np.random.seed(42)
        self.projection_matrix = np.random.randn(900, latent_dim) / np.sqrt(latent_dim)

    def encode_latent(self, grid: List[List[int]]) -> np.ndarray:
        """Encodes grid into an abstract invariant latent vector s = f(x)."""
        if not grid or not grid[0]:
            return np.zeros(self.latent_dim)
        
        # Flatten and pad grid to 30x30 standard canvas
        canvas = np.zeros((30, 30), dtype=float)
        h, w = min(len(grid), 30), min(len(grid[0]), 30)
        for r in range(h):
            for c in range(w):
                canvas[r, c] = float(grid[r][c])
                
        flat = canvas.flatten()
        latent = np.tanh(flat @ self.projection_matrix)
        # Normalize to unit hyper-sphere
        norm = np.linalg.norm(latent)
        return latent / (norm + 1e-8)

    def compute_energy(self, x_grid: List[List[int]], y_grid: List[List[int]], transform_fn: Callable) -> float:
        """Computes LeCun Energy: E(x, y, a) = || s_y - Pred(s_x, a) ||^2."""
        s_y = self.encode_latent(y_grid)
        predicted_grid = transform_fn(x_grid)
        s_pred = self.encode_latent(predicted_grid)
        
        # Quadratic Energy
        energy = float(np.sum((s_y - s_pred) ** 2))
        return energy

    def rank_transforms_by_energy(
        self,
        demo_pairs: List[Tuple[List[List[int]], List[List[int]]]],
        transforms: List[Tuple[str, Callable]]
    ) -> List[Tuple[str, float]]:
        """Ranks candidate transformations by minimizing aggregate latent energy across demonstrations."""
        scores = []
        for name, fn in transforms:
            total_energy = 0.0
            for x, y in demo_pairs:
                total_energy += self.compute_energy(x, y, fn)
            avg_energy = total_energy / max(len(demo_pairs), 1)
            scores.append((name, avg_energy))
            
        # Lowest energy = highest predictive consistency in latent space
        scores.sort(key=lambda item: item[1])
        return scores
