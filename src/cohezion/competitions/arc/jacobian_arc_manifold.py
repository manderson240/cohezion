"""ARC-AGI Jacobian J-Space Sensitivity & Differential Search Engine.

Implements the Jacobian sensitivity matrix J_ij = ∂(Manifold_State_i) / ∂(Grid_Cell_j):
1. Calculates differential sensitivity of the 12D FLUME vector to grid modifications.
2. Identifies 'Pivotal Saliency Points' on ARC grids to focus search exclusively on
   critical boundary and topological inflection cells.
3. Guides MCTS and program synthesis rollouts along the steepest Jacobian gradient.
"""

from __future__ import annotations

import numpy as np

from cohezion.competitions.arc.nexus_manifold_solver import QuadratureNexusEncoder


class JacobianARCManifoldEngine:
    """Computes Jacobian sensitivity gradients across discrete ARC grids."""

    def __init__(self) -> None:
        self.encoder = QuadratureNexusEncoder()

    def compute_grid_jacobian(self, grid: list[list[int]], bg: int = 0) -> np.ndarray:
        """Computes numerical Jacobian sensitivity map across grid coordinates.

        Returns:
            H x W matrix indicating spatial gradient influence on the 12D manifold.
        """
        h = len(grid)
        w = len(grid[0]) if h > 0 else 0
        if h == 0 or w == 0:
            return np.zeros((1, 1))

        base_state = self.encoder.encode_grid(grid, bg)
        base_vec = np.array(
            [
                base_state.x,
                base_state.y,
                base_state.z_area,
                base_state.t_entropy,
                base_state.brane_d4_symmetry,
                base_state.brane_color_diversity,
                base_state.brane_quadrature_coherence,
            ]
        )

        sensitivity_map = np.zeros((h, w), dtype=float)

        for r in range(h):
            for c in range(w):
                # Perturb single pixel to background/foreground
                original = grid[r][c]
                perturbed = bg if original != bg else 1
                grid[r][c] = perturbed

                p_state = self.encoder.encode_grid(grid, bg)
                p_vec = np.array(
                    [
                        p_state.x,
                        p_state.y,
                        p_state.z_area,
                        p_state.t_entropy,
                        p_state.brane_d4_symmetry,
                        p_state.brane_color_diversity,
                        p_state.brane_quadrature_coherence,
                    ]
                )

                # Reset
                grid[r][c] = original

                # Jacobian Euclidean differential ||∂S / ∂x_rc||
                grad_norm = float(np.linalg.norm(p_vec - base_vec))
                sensitivity_map[r, c] = round(grad_norm, 4)

        return sensitivity_map

    def extract_salient_pivot_cells(
        self, grid: list[list[int]], top_k: int = 5
    ) -> list[tuple[int, int, float]]:
        """Finds the top-K pivotal grid coordinates with highest Jacobian curvature."""
        j_map = self.compute_grid_jacobian(grid)
        coords = []
        h, w = j_map.shape
        for r in range(h):
            for c in range(w):
                coords.append((r, c, float(j_map[r, c])))
        coords.sort(key=lambda item: item[2], reverse=True)
        return coords[:top_k]
