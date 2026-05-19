"""ARC-AGI-2 Grid Transform Primitives — structural + object + tiling ops.

Pruned from 176 ops (171 color-noise) to 29 structural operations.
Every function is instrumented with @timeit for long-horizon profiling.
Budget: dimensions 1x1..30x30, values 0..9.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

import numpy as np

from cohezion.core.timeit import timeit


TransformFn = Callable[[np.ndarray], np.ndarray | None]

# ═══════════════════════════════════════════════════════════════════
# Tier 0: Geometry (rotations, flips, transpose)
# ═══════════════════════════════════════════════════════════════════


@timeit()
def rotate_90(grid: np.ndarray) -> np.ndarray | None:
    return np.rot90(grid, k=1)


@timeit()
def rotate_180(grid: np.ndarray) -> np.ndarray | None:
    return np.rot90(grid, k=2)


@timeit()
def rotate_270(grid: np.ndarray) -> np.ndarray | None:
    return np.rot90(grid, k=3)


@timeit()
def flip_horizontal(grid: np.ndarray) -> np.ndarray | None:
    return np.fliplr(grid)


@timeit()
def flip_vertical(grid: np.ndarray) -> np.ndarray | None:
    return np.flipud(grid)


@timeit()
def transpose(grid: np.ndarray) -> np.ndarray | None:
    return grid.T


# ═══════════════════════════════════════════════════════════════════
# Tier 1: Grid transforms (gravity, scale, crop)
# ═══════════════════════════════════════════════════════════════════


@timeit()
def gravity_fall(grid: np.ndarray) -> np.ndarray | None:
    """Gravity: all non-zero pixels fall to bottom of their column."""
    out = np.zeros_like(grid)
    for col in range(grid.shape[1]):
        non_zero = grid[:, col][grid[:, col] != 0]
        if len(non_zero) > 0:
            out[-len(non_zero) :, col] = non_zero
    return out


@timeit()
def scale_up_2(grid: np.ndarray) -> np.ndarray | None:
    h, w = grid.shape
    if max(h * 2, w * 2) > 30:
        return None
    return np.repeat(np.repeat(grid, 2, axis=0), 2, axis=1)


@timeit()
def scale_down_2(grid: np.ndarray) -> np.ndarray | None:
    h, w = grid.shape
    if h % 2 or w % 2:
        return None
    return grid.reshape(h // 2, 2, w // 2, 2).max(axis=(1, 3))


@timeit()
def crop_to_content(grid: np.ndarray) -> np.ndarray | None:
    """Crop to bounding box of non-zero pixels."""
    nz = np.argwhere(grid != 0)
    if nz.size == 0:
        return None
    r0, c0 = nz.min(axis=0)
    r1, c1 = nz.max(axis=0)
    return grid[r0 : r1 + 1, c0 : c1 + 1]


# ═══════════════════════════════════════════════════════════════════
# Tier 2: Morphology (dilate, erode, outline)
# ═══════════════════════════════════════════════════════════════════


@timeit()
def dilate(grid: np.ndarray) -> np.ndarray | None:
    from scipy import ndimage as ndi

    return ndi.grey_dilation(grid, size=(3, 3))


@timeit()
def erode(grid: np.ndarray) -> np.ndarray | None:
    from scipy import ndimage as ndi

    return ndi.grey_erosion(grid, size=(3, 3))


@timeit()
def outline(grid: np.ndarray) -> np.ndarray | None:
    """Edge detection: pixels not surrounded by same color on all 4 sides."""
    from scipy import ndimage as ndi

    out = np.zeros_like(grid)
    changed = False
    for c in np.unique(grid):
        if c == 0:
            continue
        mask = grid == c
        eroded = ndi.binary_erosion(mask)
        edge = mask & ~eroded
        if edge.any():
            out[edge] = c
            changed = True
    return out if changed else None


# ═══════════════════════════════════════════════════════════════════
# Tier 3: Object operations
# ═══════════════════════════════════════════════════════════════════


@timeit()
def extract_largest_component(grid: np.ndarray) -> np.ndarray | None:
    """Keep only the largest 4-connected component, remove everything else."""
    from scipy import ndimage as ndi

    labels, n = ndi.label(grid != 0)
    if n == 0:
        return None
    largest = max(range(1, n + 1), key=lambda i: np.sum(labels == i))
    out = np.zeros_like(grid)
    mask = labels == largest
    out[mask] = grid[mask]
    return out


@timeit()
def flood_fill_expand(grid: np.ndarray) -> np.ndarray | None:
    """Fill holes inside connected regions per-color."""
    from scipy import ndimage as ndi

    colors = np.unique(grid[grid != 0])
    if len(colors) == 0:
        return None
    out = grid.copy()
    for c in colors:
        mask = grid == c
        if mask.sum() == 0:
            continue
        filled = ndi.binary_fill_holes(mask)
        out[filled] = c
    return out if not np.array_equal(out, grid) else None


@timeit()
def remove_background(grid: np.ndarray) -> np.ndarray | None:
    """Set the most frequent non-zero color to 0 (remove background)."""
    vals, counts = np.unique(grid, return_counts=True)
    if len(vals) <= 1:
        return None
    bg = vals[np.argmax(counts)]
    if bg == 0 and len(vals) > 1:
        bg = vals[np.argsort(counts)[-2]]
    out = grid.copy()
    out[out == bg] = 0
    return out if not np.array_equal(out, grid) else None


# ═══════════════════════════════════════════════════════════════════
# Tier 4: Pattern detection
# ═══════════════════════════════════════════════════════════════════


@timeit()
def detect_lines(grid: np.ndarray) -> np.ndarray | None:
    """Detect full horizontal/vertical/diagonal lines."""
    out = np.zeros_like(grid)
    changed = False
    for axis in (0, 1):
        for i in range(grid.shape[axis]):
            line = grid[i, :] if axis == 0 else grid[:, i]
            if np.all(line == line[0]) and line[0] != 0:
                if axis == 0:
                    out[i, :] = line[0]
                else:
                    out[:, i] = line[0]
                changed = True
    if grid.shape[0] == grid.shape[1]:
        d = np.diag(grid)
        if np.all(d == d[0]) and d[0] != 0:
            np.fill_diagonal(out, d[0])
            changed = True
    return out if changed else None


@timeit()
def count_objects(grid: np.ndarray) -> np.ndarray | None:
    """Replace entire grid with count of 4-connected components."""
    from scipy import ndimage as ndi

    _labels, n = ndi.label(grid != 0)
    if n == 0:
        return None
    return np.full_like(grid, n)


# ═══════════════════════════════════════════════════════════════════
# Tier 5: Tiling/Pattern (recovered from pre-prune set)
# ═══════════════════════════════════════════════════════════════════


@timeit()
def pattern_repeat_row_col(grid: np.ndarray) -> np.ndarray | None:
    """Detect row/col repeating pattern and double it."""
    h, w = grid.shape
    for period in range(1, min(h, w) // 2 + 1):
        tile = grid[:period, :period]
        if h % period == 0 and w % period == 0:
            recon = np.tile(tile, (h // period, w // period))
            if np.array_equal(recon, grid):
                return np.tile(tile, (2, 2))[:30, :30]
    return None


@timeit()
def tile_3x3(grid: np.ndarray) -> np.ndarray | None:
    """Tile the grid into a 3×3 arrangement."""
    h, w = grid.shape
    if h > 10 or w > 10:
        return None
    out = np.zeros((h * 3, w * 3), dtype=grid.dtype)
    for i in range(3):
        for j in range(3):
            out[i * h : (i + 1) * h, j * w : (j + 1) * w] = grid
    return out


@timeit()
def tile_grid(grid: np.ndarray, tile_h: int = 3, tile_w: int = 3) -> np.ndarray | None:
    """Tile the grid into a tile_h × tile_w arrangement."""
    h, w = grid.shape
    if max(h * tile_h, w * tile_w) > 30:
        return None
    return np.tile(grid, (tile_h, tile_w))


@timeit()
def repeat_rows(grid: np.ndarray, n: int = 2) -> np.ndarray | None:
    """Repeat each row n times."""
    if grid.shape[0] * n > 30:
        return None
    return np.repeat(grid, n, axis=0)


@timeit()
def repeat_cols(grid: np.ndarray, n: int = 2) -> np.ndarray | None:
    """Repeat each column n times."""
    if grid.shape[1] * n > 30:
        return None
    return np.repeat(grid, n, axis=1)


@timeit()
def kronecker_mask_tile(grid: np.ndarray) -> np.ndarray | None:
    """Kronecker-product tiling: each non-zero cell expands to full H×W block."""
    h, w = grid.shape
    if h > 5 or w > 5:
        return None
    out = np.zeros((h * h, w * w), dtype=grid.dtype)
    for i in range(h):
        for j in range(w):
            if grid[i, j] != 0:
                out[i * h : (i + 1) * h, j * w : (j + 1) * w] = grid
    if np.array_equal(out, np.zeros_like(out)):
        return None
    return out


# ═══════════════════════════════════════════════════════════════════
# Tier 6: Object operations (added in A.3-A.7)
# ═══════════════════════════════════════════════════════════════════


@timeit()
def find_largest_object(grid: np.ndarray) -> np.ndarray | None:
    """Extract largest connected component as a binary mask (its color on black)."""
    from scipy import ndimage as ndi

    labels, n = ndi.label(grid != 0)
    if n == 0:
        return None
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0  # background
    largest_label = sizes.argmax()
    out = np.zeros_like(grid)
    mask = labels == largest_label
    out[mask] = grid[mask]
    return out


@timeit()
def object_bbox(grid: np.ndarray) -> np.ndarray | None:
    """Crop to bounding box of the largest object only (not all content)."""
    from scipy import ndimage as ndi

    labels, n = ndi.label(grid != 0)
    if n == 0:
        return None
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    largest_label = sizes.argmax()
    ys, xs = np.where(labels == largest_label)
    if len(ys) == 0:
        return None
    r0, r1 = ys.min(), ys.max()
    c0, c1 = xs.min(), xs.max()
    return grid[r0 : r1 + 1, c0 : c1 + 1]


@timeit()
def fill_interior(grid: np.ndarray) -> np.ndarray | None:
    """Fill holes in all objects (binary_fill_holes per connected region)."""
    from scipy import ndimage as ndi

    labels, n = ndi.label(grid != 0)
    if n == 0:
        return None
    out = grid.copy()
    for i in range(1, n + 1):
        mask = labels == i
        filled = ndi.binary_fill_holes(mask)
        if filled.sum() > mask.sum():
            color = int(grid[mask][0]) if mask.any() else 0
            out[filled] = color
    return out if not np.array_equal(out, grid) else None


@timeit()
def remove_small_objects(grid: np.ndarray, min_size: int = 4) -> np.ndarray | None:
    """Remove connected components smaller than min_size pixels."""
    from scipy import ndimage as ndi

    labels, n = ndi.label(grid != 0)
    if n == 0:
        return None
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    out = grid.copy()
    removed = False
    for i in range(1, n + 1):
        if sizes[i] < min_size:
            out[labels == i] = 0
            removed = True
    return out if removed else None


@timeit()
def color_map_by_object_size(grid: np.ndarray) -> np.ndarray | None:
    """Recolor objects from 1..N based on size rank (smallest=1, largest=N)."""
    from scipy import ndimage as ndi

    labels, n = ndi.label(grid != 0)
    if n <= 1:
        return None
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    # Rank by size: smallest gets 1, largest gets n
    order = np.argsort(sizes[1 : n + 1])  # indices of sorted sizes
    rank_map = {i + 1: int(order.tolist().index(i) + 1) for i in range(n)}
    out = np.zeros_like(grid)
    for i in range(1, n + 1):
        out[labels == i] = rank_map[i]
    return out if not np.array_equal(out, grid) else None


# ═══════════════════════════════════════════════════════════════════
# Tier 5: Direct color ops (common ARC color swaps + recolor enclosed)
# ═══════════════════════════════════════════════════════════════════


@timeit()
def replace_8_to_7(grid: np.ndarray) -> np.ndarray | None:
    """Replace all 8 (cyan) pixels with 7 (orange)."""
    mask = grid == 8
    if not mask.any():
        return None
    out = grid.copy()
    out[mask] = 7
    return out


@timeit()
def replace_1_to_2(grid: np.ndarray) -> np.ndarray | None:
    """Replace all 1 (blue) pixels with 2 (red)."""
    mask = grid == 1
    if not mask.any():
        return None
    out = grid.copy()
    out[mask] = 2
    return out


@timeit()
def replace_3_to_4(grid: np.ndarray) -> np.ndarray | None:
    """Replace all 3 (green) pixels with 4 (yellow)."""
    mask = grid == 3
    if not mask.any():
        return None
    out = grid.copy()
    out[mask] = 4
    return out


@timeit()
def replace_2_to_7(grid: np.ndarray) -> np.ndarray | None:
    """Replace all 2 (red) pixels with 7 (orange). #1 most frequent transition."""
    mask = grid == 2
    if not mask.any():
        return None
    out = grid.copy()
    out[mask] = 7
    return out


@timeit()
def replace_3_to_8(grid: np.ndarray) -> np.ndarray | None:
    """Replace all 3 (green) pixels with 8 (cyan). #4 most frequent."""
    mask = grid == 3
    if not mask.any():
        return None
    out = grid.copy()
    out[mask] = 8
    return out


@timeit()
def replace_5_to_7(grid: np.ndarray) -> np.ndarray | None:
    """Replace all 5 (gray) pixels with 7 (orange). #3 most frequent."""
    mask = grid == 5
    if not mask.any():
        return None
    out = grid.copy()
    out[mask] = 7
    return out


@timeit()
def replace_1_to_6(grid: np.ndarray) -> np.ndarray | None:
    """Replace all 1 (blue) pixels with 6 (magenta). #5 most frequent."""
    mask = grid == 1
    if not mask.any():
        return None
    out = grid.copy()
    out[mask] = 6
    return out


@timeit()
def replace_8_to_1(grid: np.ndarray) -> np.ndarray | None:
    """Replace all 8 (cyan) pixels with 1 (blue). #3 tied."""
    mask = grid == 8
    if not mask.any():
        return None
    out = grid.copy()
    out[mask] = 1
    return out


@timeit()
def replace_0_to_bg(grid: np.ndarray) -> np.ndarray | None:
    """Replace 0 (black) with the most common non-zero color (background fill)."""
    colors = grid[grid != 0]
    if len(colors) == 0:
        return None
    bg = int(np.bincount(colors).argmax())
    mask = grid == 0
    if not mask.any():
        return None
    out = grid.copy()
    out[mask] = bg
    return out


@timeit()
def recolor_enclosed(grid: np.ndarray) -> np.ndarray | None:
    """Fill regions enclosed by a single surrounding color in the original grid.

    For each connected region (of any value) that:
      - Does not touch the grid boundary, and
      - Has its entire dilation boundary (in the ORIGINAL grid) be a single non-zero color

    ...replace it with that surrounding color.  Both zero and non-zero interior
    regions are processed simultaneously from the original grid state, so nested
    frames are handled in one shot: the zero inside the inner frame fills with the
    inner-frame color, and the inner-frame color (enclosed by the outer frame) fills
    with the outer-frame color.

    Returns None if nothing changes.
    """
    from scipy import ndimage as ndi

    out = grid.copy()
    changed = False
    _h, _w = grid.shape
    values = np.unique(grid)

    for v in values:
        region_mask = grid == v
        labeled, n = ndi.label(region_mask)
        for i in range(1, n + 1):
            region = labeled == i
            # Must not touch grid boundary
            if (
                region[0, :].any()
                or region[-1, :].any()
                or region[:, 0].any()
                or region[:, -1].any()
            ):
                continue
            dilated = ndi.binary_dilation(region, iterations=1)
            boundary_mask = dilated & ~region
            # Use original grid colors for boundary (not the evolving `out`)
            boundary_colors = {int(c) for c in grid[boundary_mask].ravel()} - {0, int(v)}
            if len(boundary_colors) == 1:
                out[region] = next(iter(boundary_colors))
                changed = True

    return out if changed else None


# ═══════════════════════════════════════════════════════════════════
# Registry: ALL_TRANSFORMS (29 existing + 5 direct color ops = 34)
# ═══════════════════════════════════════════════════════════════════

ALL_TRANSFORMS: dict[str, TransformFn] = {
    # Tier 0: Geometry
    "rotate_90": rotate_90,
    "rotate_180": rotate_180,
    "rotate_270": rotate_270,
    "flip_horizontal": flip_horizontal,
    "flip_vertical": flip_vertical,
    "transpose": transpose,
    # Tier 1: Grid transforms
    "gravity_fall": gravity_fall,
    "scale_up_2": scale_up_2,
    "scale_down_2": scale_down_2,
    "crop_to_content": crop_to_content,
    # Tier 2: Morphology
    "dilate": dilate,
    "erode": erode,
    "outline": outline,
    # Tier 3: Object ops
    "extract_largest_component": extract_largest_component,
    "flood_fill_expand": flood_fill_expand,
    "remove_background": remove_background,
    # Tier 4: Pattern detection
    "detect_lines": detect_lines,
    "count_objects": count_objects,
    # Tier 5: Direct color ops
    "replace_8_to_7": replace_8_to_7,
    "replace_1_to_2": replace_1_to_2,
    "replace_3_to_4": replace_3_to_4,
    "replace_0_to_bg": replace_0_to_bg,
    "recolor_enclosed": recolor_enclosed,
    "replace_2_to_7": replace_2_to_7,
    "replace_3_to_8": replace_3_to_8,
    "replace_5_to_7": replace_5_to_7,
    "replace_1_to_6": replace_1_to_6,
    "replace_8_to_1": replace_8_to_1,
    # Tier 6: Tiling/Pattern (recovered from pre-prune set)
    "pattern_repeat_row_col": pattern_repeat_row_col,
    "tile_3x3": tile_3x3,
    "tile_grid": functools.partial(tile_grid, tile_h=3, tile_w=3),
    "repeat_rows": functools.partial(repeat_rows, n=2),
    "repeat_cols": functools.partial(repeat_cols, n=2),
    "kronecker_mask_tile": kronecker_mask_tile,
    # Tier 7: Object ops (A.3-A.7)
    "find_largest_object": find_largest_object,
    "object_bbox": object_bbox,
    "fill_interior": fill_interior,
    "remove_small_objects": remove_small_objects,
    "color_map_by_object_size": color_map_by_object_size,
}


# ═══════════════════════════════════════════════════════════════════
# Tier 7: Parameterized color ops (generated dynamically per-task)
# ═══════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════
# Color-aware transform primitives (top-level API)
# ═══════════════════════════════════════════════════════════════════


@timeit()
def color_replace(grid: np.ndarray, old: int, new: int) -> np.ndarray | None:
    """Replace all occurrences of `old` with `new`. Returns None if unchanged."""
    if old == new:
        return None
    mask = grid == old
    if not mask.any():
        return None
    out = grid.copy()
    out[mask] = new
    return out


@timeit()
def color_swap(grid: np.ndarray, a: int, b: int) -> np.ndarray | None:
    """Swap colors `a` and `b` throughout the grid. Returns None if no-op."""
    if a == b:
        return None
    has_a = (grid == a).any()
    has_b = (grid == b).any()
    if not has_a and not has_b:
        return None
    out = grid.copy()
    out[grid == a] = b
    out[grid == b] = a
    return out


@timeit()
def color_filter_keep(grid: np.ndarray, color: int) -> np.ndarray | None:
    """Zero out all cells that are not `color`. Returns None if color absent or no cells to zero.

    Special case: color=0 always returns a result (even if grid is all-zero) because
    zero represents the ARC background and filtering for it is always meaningful.
    """
    present = grid == color
    if not present.any():
        return None  # color not in grid
    out = np.zeros_like(grid)
    out[present] = color
    # Nochange: result equals input (all cells were already target-color or already zero)
    if color != 0 and np.array_equal(out, grid):
        return None
    return out


@timeit()
def color_map_learned(grid: np.ndarray, mapping: dict[int, int]) -> np.ndarray | None:
    """Apply a color remapping dict. Returns None if mapping causes no change."""
    effective = {src: dst for src, dst in mapping.items() if src != dst and (grid == src).any()}
    if not effective:
        return None
    out = grid.copy()
    for src, dst in effective.items():
        out[grid == src] = dst
    return out


@timeit()
def color_majority(grid: np.ndarray) -> np.ndarray | None:
    """For each connected non-zero component, replace minority colors with the component majority.

    Returns None if the grid is already uniform (single color) or all zeros.
    """
    from scipy import ndimage as ndi

    nonzero = grid != 0
    if not nonzero.any():
        return None

    labeled, n = ndi.label(nonzero)
    out = grid.copy()
    changed = False

    for i in range(1, n + 1):
        region = labeled == i
        colors, counts = np.unique(grid[region], return_counts=True)
        majority = int(colors[np.argmax(counts)])
        if not np.all(grid[region] == majority):
            out[region] = majority
            changed = True

    return out if changed else None


@timeit()
def color_background(grid: np.ndarray, bg_color: int | None = None) -> np.ndarray | None:
    """Flood-fill the background color from the grid border.

    With explicit bg_color: replace cells == 0 (implicit old-bg) reachable from the
    border via BFS with bg_color.

    With bg_color=None (auto-detect): detect the dominant border color as the
    background, then flood it into adjacent non-background cells (BFS from border,
    replacing non-bg-color cells with bg_color). Returns None if nothing changes.
    """
    from collections import deque

    h, w = grid.shape
    out = grid.copy()
    changed = False

    if bg_color is None:
        # Auto-detect: most common color on the border
        border_vals = np.concatenate([grid[0, :], grid[-1, :], grid[1:-1, 0], grid[1:-1, -1]])
        vals, cnts = np.unique(border_vals, return_counts=True)
        detected_bg = int(vals[np.argmax(cnts)])
        # BFS from border: spread detected_bg into adjacent non-bg cells
        queue: deque = deque()
        for r in range(h):
            for c in range(w):
                if (r == 0 or r == h - 1 or c == 0 or c == w - 1) and out[r, c] == detected_bg:
                    queue.append((r, c))
        visited = set(queue)
        while queue:
            r, c = queue.popleft()
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited:
                    visited.add((nr, nc))
                    if out[nr, nc] != detected_bg:
                        out[nr, nc] = detected_bg
                        changed = True
                    queue.append((nr, nc))
    else:
        # Explicit: BFS from border replacing cells == 0 (old implicit bg) with bg_color
        queue = deque()
        visited = set()
        for r in range(h):
            for c in range(w):
                if (r == 0 or r == h - 1 or c == 0 or c == w - 1) and grid[r, c] == 0:
                    if out[r, c] != bg_color:
                        out[r, c] = bg_color
                        changed = True
                    queue.append((r, c))
                    visited.add((r, c))
        while queue:
            r, c = queue.popleft()
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in visited:
                    visited.add((nr, nc))
                    if grid[nr, nc] == 0:
                        out[nr, nc] = bg_color
                        changed = True
                        queue.append((nr, nc))

    return out if changed else None


@timeit()
def recolor_interior(grid: np.ndarray) -> np.ndarray | None:
    """Replace any color fully enclosed (not touching grid border) by a single surrounding color.

    For each connected component that does not touch the grid boundary, if its
    dilated neighborhood is a single different color, replace it with that color.
    Returns None if no enclosed regions are found.
    """
    from scipy import ndimage as ndi

    out = grid.copy()
    changed = False
    values = np.unique(grid)
    _h, _w = grid.shape

    for v in values:
        region_mask = grid == v
        labeled, n = ndi.label(region_mask)
        for i in range(1, n + 1):
            region = labeled == i
            # Skip components touching the grid border (they can't be "interior")
            if (
                region[0, :].any()
                or region[-1, :].any()
                or region[:, 0].any()
                or region[:, -1].any()
            ):
                continue
            dilated = ndi.binary_dilation(region, iterations=2)
            boundary_mask = dilated & ~region
            boundary_colors = {int(c) for c in out[boundary_mask].ravel()} - {int(v)}
            if len(boundary_colors) == 1:
                surround = next(iter(boundary_colors))
                out[region] = surround
                changed = True

    return out if changed else None


# Register top-level color ops in ALL_TRANSFORMS (must follow function definitions)
ALL_TRANSFORMS.update(
    {
        "color_replace": functools.partial(color_replace, old=0, new=1),
        "color_swap": functools.partial(color_swap, a=1, b=2),
        "color_filter_keep": functools.partial(color_filter_keep, color=1),
        "color_map_learned": functools.partial(color_map_learned, mapping={1: 2}),
        "recolor_interior": recolor_interior,
        "color_majority": color_majority,
        "color_background": color_background,
        "recolor_enclosed": recolor_enclosed,
    }
)


def make_color_swap(from_color: int, to_color: int) -> TransformFn:
    """Return a closure that swaps one color for another."""

    @timeit()
    def color_swap(grid: np.ndarray) -> np.ndarray | None:
        if from_color == to_color:
            return None
        mask = grid == from_color
        if not mask.any():
            return None
        out = grid.copy()
        out[mask] = to_color
        return out

    return color_swap


def make_color_remap(mapping: dict[int, int]) -> TransformFn:
    """Return a closure that remaps multiple colors at once."""

    @timeit()
    def color_remap(grid: np.ndarray) -> np.ndarray | None:
        out = grid.copy()
        changed = False
        for src, dst in mapping.items():
            if src == dst:
                continue
            mask = grid == src
            if mask.any():
                out[mask] = dst
                changed = True
        return out if changed else None

    return color_remap


# ── Geometry redundancy table ─────────────────────────────────────
# Maps each geometry op to others that become redundant if it's already in the chain.
GEOMETRY_REDUNDANT_IF_PRESENT: dict[str, set[str]] = {
    # If rotate_90 is already in chain, rotate_270 is redundant
    # (rotate_270 = rotate_90 + rotate_180, and rotate_180 is always available)
    "rotate_90": {"rotate_270"},
    "rotate_180": {"rotate_180"},  # double-180 = identity
    "rotate_270": {"rotate_90"},  # rotate_90 = rotate_270 + rotate_180
    "flip_horizontal": {"flip_horizontal"},  # double-flip = identity
    "flip_vertical": {"flip_vertical"},
    "transpose": {"transpose"},  # double-transpose = identity
}


@timeit()
def apply_chain(grid: np.ndarray, chain: list[str]) -> np.ndarray | None:
    """Apply a chain of transforms by name. Returns None if any step fails."""
    current = grid.copy()
    for name in chain:
        fn = ALL_TRANSFORMS.get(name)
        if fn is None:
            return None
        try:
            result = fn(current)
        except Exception:
            return None
        if result is None:
            return None
        if result.shape[0] > 30 or result.shape[1] > 30:
            return None
        current = result
    return current


@timeit()
def get_timing_report() -> dict[str, dict[str, Any]]:
    """Return per-function @timeit statistics for profiling."""
    from cohezion.core.timeit import get_stats

    report: dict[str, dict[str, Any]] = {}
    for name in ALL_TRANSFORMS:
        fn = ALL_TRANSFORMS[name]
        # Unwrap functools.partial to get the decorated function
        actual_fn = fn.func if isinstance(fn, functools.partial) else fn
        try:
            stats = get_stats(actual_fn)
            d = stats.as_dict()
            report[name] = {
                "count": d["count"],
                "total_ms": d["total"],
                "mean_ms": d["mean"],
                "min_ms": d["min"],
                "max_ms": d["max"],
            }
        except AttributeError:
            report[name] = {"count": 0, "total_ms": 0, "mean_ms": 0, "min_ms": 0, "max_ms": 0}
    chain_stats = get_stats(apply_chain)
    cd = chain_stats.as_dict()
    report["apply_chain"] = {
        "count": cd["count"],
        "total_ms": cd["total"],
        "mean_ms": cd["mean"],
        "min_ms": cd["min"],
        "max_ms": cd["max"],
    }
    return report
