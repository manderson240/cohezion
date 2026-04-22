"""ARC-AGI-2 baseline solver with DSL primitives and brute-force search."""

from __future__ import annotations

import json
import operator
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

Grid = list[list[int]]
Program = Callable[[Grid], Grid | None]


def identity(g: Grid) -> Grid:
    return deepcopy(g)


def flip_horizontal(g: Grid) -> Grid:
    return [row[::-1] for row in g]


def flip_vertical(g: Grid) -> Grid:
    return g[::-1]


def transpose(g: Grid) -> Grid:
    if not g:
        return []
    return [[g[r][c] for r in range(len(g))] for c in range(len(g[0]))]


def rotate_90(g: Grid) -> Grid:
    if not g:
        return []
    return [[g[r][c] for r in range(len(g) - 1, -1, -1)] for c in range(len(g[0]))]


def rotate_180(g: Grid) -> Grid:
    return [row[::-1] for row in g[::-1]]


def rotate_270(g: Grid) -> Grid:
    if not g:
        return []
    return [[g[r][c] for r in range(len(g))] for c in range(len(g[0]) - 1, -1, -1)]


BASE_OPS: list[tuple[str, Program]] = [
    ("identity", identity),
    ("flip_h", flip_horizontal),
    ("flip_v", flip_vertical),
    ("transpose", transpose),
    ("rot90", rotate_90),
    ("rot180", rotate_180),
    ("rot270", rotate_270),
]


def crop_background(g: Grid) -> Grid | None:
    colors = set(c for row in g for c in row)
    if len(colors) < 2:
        return None
    bg = max(colors, key=lambda c: sum(r.count(c) for r in g))
    rows, cols = len(g), len(g[0])
    top = next((r for r in range(rows) if any(c != bg for c in g[r])), None)
    if top is None:
        return None
    bottom = next((r for r in range(rows - 1, -1, -1) if any(c != bg for c in g[r])), None)
    left = next((c for c in range(cols) if any(g[r][c] != bg for r in range(rows))), None)
    right = next((c for c in range(cols - 1, -1, -1) if any(g[r][c] != bg for r in range(rows))), None)
    assert top is not None and bottom is not None and left is not None and right is not None
    return [row[left : right + 1] for row in g[top : bottom + 1]]


def pad_to_symmetric(g: Grid) -> Grid | None:
    """Make grid square by padding with dominant color."""
    if not g:
        return None
    rows, cols = len(g), len(g[0])
    if rows == cols:
        return None
    color = max(g[0], key=lambda c: sum(r.count(c) for r in g))
    target = max(rows, cols)
    result = []
    for row in g:
        new_row = row + [color] * (target - cols) if len(row) < target else row[:target]
        result.append(new_row)
    while len(result) < target:
        result.append([color] * target)
    return result


def recolor(g: Grid) -> Grid | None:
    colors = sorted(set(c for row in g for c in row))
    if len(colors) < 2:
        return None
    mapping = {old: new for old, new in zip(colors, range(len(colors)))}
    return [[mapping[c] for c in row] for row in g]


# Map each color to a new color based on frequency order (ascending).
def remap_frequency(g: Grid) -> Grid | None:
    freq: dict[int, int] = {}
    for row in g:
        for c in row:
            freq[c] = freq.get(c, 0) + 1
    sorted_colours = sorted(freq, key=lambda c: (freq[c], c))
    mapping = {old: i for i, old in enumerate(sorted_colours)}
    return [[mapping[c] for c in row] for row in g]


# Replace most frequent color with 0, others by unique index.
def normalize_bg(g: Grid) -> Grid | None:
    if not g:
        return None
    colors = list(set(c for row in g for c in row))
    if len(colors) < 2:
        return None
    bg = max(colors, key=lambda c: sum(r.count(c) for r in g))
    others = sorted([c for c in colors if c != bg])
    mapping = {bg: 0}
    mapping.update({old: i + 1 for i, old in enumerate(others)})
    return [[mapping.get(c, c) for c in row] for row in g]


# Upsample grid by repeating each cell n times in both dimensions.
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


# Downsample by taking every n-th cell.
def downsample(n: int) -> Program:
    def fn(g: Grid) -> Grid | None:
        if not g:
            return None
        rows, cols = len(g), len(g[0])
        if rows < n or cols < n:
            return None
        return [
            [g[r * n][c * n] for c in range(cols // n)]
            for r in range(rows // n)
        ]
    return fn


# Fill enclosed areas with specific color.
def flood_fill_enclosed(g: Grid) -> Grid | None:
    if not g:
        return None
    rows, cols = len(g), len(g[0])
    if rows < 3 or cols < 3:
        return None
    bg = max(set(c for row in g for c in row), key=lambda c: sum(r.count(c) for r in g))
    result = [row[:] for row in g]
    # Simple scanline fill for rows/columns completely surrounded
    for r in range(rows):
        for c in range(cols):
            if result[r][c] == bg:
                # Check if enclosed
                blocked = (
                    r > 0 and result[r - 1][c] != bg
                    and r < rows - 1 and result[r + 1][c] != bg
                    and c > 0 and result[r][c - 1] != bg
                    and c < cols - 1 and result[r][c + 1] != bg
                )
                if blocked:
                    result[r][c] = 2  # arbitrary fill color
    return result if result != g else None


ALL_OPS: list[tuple[str, Program]] = [
    *BASE_OPS,
    ("crop_bg", crop_background),
    ("pad_sym", pad_to_symmetric),
    ("recolor", recolor),
    ("remap_freq", remap_frequency),
    ("normalize_bg", normalize_bg),
    ("upsample2", upsample(2)),
    ("downsample2", downsample(2)),
    ("flood_enclosed", flood_fill_enclosed),
]


def apply_program(g: Grid, program: list[Program]) -> Grid | None:
    """Apply a sequence of operations to a grid."""
    result = deepcopy(g)
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
) -> list[Program] | None:
    """Brute-force search for a single program that matches all training examples."""
    if ops is None:
        ops = ALL_OPS
    for depth in range(1, max_depth + 1):
        result = _search_depth(train, depth, ops)
        if result is not None:
            return result
    return None


def _search_depth(
    train: list[dict[str, Grid]],
    depth: int,
    ops: list[tuple[str, Program]],
) -> list[Program] | None:
    """Depth-limited DFS."""
    if depth == 0:
        return []
    # Try single op
    for name, op in ops:
        if all(grids_equal(op(ex["input"]), ex["output"]) for ex in train):
            return [op]
    # Try combining with recursive search
    if depth > 1:
        for name, op in ops:
            transformed_train = []
            valid = True
            for ex in train:
                t = op(deepcopy(ex["input"]))
                if t is None:
                    valid = False
                    break
                transformed_train.append({"input": t, "output": ex["output"]})
            if not valid:
                continue
            sub = _search_depth(transformed_train, depth - 1, ops)
            if sub is not None:
                return [op, *sub]
    return None


def solve_task(task: dict[str, Any], max_depth: int = 3) -> dict[str, list[dict[str, Grid]]]:
    """Solve a single ARC task. Returns predictions per test example."""
    program = search_program(task["train"], max_depth=max_depth)
    predictions: list[dict[str, Grid]] = []
    for test_example in task.get("test", []):
        pred1 = apply_program(test_example["input"], program or [identity])
        # Second attempt: try a slightly different heuristic
        pred2 = None
        if program:
            # Try same program on transposed input
            pred2 = apply_program(transpose(test_example["input"]), program)
            if pred2 is not None:
                pred2 = transpose(pred2)
        pred2 = pred2 or pred1
        predictions.append({"attempt_1": [pred1], "attempt_2": [pred2]})
    return {task["id"]: predictions}
