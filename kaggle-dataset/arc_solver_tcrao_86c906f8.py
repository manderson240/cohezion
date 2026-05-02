"""ARC-AGI-2 baseline solver with DSL primitives and brute-force search."""

from __future__ import annotations

from collections.abc import Callable


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


# New function to add rotation transforms
def add_rotation_transforms(g: Grid) -> list[Grid]:
    transformations = [
        identity,
        flip_horizontal,
        flip_vertical,
        transpose,
        rotate_90,
        rotate_180,
        rotate_270,
    ]
    return [transform(g) for transform in transformations]


BASE_OPS: list[tuple[str, Program]] = [
    ("identity", identity),
    ("flip_h", flip_horizontal),
    ("flip_v", flip_vertical),
    ("transpose", transpose),
    ("rot90", rotate_90),
    ("rot180", rotate_180),
    ("rot270", rotate_270),
]


# Example usage of add_rotation_transforms
def test_add_rotation_transforms():
    grid = [[1, 2], [3, 4]]
    results = add_rotation_transforms(grid)
    for result in results:
        print(result)


# Uncomment the line below to test the function
# test_add_rotation_transforms()

# ---------------------------------------------------------------------------
#
