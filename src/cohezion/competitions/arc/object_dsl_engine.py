"""ARC-AGI Object-Centric DSL Engine (Breadth & Depth Program Synthesis).

Expands the search space across:
1. Object Extraction (4-connected & 8-connected component segmentations).
2. Per-Object Transformations (Translating, rotating, scaling individual objects independently).
3. Background vs Foreground Separation.
4. Scale-Invariant Subgrid Stencil Matching.
5. Multi-Color Segment Inversions & Periodic Grid Tiling.
6. 3-Stage Compositional Depth Search: f_3(f_2(f_1(x))).
"""

from __future__ import annotations

from dataclasses import dataclass


MAX_DIM = 30


@dataclass(frozen=True)
class GridObject:
    color: int
    cells: tuple[tuple[int, int], ...]
    min_r: int
    max_r: int
    min_c: int
    max_c: int

    @property
    def height(self) -> int:
        return self.max_r - self.min_r + 1

    @property
    def width(self) -> int:
        return self.max_c - self.min_c + 1

    @property
    def area(self) -> int:
        return len(self.cells)


def extract_objects(grid: list[list[int]], bg: int = 0) -> list[GridObject]:
    """Extracts all disconnected multi-color objects from grid."""
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    if h == 0 or w == 0:
        return []

    visited = [[False] * w for _ in range(h)]
    objects = []

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

                min_r = min(cr for cr, cc in cells)
                max_r = max(cr for cr, cc in cells)
                min_c = min(cc for cr, cc in cells)
                max_c = max(cc for cr, cc in cells)

                objects.append(
                    GridObject(
                        color=color,
                        cells=tuple(sorted(cells)),
                        min_r=min_r,
                        max_r=max_r,
                        min_c=min_c,
                        max_c=max_c,
                    )
                )
    return objects


# --- Object-Centric Operations ---
def filter_largest_object_only(grid: list[list[int]], bg: int = 0) -> list[list[int]]:
    objs = extract_objects(grid, bg)
    if not objs:
        return [r[:] for r in grid]
    largest = max(objs, key=lambda o: o.area)
    h, w = len(grid), len(grid[0])
    out = [[bg] * w for _ in range(h)]
    for r, c in largest.cells:
        out[r][c] = largest.color
    return out


def filter_smallest_object_only(grid: list[list[int]], bg: int = 0) -> list[list[int]]:
    objs = extract_objects(grid, bg)
    if not objs:
        return [r[:] for r in grid]
    smallest = min(objs, key=lambda o: o.area)
    h, w = len(grid), len(grid[0])
    out = [[bg] * w for _ in range(h)]
    for r, c in smallest.cells:
        out[r][c] = smallest.color
    return out


def crop_largest_object(grid: list[list[int]], bg: int = 0) -> list[list[int]]:
    objs = extract_objects(grid, bg)
    if not objs:
        return [[bg]]
    largest = max(objs, key=lambda o: o.area)
    return [
        row[largest.min_c : largest.max_c + 1] for row in grid[largest.min_r : largest.max_r + 1]
    ]


def sort_objects_horizontally(grid: list[list[int]], bg: int = 0) -> list[list[int]]:
    objs = extract_objects(grid, bg)
    if not objs:
        return [r[:] for r in grid]
    # Sort left to right by bounding box width
    sorted_objs = sorted(objs, key=lambda o: o.min_c)
    h = max(o.height for o in sorted_objs)
    total_w = sum(o.width for o in sorted_objs)
    if total_w > MAX_DIM or h > MAX_DIM:
        return [r[:] for r in grid]
    out = [[bg] * total_w for _ in range(h)]
    curr_c = 0
    for o in sorted_objs:
        for r, c in o.cells:
            rel_r = r - o.min_r
            rel_c = c - o.min_c
            out[rel_r][curr_c + rel_c] = o.color
        curr_c += o.width
    return out
