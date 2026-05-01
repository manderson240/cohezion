"""ARC-AGI-2 Grid Transform Primitives.

19 transforms derived from K-Search tree (~/.cohezion-research/ksearch/arc_prize.json).
Each transform is a pure function: np.ndarray -> Optional[np.ndarray].
Dimension constraint: grids are 1x1 to 30x30, values 0-9.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np


TransformFn = Callable[[np.ndarray], np.ndarray | None]


# ── Helper: trim zeros from border ────────────────────────────────

def trim_zeros(grid: np.ndarray) -> np.ndarray | None:
    nz = np.argwhere(grid != 0)
    if nz.size == 0:
        return None
    r0, c0 = nz.min(axis=0)
    r1, c1 = nz.max(axis=0)
    return grid[r0:r1+1, c0:c1+1]


# ── Helper: transpose ─────────────────────────────────────────────

def transpose(grid: np.ndarray) -> np.ndarray | None:
    return grid.T


# ── Helper: remove isolated pixels ──────────────────────────────

def remove_isolated_pixels(grid: np.ndarray) -> np.ndarray | None:
    from scipy import ndimage as ndi
    if grid.size < 9:
        return None
    out = grid.copy()
    for c in np.unique(grid):
        if c == 0:
            continue
        mask = grid == c
        labeled, n = ndi.label(mask)
        for i in range(1, n+1):
            if np.sum(labeled == i) == 1:
                out[labeled == i] = 0
    return out if not np.array_equal(out, grid) else None


# ── Helper: outline (edge detect) ───────────────────────────────

def outline(grid: np.ndarray) -> np.ndarray | None:
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


# ── Helper: fill background with most common non-zero color ───────

def fill_background(grid: np.ndarray) -> np.ndarray | None:
    if 0 not in grid:
        return None
    colors = grid[grid != 0]
    if len(colors) == 0:
        return None
    bg = int(np.bincount(colors).argmax())
    out = grid.copy()
    out[out == 0] = bg
    return out


# ── Helper: remove background (set most common to 0) ──────────────

def remove_background(grid: np.ndarray) -> np.ndarray | None:
    vals, counts = np.unique(grid, return_counts=True)
    if len(vals) <= 1:
        return None
    bg = vals[np.argmax(counts)]
    if bg == 0 and len(vals) > 1:
        bg = vals[np.argsort(counts)[-2]]
    out = grid.copy()
    out[out == bg] = 0
    return out if not np.array_equal(out, grid) else None


def invert_colors(grid: np.ndarray) -> np.ndarray | None:
    if np.max(grid) == 0:
        return None
    return 9 - grid


# ── Helper: replace most common color with second most common ─────

def replace_most_common_with_second(grid: np.ndarray) -> np.ndarray | None:
    vals, counts = np.unique(grid, return_counts=True)
    if len(vals) < 2:
        return None
    sorted_idx = np.argsort(counts)
    most = vals[sorted_idx[-1]]
    second = vals[sorted_idx[-2]] if len(vals) > 1 else most
    if most == second:
        return None
    out = grid.copy()
    out[out == most] = second
    return out if not np.array_equal(out, grid) else None


# ── Helper: majority vote (3x3 neighborhood) ────────────────────

def majority_vote(grid: np.ndarray) -> np.ndarray | None:
    from scipy import ndimage as ndi
    if grid.size < 9:
        return None
    result = ndi.rank_filter(grid, rank=4, size=3)
    return result if not np.array_equal(result, grid) else None


# ── Helper: extract largest connected component ────────────────────

def extract_largest_component(grid: np.ndarray) -> np.ndarray | None:
    from scipy import ndimage as ndi
    labels, n = ndi.label(grid != 0)
    if n == 0:
        return None
    largest = max(range(1, n+1), key=lambda i: np.sum(labels == i))
    out = np.zeros_like(grid)
    mask = labels == largest
    out[mask] = grid[mask]
    return out


# ── Helper: color frequency rank map ──────────────────────────────

def color_frequency_map(grid: np.ndarray) -> np.ndarray | None:
    vals, counts = np.unique(grid, return_counts=True)
    if len(vals) <= 1:
        return None
    rank = {v: i for i, v in enumerate(vals[np.argsort(counts)])}
    out = np.vectorize(rank.get)(grid).astype(grid.dtype)
    return out


# ── Helper: extend each color to fill its row/col ─────────────────

def extend_to_row_col(grid: np.ndarray) -> np.ndarray | None:
    out = grid.copy()
    changed = False
    for c in np.unique(grid):
        if c == 0:
            continue
        rows = np.where(np.any(grid == c, axis=1))[0]
        cols = np.where(np.any(grid == c, axis=0))[0]
        for r in rows:
            out[r, :] = c
            changed = True
        for c_idx in cols:
            out[:, c_idx] = c
            changed = True
    return out if changed else None


# ── Helper: move all objects down by 1 ────────────────────────────

def shift_down_1(grid: np.ndarray) -> np.ndarray | None:
    if grid.shape[0] <= 1:
        return None
    out = np.zeros_like(grid)
    out[1:, :] = grid[:-1, :]
    return out


# ── Helper: shift right by 1 ──────────────────────────────────────

def shift_right_1(grid: np.ndarray) -> np.ndarray | None:
    if grid.shape[1] <= 1:
        return None
    out = np.zeros_like(grid)
    out[:, 1:] = grid[:, :-1]
    return out


# ── Helper: count objects and replace with count ──────────────────

def count_objects(grid: np.ndarray) -> np.ndarray | None:
    from scipy import ndimage as ndi
    labels, n = ndi.label(grid != 0)
    if n == 0:
        return None
    out = np.full_like(grid, n)
    return out


# ── 1. Rotations ──────────────────────────────────────────────────

def rotate_90(grid: np.ndarray) -> np.ndarray | None:
    return np.rot90(grid, k=1)


def rotate_180(grid: np.ndarray) -> np.ndarray | None:
    return np.rot90(grid, k=2)


def rotate_270(grid: np.ndarray) -> np.ndarray | None:
    return np.rot90(grid, k=3)


# ── 2. Mirror / Flip ───────────────────────────────────────────────

def flip_horizontal(grid: np.ndarray) -> np.ndarray | None:
    return np.fliplr(grid)


def flip_vertical(grid: np.ndarray) -> np.ndarray | None:
    return np.flipud(grid)


# ── 3. Gravity / Fall downward ───────────────────────────────────

def gravity_fall(grid: np.ndarray) -> np.ndarray | None:
    out = np.zeros_like(grid)
    for col in range(grid.shape[1]):
        non_zero = grid[:, col][grid[:, col] != 0]
        if len(non_zero) > 0:
            out[-len(non_zero):, col] = non_zero
    return out


# ── 4. Color swap ────────────────────────────────────────────────

def color_swap_any_pair(grid: np.ndarray, c1: int = 1, c2: int = 2) -> np.ndarray | None:
    if c1 not in grid and c2 not in grid:
        return None
    out = grid.copy()
    mask1, mask2 = (out == c1), (out == c2)
    out[mask1], out[mask2] = c2, c1
    return out


# ── 5. Connected components (4-way) ──────────────────────────────

def connected_components_4(grid: np.ndarray) -> np.ndarray | None:
    from scipy import ndimage as ndi
    if grid.size == 0:
        return None
    labels, n = ndi.label(grid != 0, structure=np.array([[0,1,0],[1,1,1],[0,1,0]]))
    out = grid.copy()
    out[out != 0] = labels[out != 0]
    return out


# ── 6. Scale up/down by 2 ───────────────────────────────────────

def scale_up_2(grid: np.ndarray) -> np.ndarray | None:
    h, w = grid.shape
    if max(h*2, w*2) > 30:
        return None
    out = np.repeat(np.repeat(grid, 2, axis=0), 2, axis=1)
    return out


def scale_down_2(grid: np.ndarray) -> np.ndarray | None:
    h, w = grid.shape
    if h % 2 or w % 2:
        return None
    return grid.reshape(h//2, 2, w//2, 2).max(axis=(1, 3))


# ── 7. Pattern repeat row/col ───────────────────────────────────

def pattern_repeat_row_col(grid: np.ndarray) -> np.ndarray | None:
    h, w = grid.shape
    for period in range(1, min(h, w)//2 + 1):
        tile = grid[:period, :period]
        if h % period == 0 and w % period == 0:
            recon = np.tile(tile, (h//period, w//period))
            if np.array_equal(recon, grid):
                return np.tile(tile, (2, 2))[:30, :30]
    return None


# ── 8. Morphological dilate / erode ─────────────────────────────

def dilate(grid: np.ndarray) -> np.ndarray | None:
    from scipy import ndimage as ndi
    return ndi.grey_dilation(grid, size=(3, 3))


def erode(grid: np.ndarray) -> np.ndarray | None:
    from scipy import ndimage as ndi
    return ndi.grey_erosion(grid, size=(3, 3))


# ── 9. Noise removal / outlier replacement ─────────────────────

def noise_removal_median(grid: np.ndarray) -> np.ndarray | None:
    from scipy import ndimage as ndi
    if grid.size < 9:
        return None
    return ndi.median_filter(grid, size=3)


# ── 10. Bounding box crop ──────────────────────────────────────

def crop_to_content(grid: np.ndarray) -> np.ndarray | None:
    nz = np.argwhere(grid != 0)
    if nz.size == 0:
        return None
    r0, c0 = nz.min(axis=0)
    r1, c1 = nz.max(axis=0)
    return grid[r0:r1+1, c0:c1+1]


# ── 11. Symmetry detection ─────────────────────────────────────

def detect_mirror_axis(grid: np.ndarray) -> np.ndarray | None:
    if grid.shape[1] % 2 == 0:
        left = grid[:, :grid.shape[1]//2]
        right = np.fliplr(grid[:, grid.shape[1]//2:])
        if np.array_equal(left, right):
            return left
    if grid.shape[0] % 2 == 0:
        top = grid[:grid.shape[0]//2, :]
        bot = np.flipud(grid[grid.shape[0]//2:, :])
        if np.array_equal(top, bot):
            return top
    return None


# ── 12. Object count matching ────────────────────────────────────

def object_count_replace(grid: np.ndarray) -> np.ndarray | None:
    from scipy import ndimage as ndi
    labels, n = ndi.label(grid != 0)
    counts = np.bincount(labels.ravel())[1:]  # skip background
    if len(counts) == 0:
        return None
    mode_count = int(np.bincount(counts).argmax())
    out = grid.copy()
    for i in range(1, n+1):
        if np.sum(labels == i) != mode_count:
            out[labels == i] = 0
    return out


# ── 13. Line detection H/V/Diag ──────────────────────────────────

def detect_lines(grid: np.ndarray) -> np.ndarray | None:
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
    # diagonal
    if grid.shape[0] == grid.shape[1]:
        d = np.diag(grid)
        if np.all(d == d[0]) and d[0] != 0:
            np.fill_diagonal(out, d[0])
            changed = True
    return out if changed else None


# ── 14. Flood fill expansion ─────────────────────────────────────

def flood_fill_expand(grid: np.ndarray) -> np.ndarray | None:
    from scipy import ndimage as ndi
    colors = np.unique(grid[grid != 0])
    if len(colors) == 0:
        return None
    out = grid.copy()
    for c in colors:
        mask = (grid == c)
        if mask.sum() == 0:
            continue
        filled = ndi.binary_fill_holes(mask)
        out[filled] = c
    return out if not np.array_equal(out, grid) else None


# ── 15. XOR overlay ──────────────────────────────────────────────

def xor_overlay(grid: np.ndarray, other: np.ndarray | None = None) -> np.ndarray | None:
    if other is None:
        other = flip_horizontal(grid)
    return np.bitwise_xor(grid, other)


# ── 16. Tile / repeat ────────────────────────────────────────────

def tile_3x3(grid: np.ndarray) -> np.ndarray | None:
    h, w = grid.shape
    if h > 10 or w > 10:
        return None
    out = np.zeros((h*3, w*3), dtype=grid.dtype)
    for i in range(3):
        for j in range(3):
            out[i*h:(i+1)*h, j*w:(j+1)*w] = grid
    return out


def repeat_rows(grid: np.ndarray) -> np.ndarray | None:
    """Repeat each row twice."""
    return np.repeat(grid, 2, axis=0) if grid.shape[0] <= 15 else None


def repeat_cols(grid: np.ndarray) -> np.ndarray | None:
    """Repeat each column twice."""
    return np.repeat(grid, 2, axis=1) if grid.shape[1] <= 15 else None


# ── 17. Set operations ─────────────────────────────────────────────

def union_with_flip(grid: np.ndarray) -> np.ndarray | None:
    return np.maximum(grid, flip_horizontal(grid))


def intersect_with_flip(grid: np.ndarray) -> np.ndarray | None:
    return np.minimum(grid, flip_horizontal(grid))


# ── 18. Color count normalization ─────────────────────────────────

def color_count_normalize(grid: np.ndarray) -> np.ndarray | None:
    """Map rare colors to common ones."""
    vals, counts = np.unique(grid, return_counts=True)
    if len(vals) <= 1:
        return None
    mode_val = vals[np.argmax(counts)]
    out = grid.copy()
    rare = vals[np.argsort(counts)[:len(vals)//2]]
    for r in rare:
        out[out == r] = mode_val
    if np.array_equal(out, grid):
        return None
    return out


# ── 19. Diagonal fill ────────────────────────────────────────────

def diagonal_fill(grid: np.ndarray) -> np.ndarray | None:
    if grid.shape[0] != grid.shape[1]:
        return None
    out = grid.copy()
    for i in range(grid.shape[0]):
        for j in range(i+1, grid.shape[1]):
            if out[i, j] == 0 and out[j, i] != 0:
                out[i, j] = out[j, i]
            if out[j, i] == 0 and out[i, j] != 0:
                out[j, i] = out[i, j]
    if np.array_equal(out, grid):
        return None
    return out


# ── 20. Kronecker mask tile — cell(i,j) maps to block H×W: input if non-zero else zero ──

def kronecker_mask_tile(grid: np.ndarray) -> np.ndarray | None:
    """Each cell replaces itself with a block equal to input if non-zero, else zeros."""
    h, w = grid.shape
    if h > 5 or w > 5:  # output up to 25x25
        return None
    out = np.zeros((h * h, w * w), dtype=grid.dtype)
    for i in range(h):
        for j in range(w):
            if grid[i, j] != 0:
                out[i*h:(i+1)*h, j*w:(j+1)*w] = grid
    if np.array_equal(out, np.zeros_like(out)):
        return None
    return out


# ── 21. Uniform n×n tile ───────────────────────────────────────────

def tile_grid(grid: np.ndarray, n: int = 2) -> np.ndarray | None:
    h, w = grid.shape
    if max(h*n, w*n) > 30:
        return None
    return np.tile(grid, (n, n))


# ── 22. Color map inference ─────────────────────────────────────────

def infer_color_map(grid: np.ndarray, target: np.ndarray | None = None) -> np.ndarray | None:
    """Requires static pattern - only useful as part of solver with training pairs."""
    return None  # placeholder; actual logic needs train data


# ── Composite helpers ───────────────────────────────────────────



# ── Auto-generated color operations ───────────────────────────────

def _generate_color_ops():
    ops = {}

    def _make_repl_0_1(a=0, b=1):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_0_with_1'] = _make_repl_0_1()

    def _make_repl_0_2(a=0, b=2):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_0_with_2'] = _make_repl_0_2()

    def _make_repl_0_3(a=0, b=3):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_0_with_3'] = _make_repl_0_3()

    def _make_repl_0_4(a=0, b=4):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_0_with_4'] = _make_repl_0_4()

    def _make_repl_0_5(a=0, b=5):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_0_with_5'] = _make_repl_0_5()

    def _make_repl_0_6(a=0, b=6):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_0_with_6'] = _make_repl_0_6()

    def _make_repl_0_7(a=0, b=7):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_0_with_7'] = _make_repl_0_7()

    def _make_repl_0_8(a=0, b=8):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_0_with_8'] = _make_repl_0_8()

    def _make_repl_0_9(a=0, b=9):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_0_with_9'] = _make_repl_0_9()

    def _make_repl_1_0(a=1, b=0):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_1_with_0'] = _make_repl_1_0()

    def _make_repl_1_2(a=1, b=2):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_1_with_2'] = _make_repl_1_2()

    def _make_repl_1_3(a=1, b=3):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_1_with_3'] = _make_repl_1_3()

    def _make_repl_1_4(a=1, b=4):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_1_with_4'] = _make_repl_1_4()

    def _make_repl_1_5(a=1, b=5):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_1_with_5'] = _make_repl_1_5()

    def _make_repl_1_6(a=1, b=6):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_1_with_6'] = _make_repl_1_6()

    def _make_repl_1_7(a=1, b=7):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_1_with_7'] = _make_repl_1_7()

    def _make_repl_1_8(a=1, b=8):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_1_with_8'] = _make_repl_1_8()

    def _make_repl_1_9(a=1, b=9):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_1_with_9'] = _make_repl_1_9()

    def _make_repl_2_0(a=2, b=0):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_2_with_0'] = _make_repl_2_0()

    def _make_repl_2_1(a=2, b=1):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_2_with_1'] = _make_repl_2_1()

    def _make_repl_2_3(a=2, b=3):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_2_with_3'] = _make_repl_2_3()

    def _make_repl_2_4(a=2, b=4):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_2_with_4'] = _make_repl_2_4()

    def _make_repl_2_5(a=2, b=5):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_2_with_5'] = _make_repl_2_5()

    def _make_repl_2_6(a=2, b=6):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_2_with_6'] = _make_repl_2_6()

    def _make_repl_2_7(a=2, b=7):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_2_with_7'] = _make_repl_2_7()

    def _make_repl_2_8(a=2, b=8):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_2_with_8'] = _make_repl_2_8()

    def _make_repl_2_9(a=2, b=9):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_2_with_9'] = _make_repl_2_9()

    def _make_repl_3_0(a=3, b=0):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_3_with_0'] = _make_repl_3_0()

    def _make_repl_3_1(a=3, b=1):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_3_with_1'] = _make_repl_3_1()

    def _make_repl_3_2(a=3, b=2):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_3_with_2'] = _make_repl_3_2()

    def _make_repl_3_4(a=3, b=4):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_3_with_4'] = _make_repl_3_4()

    def _make_repl_3_5(a=3, b=5):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_3_with_5'] = _make_repl_3_5()

    def _make_repl_3_6(a=3, b=6):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_3_with_6'] = _make_repl_3_6()

    def _make_repl_3_7(a=3, b=7):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_3_with_7'] = _make_repl_3_7()

    def _make_repl_3_8(a=3, b=8):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_3_with_8'] = _make_repl_3_8()

    def _make_repl_3_9(a=3, b=9):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_3_with_9'] = _make_repl_3_9()

    def _make_repl_4_0(a=4, b=0):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_4_with_0'] = _make_repl_4_0()

    def _make_repl_4_1(a=4, b=1):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_4_with_1'] = _make_repl_4_1()

    def _make_repl_4_2(a=4, b=2):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_4_with_2'] = _make_repl_4_2()

    def _make_repl_4_3(a=4, b=3):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_4_with_3'] = _make_repl_4_3()

    def _make_repl_4_5(a=4, b=5):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_4_with_5'] = _make_repl_4_5()

    def _make_repl_4_6(a=4, b=6):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_4_with_6'] = _make_repl_4_6()

    def _make_repl_4_7(a=4, b=7):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_4_with_7'] = _make_repl_4_7()

    def _make_repl_4_8(a=4, b=8):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_4_with_8'] = _make_repl_4_8()

    def _make_repl_4_9(a=4, b=9):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_4_with_9'] = _make_repl_4_9()

    def _make_repl_5_0(a=5, b=0):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_5_with_0'] = _make_repl_5_0()

    def _make_repl_5_1(a=5, b=1):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_5_with_1'] = _make_repl_5_1()

    def _make_repl_5_2(a=5, b=2):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_5_with_2'] = _make_repl_5_2()

    def _make_repl_5_3(a=5, b=3):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_5_with_3'] = _make_repl_5_3()

    def _make_repl_5_4(a=5, b=4):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_5_with_4'] = _make_repl_5_4()

    def _make_repl_5_6(a=5, b=6):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_5_with_6'] = _make_repl_5_6()

    def _make_repl_5_7(a=5, b=7):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_5_with_7'] = _make_repl_5_7()

    def _make_repl_5_8(a=5, b=8):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_5_with_8'] = _make_repl_5_8()

    def _make_repl_5_9(a=5, b=9):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_5_with_9'] = _make_repl_5_9()

    def _make_repl_6_0(a=6, b=0):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_6_with_0'] = _make_repl_6_0()

    def _make_repl_6_1(a=6, b=1):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_6_with_1'] = _make_repl_6_1()

    def _make_repl_6_2(a=6, b=2):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_6_with_2'] = _make_repl_6_2()

    def _make_repl_6_3(a=6, b=3):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_6_with_3'] = _make_repl_6_3()

    def _make_repl_6_4(a=6, b=4):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_6_with_4'] = _make_repl_6_4()

    def _make_repl_6_5(a=6, b=5):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_6_with_5'] = _make_repl_6_5()

    def _make_repl_6_7(a=6, b=7):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_6_with_7'] = _make_repl_6_7()

    def _make_repl_6_8(a=6, b=8):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_6_with_8'] = _make_repl_6_8()

    def _make_repl_6_9(a=6, b=9):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_6_with_9'] = _make_repl_6_9()

    def _make_repl_7_0(a=7, b=0):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_7_with_0'] = _make_repl_7_0()

    def _make_repl_7_1(a=7, b=1):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_7_with_1'] = _make_repl_7_1()

    def _make_repl_7_2(a=7, b=2):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_7_with_2'] = _make_repl_7_2()

    def _make_repl_7_3(a=7, b=3):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_7_with_3'] = _make_repl_7_3()

    def _make_repl_7_4(a=7, b=4):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_7_with_4'] = _make_repl_7_4()

    def _make_repl_7_5(a=7, b=5):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_7_with_5'] = _make_repl_7_5()

    def _make_repl_7_6(a=7, b=6):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_7_with_6'] = _make_repl_7_6()

    def _make_repl_7_8(a=7, b=8):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_7_with_8'] = _make_repl_7_8()

    def _make_repl_7_9(a=7, b=9):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_7_with_9'] = _make_repl_7_9()

    def _make_repl_8_0(a=8, b=0):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_8_with_0'] = _make_repl_8_0()

    def _make_repl_8_1(a=8, b=1):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_8_with_1'] = _make_repl_8_1()

    def _make_repl_8_2(a=8, b=2):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_8_with_2'] = _make_repl_8_2()

    def _make_repl_8_3(a=8, b=3):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_8_with_3'] = _make_repl_8_3()

    def _make_repl_8_4(a=8, b=4):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_8_with_4'] = _make_repl_8_4()

    def _make_repl_8_5(a=8, b=5):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_8_with_5'] = _make_repl_8_5()

    def _make_repl_8_6(a=8, b=6):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_8_with_6'] = _make_repl_8_6()

    def _make_repl_8_7(a=8, b=7):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_8_with_7'] = _make_repl_8_7()

    def _make_repl_8_9(a=8, b=9):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_8_with_9'] = _make_repl_8_9()

    def _make_repl_9_0(a=9, b=0):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_9_with_0'] = _make_repl_9_0()

    def _make_repl_9_1(a=9, b=1):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_9_with_1'] = _make_repl_9_1()

    def _make_repl_9_2(a=9, b=2):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_9_with_2'] = _make_repl_9_2()

    def _make_repl_9_3(a=9, b=3):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_9_with_3'] = _make_repl_9_3()

    def _make_repl_9_4(a=9, b=4):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_9_with_4'] = _make_repl_9_4()

    def _make_repl_9_5(a=9, b=5):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_9_with_5'] = _make_repl_9_5()

    def _make_repl_9_6(a=9, b=6):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_9_with_6'] = _make_repl_9_6()

    def _make_repl_9_7(a=9, b=7):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_9_with_7'] = _make_repl_9_7()

    def _make_repl_9_8(a=9, b=8):
        def repl(grid):
            if a not in grid:
                return None
            out = grid.copy()
            out[out == a] = b
            return out if not np.array_equal(out, grid) else None
        return repl
    ops['replace_9_with_8'] = _make_repl_9_8()

    def _make_swap_0_1(a=0, b=1):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_0_1'] = _make_swap_0_1()

    def _make_swap_0_2(a=0, b=2):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_0_2'] = _make_swap_0_2()

    def _make_swap_0_3(a=0, b=3):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_0_3'] = _make_swap_0_3()

    def _make_swap_0_4(a=0, b=4):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_0_4'] = _make_swap_0_4()

    def _make_swap_0_5(a=0, b=5):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_0_5'] = _make_swap_0_5()

    def _make_swap_0_6(a=0, b=6):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_0_6'] = _make_swap_0_6()

    def _make_swap_0_7(a=0, b=7):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_0_7'] = _make_swap_0_7()

    def _make_swap_0_8(a=0, b=8):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_0_8'] = _make_swap_0_8()

    def _make_swap_0_9(a=0, b=9):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_0_9'] = _make_swap_0_9()

    def _make_swap_1_2(a=1, b=2):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_1_2'] = _make_swap_1_2()

    def _make_swap_1_3(a=1, b=3):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_1_3'] = _make_swap_1_3()

    def _make_swap_1_4(a=1, b=4):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_1_4'] = _make_swap_1_4()

    def _make_swap_1_5(a=1, b=5):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_1_5'] = _make_swap_1_5()

    def _make_swap_1_6(a=1, b=6):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_1_6'] = _make_swap_1_6()

    def _make_swap_1_7(a=1, b=7):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_1_7'] = _make_swap_1_7()

    def _make_swap_1_8(a=1, b=8):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_1_8'] = _make_swap_1_8()

    def _make_swap_1_9(a=1, b=9):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_1_9'] = _make_swap_1_9()

    def _make_swap_2_3(a=2, b=3):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_2_3'] = _make_swap_2_3()

    def _make_swap_2_4(a=2, b=4):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_2_4'] = _make_swap_2_4()

    def _make_swap_2_5(a=2, b=5):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_2_5'] = _make_swap_2_5()

    def _make_swap_2_6(a=2, b=6):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_2_6'] = _make_swap_2_6()

    def _make_swap_2_7(a=2, b=7):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_2_7'] = _make_swap_2_7()

    def _make_swap_2_8(a=2, b=8):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_2_8'] = _make_swap_2_8()

    def _make_swap_2_9(a=2, b=9):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_2_9'] = _make_swap_2_9()

    def _make_swap_3_4(a=3, b=4):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_3_4'] = _make_swap_3_4()

    def _make_swap_3_5(a=3, b=5):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_3_5'] = _make_swap_3_5()

    def _make_swap_3_6(a=3, b=6):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_3_6'] = _make_swap_3_6()

    def _make_swap_3_7(a=3, b=7):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_3_7'] = _make_swap_3_7()

    def _make_swap_3_8(a=3, b=8):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_3_8'] = _make_swap_3_8()

    def _make_swap_3_9(a=3, b=9):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_3_9'] = _make_swap_3_9()

    def _make_swap_4_5(a=4, b=5):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_4_5'] = _make_swap_4_5()

    def _make_swap_4_6(a=4, b=6):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_4_6'] = _make_swap_4_6()

    def _make_swap_4_7(a=4, b=7):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_4_7'] = _make_swap_4_7()

    def _make_swap_4_8(a=4, b=8):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_4_8'] = _make_swap_4_8()

    def _make_swap_4_9(a=4, b=9):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_4_9'] = _make_swap_4_9()

    def _make_swap_5_6(a=5, b=6):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_5_6'] = _make_swap_5_6()

    def _make_swap_5_7(a=5, b=7):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_5_7'] = _make_swap_5_7()

    def _make_swap_5_8(a=5, b=8):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_5_8'] = _make_swap_5_8()

    def _make_swap_5_9(a=5, b=9):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_5_9'] = _make_swap_5_9()

    def _make_swap_6_7(a=6, b=7):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_6_7'] = _make_swap_6_7()

    def _make_swap_6_8(a=6, b=8):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_6_8'] = _make_swap_6_8()

    def _make_swap_6_9(a=6, b=9):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_6_9'] = _make_swap_6_9()

    def _make_swap_7_8(a=7, b=8):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_7_8'] = _make_swap_7_8()

    def _make_swap_7_9(a=7, b=9):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_7_9'] = _make_swap_7_9()

    def _make_swap_8_9(a=8, b=9):
        def swap(grid):
            if a not in grid and b not in grid:
                return None
            out = grid.copy()
            mask_a, mask_b = (out == a), (out == b)
            out[mask_a], out[mask_b] = b, a
            return out
        return swap
    ops['swap_8_9'] = _make_swap_8_9()

    return ops


_COLOR_OPS = _generate_color_ops()

ALL_TRANSFORMS = {
    "rotate_90": rotate_90,
    "rotate_180": rotate_180,
    "rotate_270": rotate_270,
    "flip_horizontal": flip_horizontal,
    "flip_vertical": flip_vertical,
    "gravity_fall": gravity_fall,
    "scale_up_2": scale_up_2,
    "scale_down_2": scale_down_2,
    "crop_to_content": crop_to_content,
    "trim_zeros": trim_zeros,
    "transpose": transpose,
    "pattern_repeat_row_col": pattern_repeat_row_col,
    "dilate": dilate,
    "erode": erode,
    "noise_removal_median": noise_removal_median,
    "remove_isolated_pixels": remove_isolated_pixels,
    "outline": outline,
    "detect_mirror_axis": detect_mirror_axis,
    "object_count_replace": object_count_replace,
    "detect_lines": detect_lines,
    "flood_fill_expand": flood_fill_expand,
    "fill_background": fill_background,
    "remove_background": remove_background,
    "tile_3x3": tile_3x3,
    "repeat_rows": repeat_rows,
    "repeat_cols": repeat_cols,
    "union_with_flip": union_with_flip,
    "intersect_with_flip": intersect_with_flip,
    "color_count_normalize": color_count_normalize,
    "diagonal_fill": diagonal_fill,
    "kronecker_mask_tile": kronecker_mask_tile,
    "tile_grid": tile_grid,
    "invert_colors": invert_colors,
    "replace_most_common_with_second": replace_most_common_with_second,
    "majority_vote": majority_vote,
    "extract_largest_component": extract_largest_component,
    "color_frequency_map": color_frequency_map,
    "extend_to_row_col": extend_to_row_col,
    "shift_down_1": shift_down_1,
    "shift_right_1": shift_right_1,
    "count_objects": count_objects,
    **_COLOR_OPS,
}


def apply_chain(grid: np.ndarray, chain: list[str]) -> np.ndarray | None:
    current = grid.copy()
    for name in chain:
        fn = ALL_TRANSFORMS.get(name)
        if fn is None:
            return None
        try:
            result = fn(current)
        except Exception:
            return None
        if result is None or result.shape[0] > 30 or result.shape[1] > 30:
            return None
        current = result
    return current
