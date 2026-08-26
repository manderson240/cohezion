"""Advanced ARC-AGI Grid Reasoning Engine (Color Masking, Object Cropping, Multi-Scale Search).

Handles:
1. Marker/Indicator Object Isolation (Finding special color boxes like color 8/teal/pink that frame subgrids).
2. Color Frequency / Dominant Color Extraction.
3. Subgrid Extraction by Color Bounding Box.
4. Scale-Invariant Pattern Tiling.
5. Invariant Color Remapping.
"""

from __future__ import annotations

import collections
from typing import Any, Callable

def extract_subgrid_by_indicator(grid: list[list[int]]) -> list[list[int]] | None:
    """Extracts subgrid enclosed by indicator/marker color pixels."""
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    if h == 0 or w == 0:
        return None

    # Count occurrences of all colors
    counts = collections.Counter(c for row in grid for c in row)
    # Check rare framing colors (present in 4-20 cells)
    rare_colors = [c for c, cnt in counts.items() if 2 <= cnt <= 40 and c != 0]

    for color in rare_colors:
        coords = [(r, c) for r in range(h) for c in range(w) if grid[r][c] == color]
        if len(coords) >= 2:
            min_r = min(r for r, c in coords)
            max_r = max(r for r, c in coords)
            min_c = min(c for r, c in coords)
            max_c = max(c for r, c in coords)

            sub_h = max_r - min_r + 1
            sub_w = max_c - min_c + 1

            if 2 <= sub_h <= 30 and 2 <= sub_w <= 30:
                # Return the enclosed interior subgrid (excluding indicator border if framed)
                if sub_h > 2 and sub_w > 2:
                    return [row[min_c + 1 : max_c] for row in grid[min_r + 1 : max_r]]
                else:
                    return [row[min_c : max_c + 1] for row in grid[min_r : max_r + 1]]
    return None

def extract_most_frequent_subgrid_pattern(grid: list[list[int]], size: tuple[int, int] = (3, 3)) -> list[list[int]]:
    """Extracts the dominant repeating subgrid block."""
    h, w = len(grid), len(grid[0]) if grid else 0
    sh, sw = size
    if h < sh or w < sw:
        return [row[:] for row in grid]

    patterns = collections.defaultdict(int)
    for r in range(0, h - sh + 1, sh):
        for c in range(0, w - sw + 1, sw):
            sub = tuple(tuple(grid[r + dr][c + dc] for dc in range(sw)) for dr in range(sh))
            patterns[sub] += 1

    if patterns:
        best = max(patterns.keys(), key=lambda k: patterns[k])
        return [list(r) for r in best]
    return [row[:] for row in grid]
