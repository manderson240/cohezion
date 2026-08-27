"""Michael Levin-Inspired Bioelectric Voltage Diffusion & Morphogenetic Attractor Engine.

Models 2D grids as bioelectric cellular lattices with:
1. Membrane Potential $V_{ij} \in [-70, -10]$ mV.
2. Gap-Junction Coupling Tensor $\kappa_{ij} \in [0, 1]$ and Voltage Diffusion $D \nabla^2 V$.
3. Morphogenetic Attractor Dynamics converging incomplete/damaged shapes to target morphology.
"""

from __future__ import annotations
import numpy as np
from typing import List, Tuple, Optional

class BioelectricNCAMorphogenesis:
    """Simulates bioelectric cell voltage fields and gap-junction target morphology repair."""

    def __init__(self, diffusion_rate: float = 0.25, gamma_leak: float = 0.05, steps: int = 8):
        self.diffusion_rate = diffusion_rate
        self.gamma_leak = gamma_leak
        self.steps = steps

    def repair_morphology(self, grid: List[List[int]], target_color: int = 0) -> List[List[int]]:
        """Applies bioelectric voltage diffusion to repair broken or occluded shapes."""
        if not grid or not grid[0]:
            return grid
        
        arr = np.array(grid, dtype=float)
        h, w = arr.shape
        
        # 1. Initialize Bioelectric Voltage Potential Field V (-70mV background, -20mV depolarized signal)
        V = np.where(arr > 0, -20.0, -70.0)
        
        # 2. Bioelectric Gap-Junction Diffusion Dynamics
        for _ in range(self.steps):
            # 5-point discrete Laplace-Beltrami operator for voltage diffusion
            laplacian = (
                np.roll(V, 1, axis=0) + np.roll(V, -1, axis=0) +
                np.roll(V, 1, axis=1) + np.roll(V, -1, axis=1) -
                4.0 * V
            )
            # Boundary condition clamping
            laplacian[0, :] = 0
            laplacian[-1, :] = 0
            laplacian[:, 0] = 0
            laplacian[:, -1] = 0
            
            # Voltage update equation: dV/dt = D * Lap(V) - gamma * (V - V_rest)
            V += self.diffusion_rate * laplacian - self.gamma_leak * (V - (-70.0))
        
        # 3. Morphogenetic Thresholding: Cells above depolarized threshold (-45mV) precipitate structure
        repaired = np.copy(arr)
        dominant_color = int(arr.max()) if arr.max() > 0 else 1
        if target_color > 0:
            dominant_color = target_color
            
        # Repair holes/occlusions where voltage diffused strongly
        morphogenetic_mask = (V > -48.0) & (arr == 0)
        repaired[morphogenetic_mask] = dominant_color
        
        return repaired.astype(int).tolist()


def transform_bioelectric_morphogenetic_repair(grid: List[List[int]]) -> List[List[int]]:
    """Transforms damaged or occluded ARC grids via Levin bioelectric field repair."""
    engine = BioelectricNCAMorphogenesis()
    return engine.repair_morphology(grid)
