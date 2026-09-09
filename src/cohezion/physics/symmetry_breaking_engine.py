"""Spontaneous Symmetry Breaking & Ginzburg-Landau Order Parameter Engine.

Models ARC grid and decision state phase transitions:
1. Symmetric High-Temperature State ($\phi = 0$, uniform potential).
2. Spontaneous Symmetry Breaking ($V(\phi) = -\frac{\alpha}{2} \phi^2 + \frac{\beta}{4} \phi^4$).
3. Directional Perturbation ($\epsilon$) resolving grid parity, chirality, and winner-take-all action choice.
"""

from __future__ import annotations
import numpy as np
from typing import List, Tuple, Optional

class SymmetryBreakingEngine:
    """Computes spontaneous symmetry breaking and Landau phase transitions for discrete grids."""

    def __init__(self, alpha: float = 2.0, beta: float = 1.0):
        self.alpha = alpha
        self.beta = beta
        # Theoretical non-zero ground-state order parameter: phi_0 = sqrt(alpha / beta)
        self.phi_ground_state = np.sqrt(alpha / beta)

    def compute_potential(self, phi: np.ndarray) -> np.ndarray:
        """Mexican-hat Landau free energy: V(phi) = -0.5 * alpha * phi^2 + 0.25 * beta * phi^4."""
        return -0.5 * self.alpha * (phi ** 2) + 0.25 * self.beta * (phi ** 4)

    def break_grid_symmetry(
        self,
        grid: List[List[int]],
        perturbation_axis: str = "horizontal",
        asymmetry_strength: float = 0.15
    ) -> Tuple[List[List[int]], float]:
        """Resolves an ambiguous symmetric grid into a broken-symmetry stable ground state."""
        if not grid or not grid[0]:
            return grid, 0.0

        arr = np.array(grid, dtype=float)
        h, w = arr.shape

        # Initial order parameter field (near zero symmetric state)
        phi = np.where(arr > 0, 0.1, -0.1)

        # Apply infinitesimal directional perturbation along the breaking axis
        if perturbation_axis == "horizontal":
            gradient = np.linspace(-asymmetry_strength, asymmetry_strength, w)
            phi += gradient[np.newaxis, :]
        elif perturbation_axis == "vertical":
            gradient = np.linspace(-asymmetry_strength, asymmetry_strength, h)
            phi += gradient[:, np.newaxis]

        # Gradient descent down Mexican-hat potential to stable minima +/- phi_0
        for _ in range(25):
            dV_dphi = -self.alpha * phi + self.beta * (phi ** 3)
            phi -= 0.15 * dV_dphi

        # Compute order parameter magnitude
        order_parameter = float(np.mean(np.abs(phi)))

        # Assign phase-separated colors based on broken parity (Left vs Right / Up vs Down)
        broken_grid = np.copy(arr)
        for r in range(h):
            for c in range(w):
                if arr[r][c] != 0:
                    broken_grid[r][c] = int(arr[r][c]) if phi[r][c] > 0 else (int(arr[r][c]) % 9 + 1)

        return broken_grid.astype(int).tolist(), order_parameter
