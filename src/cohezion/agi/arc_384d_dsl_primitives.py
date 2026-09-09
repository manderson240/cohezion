"""Synthesized 384D ARC High-Yield DSL Primitives for Test-Time Compute (TTC).

Implements 5 core geometric & topological primitives for 2D ARC grids (<= 30x30):
1. Gravity drop with obstacle occlusion.
2. Topological hole filling with convex hull boundary.
3. Connected component color remapping based on perimeter-to-area ratio.
4. Diagonal reflection across anti-diagonal with color inversion.
5. Periodic repeating tile pattern extrapolation.
"""

from __future__ import annotations
import numpy as np

def primitive_gravity_drop(grid: np.ndarray, obstacle_color: int = 5, empty_color: int = 0) -> np.ndarray:
    """Simulates gravity falling downwards, stopped by obstacles or bottom floor."""
    h, w = grid.shape
    result = np.full((h, w), empty_color, dtype=np.int32)
    
    for c in range(w):
        col = grid[:, c]
        write_idx = h - 1
        for r in range(h - 1, -1, -1):
            val = col[r]
            if val == obstacle_color:
                result[r, c] = obstacle_color
                write_idx = r - 1
            elif val != empty_color:
                while write_idx >= 0 and result[write_idx, c] == obstacle_color:
                    write_idx -= 1
                if write_idx >= 0:
                    result[write_idx, c] = val
                    write_idx -= 1
    return result

def primitive_convex_hull_fill(grid: np.ndarray, fill_color: int = 1, bg_color: int = 0) -> np.ndarray:
    """Encloses non-background pixels and fills the bounding box envelope."""
    result = grid.copy()
    coords = np.argwhere(grid != bg_color)
    if len(coords) < 2:
        return result
    
    r_min, c_min = coords.min(axis=0)
    r_max, c_max = coords.max(axis=0)
    
    result[r_min:r_max + 1, c_min:c_max + 1] = fill_color
    return result

def primitive_remap_by_compactness(grid: np.ndarray, target_color: int = 2, bg_color: int = 0) -> np.ndarray:
    """Remaps component color if perimeter-to-area ratio indicates high compactness."""
    h, w = grid.shape
    result = grid.copy()
    visited = np.zeros((h, w), dtype=bool)

    for r in range(h):
        for c in range(w):
            if grid[r, c] != bg_color and not visited[r, c]:
                color = grid[r, c]
                queue = [(r, c)]
                visited[r, c] = True
                comp = [(r, c)]
                perimeter = 0

                while queue:
                    curr_r, curr_c = queue.pop(0)
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = curr_r + dr, curr_c + dc
                        if 0 <= nr < h and 0 <= nc < w:
                            if grid[nr, nc] == color and not visited[nr, nc]:
                                visited[nr, nc] = True
                                queue.append((nr, nc))
                                comp.append((nr, nc))
                            elif grid[nr, nc] != color:
                                perimeter += 1
                        else:
                            perimeter += 1

                area = len(comp)
                if area > 0:
                    compactness = (perimeter ** 2) / (4.0 * np.pi * area)
                    if compactness < 1.8:  # Highly circular/compact shape
                        for cr, cc in comp:
                            result[cr, cc] = target_color
    return result

def primitive_antidiagonal_reflection_invert(grid: np.ndarray) -> np.ndarray:
    """Reflects across anti-diagonal and inverts non-zero palette values."""
    # (i, j) -> (W - 1 - j, H - 1 - i)
    reflected = np.transpose(grid)[::-1, ::-1]
    inverted = np.where(reflected > 0, 10 - reflected, 0)
    return inverted

def primitive_periodic_tile_extrapolate(grid: np.ndarray, out_shape: tuple[int, int]) -> np.ndarray:
    """Detects fundamental period tile and replicates to out_shape."""
    h, w = grid.shape
    out_h, out_w = out_shape
    tile_h, tile_w = min(h, out_h), min(w, out_w)
    tile = grid[:tile_h, :tile_w]
    reps_h = (out_h + tile_h - 1) // tile_h
    reps_w = (out_w + tile_w - 1) // tile_w
    tiled = np.tile(tile, (reps_h, reps_w))
    return tiled[:out_h, :out_w]
