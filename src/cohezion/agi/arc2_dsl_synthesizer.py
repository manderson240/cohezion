"""Fast-Path Neuro-Symbolic DSL Program Synthesizer for ARC-AGI-2.

Searches a space of deterministic geometric, topological, and compositional
primitives against training demonstration pairs. If a synthesized program
achieves 100% exact match across all demo pairs, it evaluates the test grid
in <1 ms with 0 hallucination and confidence 1.0.
"""

from __future__ import annotations

import itertools
import numpy as np
from typing import Callable, Any, Optional

Grid = list[list[int]]


def to_np(grid: Grid) -> np.ndarray:
    return np.array(grid, dtype=np.int32)


def to_grid(arr: np.ndarray) -> Grid:
    return arr.tolist()


# --- Geometric Primitives ---

def d4_transforms(arr: np.ndarray) -> dict[str, np.ndarray]:
    """Return all 8 elements of the Dihedral group D4."""
    return {
        "R0": arr.copy(),
        "R90": np.rot90(arr, -1),
        "R180": np.rot90(arr, 2),
        "R270": np.rot90(arr, 1),
        "SH": np.flipud(arr),
        "SV": np.fliplr(arr),
        "SD": arr.T,
        "SAD": np.rot90(np.rot90(arr.T, 1), 1),
    }


def color_substitutions(x: np.ndarray, y: np.ndarray) -> Optional[dict[int, int]]:
    """Infer a deterministic color mapping sigma: x -> y if dimensions match."""
    if x.shape != y.shape:
        return None
    mapping: dict[int, int] = {}
    for cx, cy in zip(x.flat, y.flat):
        if cx in mapping:
            if mapping[cx] != cy:
                return None
        else:
            mapping[cx] = cy
    return mapping


def apply_mapping(arr: np.ndarray, mapping: dict[int, int]) -> np.ndarray:
    out = arr.copy()
    for src, dst in mapping.items():
        out[arr == src] = dst
    return out


# --- Cropping & Subgrid Primitives ---

def crop_bounding_box(arr: np.ndarray, bg_color: int = 0) -> np.ndarray:
    coords = np.argwhere(arr != bg_color)
    if len(coords) == 0:
        return arr
    r_min, c_min = coords.min(axis=0)
    r_max, c_max = coords.max(axis=0)
    return arr[r_min : r_max + 1, c_min : c_max + 1]


def crop_most_frequent_color_box(arr: np.ndarray, bg_color: int = 0) -> np.ndarray:
    unique, counts = np.unique(arr[arr != bg_color], return_counts=True)
    if len(unique) == 0:
        return arr
    dom_color = unique[np.argmax(counts)]
    coords = np.argwhere(arr == dom_color)
    r_min, c_min = coords.min(axis=0)
    r_max, c_max = coords.max(axis=0)
    return arr[r_min : r_max + 1, c_min : c_max + 1]


# --- Tiling & Scaling Primitives ---

def scale_grid(arr: np.ndarray, factor: int) -> np.ndarray:
    return np.repeat(np.repeat(arr, factor, axis=0), factor, axis=1)


def tile_grid(arr: np.ndarray, reps: tuple[int, int]) -> np.ndarray:
    return np.tile(arr, reps)


# --- Gravity Primitives ---

def gravity_fall(arr: np.ndarray, direction: str = "down", bg_color: int = 0) -> np.ndarray:
    h, w = arr.shape
    out = np.full((h, w), bg_color, dtype=np.int32)
    
    if direction == "down":
        for c in range(w):
            col = arr[:, c]
            vals = col[col != bg_color]
            out[h - len(vals) :, c] = vals
    elif direction == "up":
        for c in range(w):
            col = arr[:, c]
            vals = col[col != bg_color]
            out[: len(vals), c] = vals
    elif direction == "right":
        for r in range(h):
            row = arr[r, :]
            vals = row[row != bg_color]
            out[r, w - len(vals) :] = vals
    elif direction == "left":
        for r in range(h):
            row = arr[r, :]
            vals = row[row != bg_color]
            out[r, : len(vals)] = vals
    return out


# --- Synthesis Engine ---

class ARCDSLSynthesizer:
    """Synthesizes and validates candidate Python functions on demo pairs."""

    def __init__(self, timeout_ms: float = 100.0) -> None:
        self.timeout_ms = timeout_ms

    def synthesize(self, train_pairs: list[tuple[Grid, Grid]]) -> Optional[Callable[[Grid], Grid]]:
        if not train_pairs:
            return None

        np_pairs = [(to_np(x), to_np(y)) for x, y in train_pairs]

        # 1. Identity Check
        if all(np.array_equal(x, y) for x, y in np_pairs):
            return lambda g: g

        # 2. Pure D4 Geometric Transformation Check
        d4_ops = ["R0", "R90", "R180", "R270", "SH", "SV", "SD", "SAD"]
        for op in d4_ops:
            if all(np.array_equal(d4_transforms(x)[op], y) for x, y in np_pairs):
                return lambda g, o=op: to_grid(d4_transforms(to_np(g))[o])

        # 3. Global Color Substitution Map (with optional D4 op)
        for op in d4_ops:
            maps = [color_substitutions(d4_transforms(x)[op], y) for x, y in np_pairs]
            if all(m is not None for m in maps):
                # Check if all mappings are consistent
                merged: dict[int, int] = {}
                consistent = True
                for m in maps:
                    assert m is not None
                    for k, v in m.items():
                        if k in merged and merged[k] != v:
                            consistent = False
                            break
                        merged[k] = v
                    if not consistent:
                        break
                if consistent:
                    return lambda g, o=op, m=merged: to_grid(apply_mapping(d4_transforms(to_np(g))[o], m))

        # 4. Bounding Box Cropping (with optional D4 op)
        for op in d4_ops:
            if all(np.array_equal(crop_bounding_box(d4_transforms(x)[op]), y) for x, y in np_pairs):
                return lambda g, o=op: to_grid(crop_bounding_box(d4_transforms(to_np(g))[o]))

        # 5. Most Frequent Color Box Cropping
        for op in d4_ops:
            if all(np.array_equal(crop_most_frequent_color_box(d4_transforms(x)[op]), y) for x, y in np_pairs):
                return lambda g, o=op: to_grid(crop_most_frequent_color_box(d4_transforms(to_np(g))[o]))

        # 6. Uniform Scaling (2x, 3x, 4x)
        for factor in [2, 3, 4]:
            for op in d4_ops:
                if all(np.array_equal(scale_grid(d4_transforms(x)[op], factor), y) for x, y in np_pairs):
                    return lambda g, o=op, f=factor: to_grid(scale_grid(d4_transforms(to_np(g))[o], f))

        # 7. Tiling (2x2, 3x3, 1x2, 2x1, 1x3, 3x1)
        for reps in [(2, 2), (3, 3), (1, 2), (2, 1), (1, 3), (3, 1)]:
            for op in d4_ops:
                if all(np.array_equal(tile_grid(d4_transforms(x)[op], reps), y) for x, y in np_pairs):
                    return lambda g, o=op, r=reps: to_grid(tile_grid(d4_transforms(to_np(g))[o], r))

        # 8. Directional Gravity
        for direction in ["down", "up", "right", "left"]:
            if all(np.array_equal(gravity_fall(x, direction), y) for x, y in np_pairs):
                return lambda g, d=direction: to_grid(gravity_fall(to_np(g), d))

        return None
