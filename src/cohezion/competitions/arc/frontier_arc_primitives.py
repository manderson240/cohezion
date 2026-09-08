"""Frontier ARC-AGI Primitives (Synthesized via Qwen-397B & DeepSeek-V4 Pro Cloud).

Implements the 3 highest-leverage algorithmic transforms:
1. Connected Component Sorting & Lexicographical Relocation.
2. Obstacle-Constrained Geodesic BFS Path Propagation.
3. Wildcard 3x3 Convolutional Pattern Replacement (Cellular Automata).
"""

from __future__ import annotations

import collections


MAX_DIM = 30


def get_dims(grid: list[list[int]]) -> tuple[int, int]:
    if not grid or not isinstance(grid, list):
        return (0, 0)
    return (len(grid), len(grid[0]) if isinstance(grid[0], list) else 0)


# --- 1. Connected Component Sorting by Area & Centroid ---
def sort_components_by_area(grid: list[list[int]], bg: int = 0) -> list[list[int]]:
    h, w = get_dims(grid)
    if h == 0 or w == 0:
        return [row[:] for row in grid]

    visited = [[False] * w for _ in range(h)]
    components = []

    for r in range(h):
        for c in range(w):
            if not visited[r][c] and grid[r][c] != bg:
                color = grid[r][c]
                cells = []
                queue = [(r, c)]
                visited[r][c] = True
                while queue:
                    cr, cc = queue.pop(0)
                    cells.append((cr, cc))
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nr, nc = cr + dr, cc + dc
                        if (
                            0 <= nr < h
                            and 0 <= nc < w
                            and not visited[nr][nc]
                            and grid[nr][nc] == color
                        ):
                            visited[nr][nc] = True
                            queue.append((nr, nc))
                components.append((len(cells), color, cells))

    # Sort components by area (largest to smallest)
    components.sort(key=lambda c: c[0], reverse=True)

    out = [[bg] * w for _ in range(h)]
    # Write back in sorted order
    for _, color, cells in components:
        for cr, cc in cells:
            out[cr][cc] = color
    return out


# --- 2. Obstacle-Constrained Geodesic BFS Propagation ---
def geodesic_bfs_propagation(
    grid: list[list[int]], seed_color: int = 1, barrier_color: int = 2, bg: int = 0
) -> list[list[int]]:
    h, w = get_dims(grid)
    out = [row[:] for row in grid]
    queue: collections.deque[tuple[int, int]] = collections.deque()

    for r in range(h):
        for c in range(w):
            if grid[r][c] == seed_color:
                queue.append((r, c))

    while queue:
        cr, cc = queue.popleft()
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = cr + dr, cc + dc
            if 0 <= nr < h and 0 <= nc < w and out[nr][nc] == bg and out[nr][nc] != barrier_color:
                out[nr][nc] = seed_color
                queue.append((nr, nc))
    return out


# --- 3. Wildcard 3x3 Convolutional Pattern Replacement ---
def conv_pattern_replacement(
    grid: list[list[int]], target_color: int = 3, bg: int = 0
) -> list[list[int]]:
    """Applies a 3x3 cross stencil (context-dependent cellular automata filter)."""
    h, w = get_dims(grid)
    out = [row[:] for row in grid]
    for r in range(1, h - 1):
        for c in range(1, w - 1):
            # Check 4-neighbor cross pattern
            if (
                grid[r][c] == bg
                and grid[r - 1][c] != bg
                and grid[r + 1][c] != bg
                and grid[r][c - 1] != bg
                and grid[r][c + 1] != bg
            ):
                out[r][c] = target_color
    return out
