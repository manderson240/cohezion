"""ARC-AGI-2 baseline solver with DSL primitives and brute-force search."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

Grid = list[list[int]]
Program = Callable[[Grid], Grid | None]


def _rows(g: Grid) -> int:
    return len(g)


def _cols(g: Grid) -> int:
    return len(g[0]) if g else 0


def deepcopy_grid(g: Grid) -> Grid:
    return [r[:] for r in g]


def identity(g: Grid) -> Grid:
    return deepcopy_grid(g)


def flip_horizontal(g: Grid) -> Grid:
    return [r[:] for r in reversed(g)]


def flip_vertical(g: Grid) -> Grid:
    return [r[::-1] for r in g]


def transpose(g: Grid) -> Grid:
    if not g:
        return []
    return [[g[r][c] for r in range(len(g))] for c in range(len(g[0]))]


def rotate_90(g: Grid) -> Grid:
    if not g:
        return []
    return [[g[r][c] for r in range(len(g))] for c in range(len(g[0]) - 1, -1, -1)]


def rotate_180(g: Grid) -> Grid:
    return [r[::-1] for r in reversed(g)]


def rotate_270(g: Grid) -> Grid:
    if not g:
        return []
    return [[g[r][c] for r in range(len(g) - 1, -1, -1)] for c in range(len(g[0]))]


BASE_OPS: list[tuple[str, Program]] = [
    ("identity", identity),
    ("flip_h", flip_horizontal),
    ("flip_v", flip_vertical),
    ("transpose", transpose),
    ("rot90", rotate_90),
    ("rot180", rotate_180),
    ("rot270", rotate_270),
]


# ---------------------------------------------------------------------------
# Object detection
# ---------------------------------------------------------------------------

def _neighbors4(r: int, c: int, rows: int, cols: int) -> list[tuple[int, int]]:
    out = []
    if r > 0:
        out.append((r - 1, c))
    if r < rows - 1:
        out.append((r + 1, c))
    if c > 0:
        out.append((r, c - 1))
    if c < cols - 1:
        out.append((r, c + 1))
    return out


def _neighbors8(r: int, c: int, rows: int, cols: int) -> list[tuple[int, int]]:
    out = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                out.append((nr, nc))
    return out


def find_objects(g: Grid, conn: int = 4) -> tuple[list[set[tuple[int, int]]], dict[tuple[int, int], int]]:
    """Find connected components of non-background color."""
    if not g:
        return [], {}
    rows, cols = len(g), len(g[0])
    # Background = most common color
    bg = _most_common_color(g)
    visited = [[False] * cols for _ in range(rows)]
    objects = []
    nbr_fn = _neighbors4 if conn == 4 else _neighbors8
    for r in range(rows):
        for c in range(cols):
            if visited[r][c] or g[r][c] == bg:
                continue
            stack = [(r, c)]
            visited[r][c] = True
            obj = set()
            while stack:
                cr, cc = stack.pop()
                obj.add((cr, cc))
                for nr, nc in nbr_fn(cr, cc, rows, cols):
                    if not visited[nr][nc] and g[nr][nc] != bg:
                        visited[nr][nc] = True
                        stack.append((nr, nc))
            objects.append(obj)
    cell2obj = {}
    for i, obj in enumerate(objects):
        for cell in obj:
            cell2obj[cell] = i
    return objects, cell2obj


def _most_common_color(g: Grid) -> int:
    cnt = Counter(c for row in g for c in row)
    if not cnt:
        return 0
    return cnt.most_common(1)[0][0]


def bounding_box(obj: set[tuple[int, int]]) -> tuple[int, int, int, int]:
    rs, cs = zip(*obj)
    return min(rs), min(cs), max(rs), max(cs)


def crop_to_object(g: Grid) -> Grid | None:
    objects, _ = find_objects(g, conn=4)
    if not objects:
        return None
    for obj in objects:
        top, left, bottom, right = bounding_box(obj)
        cropped = [row[left : right + 1] for row in g[top : bottom + 1]]
        if len(cropped) == len(g) and all(len(r) == len(g[0]) for r in cropped):
            continue
        return cropped
    return None


def remove_background(g: Grid) -> Grid | None:
    bg = _most_common_color(g)
    new_grid = [[0 if c == bg else c for c in row] for row in g]
    if new_grid == g:
        return None
    return new_grid


def count_colors(g: Grid) -> int:
    return len(set(c for row in g for c in row))


def grid_to_colors(g: Grid) -> set[int]:
    return set(c for row in g for c in row)


# ---------------------------------------------------------------------------
# Color remapping primitives
# ---------------------------------------------------------------------------

def replace_color(g: Grid, old: int, new: int) -> Grid | None:
    if not any(c == old for row in g for c in row):
        return None
    return [[new if c == old else c for c in row] for row in g]


def swap_colors(g: Grid, c1: int, c2: int) -> Grid | None:
    has1 = any(c == c1 for row in g for c in row)
    has2 = any(c == c2 for row in g for c in row)
    if not (has1 and has2):
        return None
    return [[c2 if c == c1 else (c1 if c == c2 else c) for c in row] for row in g]


def keep_only(g: Grid, keep: int) -> Grid | None:
    if not any(c == keep for row in g for c in row):
        return None
    bg = _most_common_color(g)
    return [[c if c == keep else bg for c in row] for row in g]


def invert_colors(g: Grid) -> Grid | None:
    colors = sorted(set(c for row in g for c in row))
    if len(colors) != 2:
        return None
    c1, c2 = colors
    return swap_colors(g, c1, c2)


# ---------------------------------------------------------------------------
# Geometric / fill primitives
# ---------------------------------------------------------------------------

def pad_to_object(g: Grid) -> Grid | None:
    """Crop to largest non-background object and center it."""
    cropped = crop_to_object(g)
    return cropped


def fill_holes(g: Grid) -> Grid | None:
    if not g:
        return None
    rows, cols = len(g), len(g[0])
    bg = _most_common_color(g)
    out = [r[:] for r in g]
    changed = False
    # Fill cells surrounded by non-background on all 4 sides
    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            if out[r][c] == bg:
                neighbors = {
                    out[r - 1][c], out[r + 1][c],
                    out[r][c - 1], out[r][c + 1]
                }
                if bg not in neighbors and len(neighbors) == 1:
                    out[r][c] = next(iter(neighbors))
                    changed = True
    return out if changed else None


def border(g: Grid) -> Grid | None:
    if not g or len(g) < 3 or len(g[0]) < 3:
        return None
    bg = _most_common_color(g)
    rows, cols = len(g), len(g[0])
    result = [[bg] * cols for _ in range(rows)]
    for r in range(rows):
        result[r][0] = g[r][0]
        result[r][cols - 1] = g[r][cols - 1]
    for c in range(cols):
        result[0][c] = g[0][c]
        result[rows - 1][c] = g[rows - 1][c]
    return result if result != g else None


def interior(g: Grid) -> Grid | None:
    if not g or len(g) < 3 or len(g[0]) < 3:
        return None
    rows, cols = len(g), len(g[0])
    result = [r[:] for r in g]
    bg = _most_common_color(g)
    for c in range(cols):
        result[0][c] = bg
        result[rows - 1][c] = bg
    for r in range(rows):
        result[r][0] = bg
        result[r][cols - 1] = bg
    return result if result != g else None


# ---------------------------------------------------------------------------
# Grid scaling / tiling
# ---------------------------------------------------------------------------

def upsample(n: int) -> Program:
    def fn(g: Grid) -> Grid | None:
        if not g:
            return None
        rows, cols = len(g), len(g[0])
        if rows * n > 30 or cols * n > 30:
            return None
        return [
            [g[r // n][c // n] for c in range(cols * n)]
            for r in range(rows * n)
        ]
    return fn


def downsample(n: int) -> Program:
    def fn(g: Grid) -> Grid | None:
        if not g:
            return None
        rows, cols = len(g), len(g[0])
        if rows % n or cols % n:
            return None
        return [
            [g[r * n][c * n] for c in range(cols // n)]
            for r in range(rows // n)
        ]
    return fn


def mirror_horizontal(g: Grid) -> Grid | None:
    if not g:
        return None
    rows = len(g)
    result = g + [r[:] for r in reversed(g)]
    return result if len(result) <= 30 else None


def mirror_vertical(g: Grid) -> Grid | None:
    if not g or not g[0]:
        return None
    result = [r + r[::-1] for r in g]
    return result if all(len(r) <= 30 for r in result) else None


def diagonal_symmetry(g: Grid) -> Grid | None:
    if not g:
        return None
    if len(g) != len(g[0]):
        return None
    result = [r[:] for r in g]
    changed = False
    for r in range(len(g)):
        for c in range(r + 1, len(g[0])):
            if result[r][c] != result[c][r]:
                result[r][c] = result[c][r]
                changed = True
    return result if changed else None


# ---------------------------------------------------------------------------
# Object manipulation
# ---------------------------------------------------------------------------

def move_objects_up(g: Grid) -> Grid | None:
    objects, _ = find_objects(g)
    if len(objects) != 1:
        return None
    bg = _most_common_color(g)
    rows, cols = len(g), len(g[0])
    result = [[bg] * cols for _ in range(rows)]
    obj = objects.pop()
    top, left, _, _ = bounding_box(obj)
    for r, c in obj:
        nr = r - top
        if nr < 0 or nr >= rows:
            return None
        result[nr][c] = g[r][c]
    return result if result != g else None


def order_objects_by_size(g: Grid) -> Grid | None:
    objects, _ = find_objects(g, conn=4)
    if len(objects) < 2:
        return None
    # Sort by size, recolor in order
    sizes = [(i, len(obj)) for i, obj in enumerate(objects)]
    sizes.sort(key=lambda x: x[1])
    color_map = {}
    for rank, (orig_idx, _) in enumerate(sizes):
        color_map[orig_idx] = rank + 1  # 1-indexed for objects
    rows, cols = len(g), len(g[0])
    bg = _most_common_color(g)
    result = [[bg] * cols for _ in range(rows)]
    for i, obj in enumerate(objects):
        for r, c in obj:
            result[r][c] = color_map[i]
    return result if result != g else None


# ---------------------------------------------------------------------------
# Primitive registry for meta-search
# ---------------------------------------------------------------------------

def _make_parametric() -> list[tuple[str, Program]]:
    out: list[tuple[str, Program]] = []
    for n in (2, 3):
        out.append((f"upsample{n}", upsample(n)))
        out.append((f"downsample{n}", downsample(n)))
    return out


ALL_OPS: list[tuple[str, Program]] = [
    *BASE_OPS,
    ("crop_obj", crop_to_object),
    ("remove_bg", remove_background),
    ("fill_holes", fill_holes),
    ("border", border),
    ("interior", interior),
    ("pad_obj", pad_to_object),
    ("mirror_h", mirror_horizontal),
    ("mirror_v", mirror_vertical),
    ("diag_sym", diagonal_symmetry),
    ("invert", invert_colors),
    ("move_up", move_objects_up),
    ("order_objs", order_objects_by_size),
    *_make_parametric(),
]


def apply_program(g: Grid, program: list[Program]) -> Grid | None:
    result = deepcopy_grid(g)
    for op in program:
        result = op(result)
        if result is None:
            return None
    return result


def grids_equal(a: Grid | None, b: Grid | None) -> bool:
    if a is None or b is None:
        return False
    if len(a) != len(b):
        return False
    if not a:
        return not b
    if any(len(ar) != len(br) for ar, br in zip(a, b)):
        return False
    return all(ar == br for ar, br in zip(a, b))


def search_program(
    train: list[dict[str, Grid]],
    max_depth: int = 3,
    ops: list[tuple[str, Program]] | None = None,
    budget: int = 500,
) -> list[Program] | None:
    if ops is None:
        ops = ALL_OPS
    visited = set()
    for depth in range(1, max_depth + 1):
        result = _search_depth_bfs(train, depth, ops, budget, visited)
        if result is not None:
            return result
    # Fallback to identity
    if all(grids_equal(train[0].get("input"), ex.get("input")) for ex in train):
        return None
    return None


def _search_depth_bfs(
    train: list[dict[str, Grid]],
    depth: int,
    ops: list[tuple[str, Program]],
    budget: int,
    visited: set[str],
) -> list[Program] | None:
    checked = 0
    if depth == 1:
        for name, op in ops:
            checked += 1
            if checked > budget:
                break
            if all(grids_equal(op(deepcopy_grid(ex["input"])), ex["output"]) for ex in train):
                return [op]
        return None
    for name, op in ops:
        transformed = []
        valid = True
        for ex in train:
            t = op(deepcopy_grid(ex["input"]))
            if t is None:
                valid = False
                break
            transformed.append({"input": t, "output": ex["output"]})
        if not valid:
            continue
        sub = _search_depth_bfs(transformed, depth - 1, ops, budget // len(ops), visited)
        if sub is not None:
            return [op, *sub]
    return None


def solve_task(task: dict[str, Any], max_depth: int = 3) -> dict[str, list[dict[str, Grid]]]:
    program = search_program(task["train"], max_depth=max_depth)
    predictions: list[dict[str, Grid]] = []
    for test_example in task.get("test", []):
        pred1 = apply_program(test_example["input"], program or [identity])
        pred2 = None
        if program:
            pred2 = apply_program(transpose(test_example["input"]), program)
            if pred2 is not None:
                pred2 = transpose(pred2)
        pred2 = pred2 or pred1
        predictions.append({"attempt_1": [pred1], "attempt_2": [pred2]})
    return {task["id"]: predictions}