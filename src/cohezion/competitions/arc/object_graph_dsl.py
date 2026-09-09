"""ARC Object-Centric Segmentation & Relational Graph DSL Engine.

Extracts connected components, bounding boxes, spatial hierarchies, and provides
higher-order relational primitives for solving ARC-AGI puzzles.
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple, Set, Optional
from collections import deque
import numpy as np

class ARCObject:
    """Represents an individual connected component in an ARC grid."""
    def __init__(self, color: int, pixels: Set[Tuple[int, int]], grid_shape: Tuple[int, int]):
        self.color = color
        self.pixels = pixels  # Set of (r, c)
        self.grid_h, self.grid_w = grid_shape
        self.size = len(pixels)
        
        # Bounding box calculation
        rs = [r for r, c in pixels]
        cs = [c for r, c in pixels]
        self.r_min, self.r_max = min(rs), max(rs)
        self.c_min, self.c_max = min(cs), max(cs)
        self.h = self.r_max - self.r_min + 1
        self.w = self.c_max - self.c_min + 1
        self.centroid = (float(np.mean(rs)), float(np.mean(cs)))

    def to_mask(self) -> np.ndarray:
        mask = np.zeros((self.grid_h, self.grid_w), dtype=bool)
        for r, c in self.pixels:
            mask[r, c] = True
        return mask

    def move(self, dr: int, dc: int) -> ARCObject:
        new_pixels = {
            (r + dr, c + dc) for r, c in self.pixels
            if 0 <= r + dr < self.grid_h and 0 <= c + dc < self.grid_w
        }
        return ARCObject(self.color, new_pixels, (self.grid_h, self.grid_w))


class ObjectGraphExtractor:
    """Segments a 2D grid into connected component objects and spatial relations."""

    @staticmethod
    def extract_objects(grid: List[List[int]], background_color: int = 0, diagonal: bool = False) -> List[ARCObject]:
        if not grid or not grid[0]:
            return []
        h, w = len(grid), len(grid[0])
        visited = set()
        objects = []

        neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if diagonal:
            neighbors += [(-1, -1), (-1, 1), (1, -1), (1, 1)]

        for r in range(h):
            for c in range(w):
                color = grid[r][c]
                if color != background_color and (r, c) not in visited:
                    # BFS flood fill for single object
                    component = set()
                    queue = deque([(r, c)])
                    visited.add((r, c))

                    while queue:
                        curr_r, curr_c = queue.popleft()
                        component.add((curr_r, curr_c))

                        for dr, dc in neighbors:
                            nr, nc = curr_r + dr, curr_c + dc
                            if 0 <= nr < h and 0 <= nc < w:
                                if (nr, nc) not in visited and grid[nr][nc] == color:
                                    visited.add((nr, nc))
                                    queue.append((nr, nc))

                    objects.append(ARCObject(color, component, (h, w)))

        return objects


# ---------------------------------------------------------------------------
# High-Level Relational Object DSL Operators
# ---------------------------------------------------------------------------

def dsl_sort_objects_by_size(objects: List[ARCObject], reverse: bool = True) -> List[ARCObject]:
    return sorted(objects, key=lambda o: o.size, reverse=reverse)

def dsl_filter_objects_by_color(objects: List[ARCObject], color: int) -> List[ARCObject]:
    return [o for o in objects if o.color == color]

def dsl_move_object_gravity(obj: ARCObject, direction: str = "down") -> ARCObject:
    if direction == "down":
        dr = (obj.grid_h - 1) - obj.r_max
        return obj.move(dr, 0)
    elif direction == "up":
        dr = -obj.r_min
        return obj.move(dr, 0)
    elif direction == "right":
        dc = (obj.grid_w - 1) - obj.c_max
        return obj.move(0, dc)
    elif direction == "left":
        dc = -obj.c_min
        return obj.move(0, dc)
    return obj

def dsl_render_objects(objects: List[ARCObject], grid_shape: Tuple[int, int], bg: int = 0) -> List[List[int]]:
    h, w = grid_shape
    grid = [[bg] * w for _ in range(h)]
    for obj in objects:
        for r, c in obj.pixels:
            if 0 <= r < h and 0 <= c < w:
                grid[r][c] = obj.color
    return grid

def transform_object_gravity_all(grid: List[List[int]]) -> List[List[int]]:
    """Relational DSL transform: pulls all discrete objects to the bottom boundary."""
    if not grid or not grid[0]:
        return grid
    h, w = len(grid), len(grid[0])
    objs = ObjectGraphExtractor.extract_objects(grid)
    moved_objs = [dsl_move_object_gravity(o, "down") for o in objs]
    return dsl_render_objects(moved_objs, (h, w))

def transform_keep_largest_object(grid: List[List[int]]) -> List[List[int]]:
    """Relational DSL transform: isolates the single largest connected object."""
    if not grid or not grid[0]:
        return grid
    h, w = len(grid), len(grid[0])
    objs = ObjectGraphExtractor.extract_objects(grid)
    if not objs:
        return grid
    largest = max(objs, key=lambda o: o.size)
    return dsl_render_objects([largest], (h, w))

def transform_keep_smallest_object(grid: List[List[int]]) -> List[List[int]]:
    """Relational DSL transform: isolates the single smallest connected object."""
    if not grid or not grid[0]:
        return grid
    h, w = len(grid), len(grid[0])
    objs = ObjectGraphExtractor.extract_objects(grid)
    if not objs:
        return grid
    smallest = min(objs, key=lambda o: o.size)
    return dsl_render_objects([smallest], (h, w))

# ---------------------------------------------------------------------------
# 3 Red-Team Visual Primitives: Symmetry, Topology Enclosure, Recursive Motifs
# ---------------------------------------------------------------------------

def transform_complete_horizontal_symmetry(grid: List[List[int]]) -> List[List[int]]:
    """Reflects left half onto right half across vertical center axis."""
    if not grid or not grid[0]: return grid
    h, w = len(grid), len(grid[0])
    res = [row[:] for row in grid]
    mid = w // 2
    for r in range(h):
        for c in range(mid):
            if res[r][c] != 0 and res[r][w - 1 - c] == 0:
                res[r][w - 1 - c] = res[r][c]
            elif res[r][w - 1 - c] != 0 and res[r][c] == 0:
                res[r][c] = res[r][w - 1 - c]
    return res

def transform_complete_vertical_symmetry(grid: List[List[int]]) -> List[List[int]]:
    """Reflects top half onto bottom half across horizontal center axis."""
    if not grid or not grid[0]: return grid
    h, w = len(grid), len(grid[0])
    res = [row[:] for row in grid]
    mid = h // 2
    for r in range(mid):
        for c in range(w):
            if res[r][c] != 0 and res[h - 1 - r][c] == 0:
                res[h - 1 - r][c] = res[r][c]
            elif res[h - 1 - r][c] != 0 and res[r][c] == 0:
                res[r][c] = res[h - 1 - r][c]
    return res

def transform_fill_enclosed_regions(grid: List[List[int]], fill_color: int = 3) -> List[List[int]]:
    """Topological Euler Enclosure: Fills background regions enclosed by non-zero contours."""
    if not grid or not grid[0]: return grid
    h, w = len(grid), len(grid[0])
    # BFS flood-fill from all 4 outside borders
    outside = set()
    queue = deque()
    for r in range(h):
        for c in [0, w - 1]:
            if grid[r][c] == 0:
                outside.add((r, c))
                queue.append((r, c))
    for c in range(w):
        for r in [0, h - 1]:
            if grid[r][c] == 0 and (r, c) not in outside:
                outside.add((r, c))
                queue.append((r, c))

    while queue:
        cr, cc = queue.popleft()
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = cr + dr, cc + dc
            if 0 <= nr < h and 0 <= nc < w:
                if (nr, nc) not in outside and grid[nr][nc] == 0:
                    outside.add((nr, nc))
                    queue.append((nr, nc))

    res = [row[:] for row in grid]
    for r in range(h):
        for c in range(w):
            if res[r][c] == 0 and (r, c) not in outside:
                res[r][c] = fill_color
    return res

def transform_tile_periodic_2x2(grid: List[List[int]]) -> List[List[int]]:
    """Recursive Motif Progression: Expands a core repeating tile pattern."""
    if not grid or not grid[0]: return grid
    h, w = len(grid), len(grid[0])
    res = [[0] * (w * 2) for _ in range(h * 2)]
    for r in range(h * 2):
        for c in range(w * 2):
            res[r][c] = grid[r % h][c % w]
    return res
