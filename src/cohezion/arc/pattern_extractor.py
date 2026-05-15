"""Pattern Rule Extractor using Compound Engineering.

Extracts human-readable, verifiable transformation rules from ARC task training
examples by combining:

1. Geometric primitive search (DSL ops from arc_solver)
2. Compound-engineering consensus voting across multiple search strategies
3. FLUME 256-D latent similarity for analogy detection
4. HIHO-gated rule confidence scoring

The output is a list of ``CompoundRule`` objects that can be serialized,
verified, and fed into the submission builder.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cohezion.arc.codec import ARCCodec, Grid, grids_equal


# ---------------------------------------------------------------------------
# Dependencies: try to import solver ops, fall back gracefully
# ---------------------------------------------------------------------------
try:
    from cohezion.competition.arc_solver import get_all_ops as _get_solver_ops
    from cohezion.competition.arc_solver import search_program
except Exception:
    get_all_ops = None  # type: ignore[misc]
    search_program = None  # type: ignore[misc]
else:
    get_all_ops = _get_solver_ops

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------
Program = Callable[[Grid], Grid | None]


# ---------------------------------------------------------------------------
# CompoundRule dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CompoundRule:
    """A verified transformation rule extracted by compound engineering."""

    name: str  # e.g. "color_map + gravity_down"
    ops: tuple[str, ...]  # ordered primitive names
    confidence: float  # 0..1, compound consensus score
    train_coverage: float  # fraction of train examples matched
    strategy_votes: int  # how many search strategies agreed
    hiho_score: float  # geometric coherence of the rule
    latent_delta: tuple[float, ...]  # mean 256-D delta vector (latent analogy)
    signature: str  # deterministic SHA-256 of op sequence

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ops": list(self.ops),
            "confidence": self.confidence,
            "train_coverage": self.train_coverage,
            "strategy_votes": self.strategy_votes,
            "hiho_score": self.hiho_score,
            "latent_delta": list(self.latent_delta),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CompoundRule:
        return cls(
            name=d["name"],
            ops=tuple(d["ops"]),
            confidence=d["confidence"],
            train_coverage=d["train_coverage"],
            strategy_votes=d["strategy_votes"],
            hiho_score=d["hiho_score"],
            latent_delta=tuple(d["latent_delta"]),
            signature=d["signature"],
        )


# ---------------------------------------------------------------------------
# Primitive registry (inline fallback so extractor works even if solver import fails)
# ---------------------------------------------------------------------------


def _identity(g: Grid) -> Grid:
    return [r[:] for r in g]


def _transpose(g: Grid) -> Grid:
    if not g:
        return []
    return [[g[r][c] for r in range(len(g))] for c in range(len(g[0]))]


def _rot90(g: Grid) -> Grid:
    if not g:
        return []
    return [[g[r][c] for r in range(len(g))] for c in range(len(g[0]) - 1, -1, -1)]


def _rot180(g: Grid) -> Grid:
    return [r[::-1] for r in reversed(g)]


def _flip_h(g: Grid) -> Grid:
    return [r[:] for r in reversed(g)]


def _flip_v(g: Grid) -> Grid:
    return [r[::-1] for r in g]


def _replace_color(g: Grid, old: int, new: int) -> Grid | None:
    if not any(c == old for row in g for c in row):
        return None
    return [[new if c == old else c for c in row] for row in g]


def _invert_colors(g: Grid) -> Grid | None:
    colors = sorted({c for row in g for c in row})
    if len(colors) != 2:
        return None
    a, b = colors
    return [[b if c == a else a for c in row] for row in g]


def _most_common_color(g: Grid) -> int:
    from collections import Counter

    cnt = Counter(c for row in g for c in row)
    return cnt.most_common(1)[0][0] if cnt else 0


def _remove_bg(g: Grid) -> Grid | None:
    bg = _most_common_color(g)
    ng = [[0 if c == bg else c for c in row] for row in g]
    return ng if ng != g else None


def _fill_holes(g: Grid) -> Grid | None:
    if not g or not g[0]:
        return None
    rows, cols = len(g), len(g[0])
    result = [r[:] for r in g]
    changed = False
    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            if result[r][c] != 0:
                continue
            nbrs = {result[r - 1][c], result[r + 1][c], result[r][c - 1], result[r][c + 1]}
            nbrs.discard(0)
            if len(nbrs) == 1:
                result[r][c] = nbrs.pop()
                changed = True
    return result if changed else None


def _mirror_h(g: Grid) -> Grid | None:
    if not g or not g[0]:
        return None
    rows, cols = len(g), len(g[0])
    if cols % 2 != 0:
        return None
    half = cols // 2
    result = []
    for r in range(rows):
        left = g[r][:half]
        right = g[r][half:]
        if left != right[::-1]:
            result.append(left + left[::-1])
        else:
            result.append(g[r])
    return result if result != g else None


def _mirror_v(g: Grid) -> Grid | None:
    if not g:
        return None
    rows = len(g)
    if rows % 2 != 0:
        return None
    half = rows // 2
    top = g[:half]
    bottom = g[half:]
    if top == [row[::-1] for row in bottom[::-1]]:
        return None
    return top + [row[::-1] for row in top[::-1]]


def _gravity_down(g: Grid) -> Grid | None:
    if not g or not g[0]:
        return None
    rows, cols = len(g), len(g[0])
    result = [[0] * cols for _ in range(rows)]
    changed = False
    for c in range(cols):
        col = [g[r][c] for r in range(rows) if g[r][c] != 0]
        if col:
            for r in range(rows - len(col), rows):
                result[r][c] = col[r - (rows - len(col))]
            if any(result[r][c] != g[r][c] for r in range(rows)):
                changed = True
    return result if changed else None


def _gravity_up(g: Grid) -> Grid | None:
    if not g or not g[0]:
        return None
    rows, cols = len(g), len(g[0])
    result = [[0] * cols for _ in range(rows)]
    changed = False
    for c in range(cols):
        col = [g[r][c] for r in range(rows) if g[r][c] != 0]
        if col:
            for r in range(len(col)):
                result[r][c] = col[r]
            if any(result[r][c] != g[r][c] for r in range(rows)):
                changed = True
    return result if changed else None


def _extend_down(g: Grid) -> Grid | None:
    """Double height by appending a vertically-mirrored copy below."""
    if not g:
        return None
    result = g + [r[:] for r in reversed(g)]
    return result if len(result) <= 30 else None


def _extend_right(g: Grid) -> Grid | None:
    """Double width by appending a horizontally-mirrored copy to the right."""
    if not g or not g[0]:
        return None
    result = [r + r[::-1] for r in g]
    return result if all(len(r) <= 30 for r in result) else None


def _crop_to_object(g: Grid) -> Grid | None:
    """Crop to the bounding box of the first non-background connected component."""
    if not g or not g[0]:
        return None
    rows, cols = len(g), len(g[0])
    # Find background (most common color)
    from collections import Counter

    counts: Counter[int] = Counter(g[r][c] for r in range(rows) for c in range(cols))
    bg = counts.most_common(1)[0][0]
    # BFS to find connected components of non-background colors
    visited = [[False] * cols for _ in range(rows)]
    for sr in range(rows):
        for sc in range(cols):
            if g[sr][sc] == bg or visited[sr][sc]:
                continue
            # BFS
            queue = [(sr, sc)]
            component: list[tuple[int, int]] = []
            visited[sr][sc] = True
            while queue:
                r, c = queue.pop()
                component.append((r, c))
                for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                    if (
                        0 <= nr < rows
                        and 0 <= nc < cols
                        and not visited[nr][nc]
                        and g[nr][nc] != bg
                    ):
                        visited[nr][nc] = True
                        queue.append((nr, nc))
            min_r = min(r for r, c in component)
            max_r = max(r for r, c in component)
            min_c = min(c for r, c in component)
            max_c = max(c for r, c in component)
            cropped = [g[r][min_c : max_c + 1] for r in range(min_r, max_r + 1)]
            if len(cropped) != rows or len(cropped[0]) != cols:
                return cropped
    return None


def _fill_with_modal(g: Grid) -> Grid | None:
    """Fill every cell with the most-common color in the grid."""
    if not g or not g[0]:
        return None
    from collections import Counter

    modal = Counter(c for row in g for c in row).most_common(1)[0][0]
    out = [[modal] * len(row) for row in g]
    return out if out != g else None


def _shift_down_1(g: Grid) -> Grid | None:
    """Shift every row down by one; top row becomes all zeros."""
    if not g or not g[0]:
        return None
    h, w = len(g), len(g[0])
    out = [[0] * w] + [g[r][:] for r in range(h - 1)]
    return out if out != g else None


def _grid_lines(g: Grid) -> Grid | None:
    """Fill every cell at an even row OR even column with 1, rest 0.

    Produces the 'grid lines' checkerboard that many ARC-2 tasks require when
    the input is an all-zero grid of a given size.
    """
    if not g or not g[0]:
        return None
    h, w = len(g), len(g[0])
    out = [[1 if (r % 2 == 0 or c % 2 == 0) else 0 for c in range(w)] for r in range(h)]
    return out if out != g else None


def _border_fill(g: Grid) -> Grid | None:
    """Fill the outer border with the single unique non-zero color; zero the interior.

    Matches tasks where a seed cell (any position) causes the grid border to be
    drawn with that color and everything else zeroed out.
    """
    if not g or not g[0]:
        return None
    h, w = len(g), len(g[0])

    nz = [c for row in g for c in row if c != 0]
    if not nz:
        return None
    colors = set(nz)
    if len(colors) != 1:
        return None
    color = colors.pop()
    out = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            if r == 0 or r == h - 1 or c == 0 or c == w - 1:
                out[r][c] = color
    return out if out != g else None


def _deduplicate_cols(g: Grid) -> Grid | None:
    """Remove duplicate columns, keeping first occurrence of each unique column pattern."""
    if not g or not g[0]:
        return None
    seen: list[tuple[int, ...]] = []
    kept: list[int] = []
    for c in range(len(g[0])):
        col = tuple(g[r][c] for r in range(len(g)))
        if col not in seen:
            seen.append(col)
            kept.append(c)
    if len(kept) == len(g[0]):
        return None
    return [[g[r][c] for c in kept] for r in range(len(g))]


def _color_objects_by_size(g: Grid) -> Grid | None:
    """Recolor each connected component by its size rank (largest → color 1).

    All non-background components share the same background color in the input.
    Rank 0 (largest component) → color 1, rank 1 → color 2, etc.
    Background cells stay at background color.
    """
    if not g or not g[0]:
        return None
    from collections import Counter

    rows, cols = len(g), len(g[0])
    counts: Counter[int] = Counter(g[r][c] for r in range(rows) for c in range(cols))
    bg = counts.most_common(1)[0][0]
    visited = [[False] * cols for _ in range(rows)]
    components: list[list[tuple[int, int]]] = []
    for sr in range(rows):
        for sc in range(cols):
            if g[sr][sc] == bg or visited[sr][sc]:
                continue
            queue = [(sr, sc)]
            component: list[tuple[int, int]] = []
            visited[sr][sc] = True
            while queue:
                r, c = queue.pop()
                component.append((r, c))
                for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                    if (
                        0 <= nr < rows
                        and 0 <= nc < cols
                        and not visited[nr][nc]
                        and g[nr][nc] != bg
                    ):
                        visited[nr][nc] = True
                        queue.append((nr, nc))
            components.append(component)
    if len(components) < 2:
        return None
    components.sort(key=len, reverse=True)
    result = [[bg] * cols for _ in range(rows)]
    for rank, comp in enumerate(components):
        color = rank + 1  # 1-indexed, largest gets 1
        for r, c in comp:
            result[r][c] = color
    return result if result != g else None


def _extract_largest_object(g: Grid) -> Grid | None:
    """BFS-crop to the bounding box of the LARGEST non-background connected component.

    Unlike _crop_to_object (which returns the first/any component), this returns
    the largest by cell count — needed when multiple objects exist and the task
    selects the biggest.
    """
    if not g or not g[0]:
        return None
    from collections import Counter

    rows, cols = len(g), len(g[0])
    counts: Counter[int] = Counter(g[r][c] for r in range(rows) for c in range(cols))
    bg = counts.most_common(1)[0][0]
    visited = [[False] * cols for _ in range(rows)]
    best_component: list[tuple[int, int]] = []
    for sr in range(rows):
        for sc in range(cols):
            if g[sr][sc] == bg or visited[sr][sc]:
                continue
            queue = [(sr, sc)]
            component: list[tuple[int, int]] = []
            visited[sr][sc] = True
            while queue:
                r, c = queue.pop()
                component.append((r, c))
                for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                    if (
                        0 <= nr < rows
                        and 0 <= nc < cols
                        and not visited[nr][nc]
                        and g[nr][nc] != bg
                    ):
                        visited[nr][nc] = True
                        queue.append((nr, nc))
            if len(component) > len(best_component):
                best_component = component
    if not best_component:
        return None
    min_r = min(r for r, _ in best_component)
    max_r = max(r for r, _ in best_component)
    min_c = min(c for _, c in best_component)
    max_c = max(c for _, c in best_component)
    cropped = [g[r][min_c : max_c + 1] for r in range(min_r, max_r + 1)]
    if len(cropped) == rows and len(cropped[0]) == cols:
        return None
    return cropped


def _kronecker_minority(g: Grid) -> Grid | None:
    """Kronecker tile triggered by the least-common non-zero color.

    Places a copy of g at each block (i, j) where input[i][j] equals the
    rarest non-zero color.  Complement of _kronecker_modal (which uses the
    most common color as trigger).
    """
    from collections import Counter

    if not g or not g[0]:
        return None
    counts: Counter[int] = Counter(
        g[r][c] for r in range(len(g)) for c in range(len(g[0])) if g[r][c] != 0
    )
    if not counts:
        return None
    minority = counts.most_common()[-1][0]
    h, w = len(g), len(g[0])
    if h * h > 30 or w * w > 30:
        return None
    out = [[0] * (w * w) for _ in range(h * h)]
    for i in range(h):
        for j in range(w):
            if g[i][j] == minority:
                for di in range(h):
                    for dj in range(w):
                        out[i * h + di][j * w + dj] = g[di][dj]
    return out if any(out[r][c] != 0 for r in range(h * h) for c in range(w * w)) else None


def _make_kronecker_color(trigger: int) -> Program:
    """Return a Kronecker-tile function using a specific trigger color."""

    def fn(g: Grid) -> Grid | None:
        if not g or not g[0]:
            return None
        h, w = len(g), len(g[0])
        if h * h > 30 or w * w > 30:
            return None
        if not any(g[r][c] == trigger for r in range(h) for c in range(w)):
            return None
        out = [[0] * (w * w) for _ in range(h * h)]
        for i in range(h):
            for j in range(w):
                if g[i][j] == trigger:
                    for di in range(h):
                        for dj in range(w):
                            out[i * h + di][j * w + dj] = g[di][dj]
        return out if any(out[r][c] != 0 for r in range(h * h) for c in range(w * w)) else None

    return fn


def _find_kronecker_trigger(train: list[dict[str, Grid]]) -> int | None:
    """Find which color, when used as Kronecker trigger, explains all training pairs."""
    if not train:
        return None
    first_in = train[0]["input"]
    candidates = sorted(
        {first_in[r][c] for r in range(len(first_in)) for c in range(len(first_in[0]))}
    )
    for color in candidates:
        fn = _make_kronecker_color(color)
        if all(fn(ex["input"]) == ex["output"] for ex in train):
            return color
    return None


def _make_kronecker_learned(train: list[dict[str, Grid]]) -> Program:
    """Kronecker tile with trigger color learned from training examples."""
    trigger = _find_kronecker_trigger(train)
    if trigger is None:
        return lambda g: None  # type: ignore[return-value]
    return _make_kronecker_color(trigger)


def _make_kronecker_template(
    transform_fn: Callable[[Grid], Grid], train: list[dict[str, Grid]]
) -> Program:
    """Kronecker tile: at each trigger position place transform_fn(g) instead of g.

    Trigger color is learned from training data.  Handles tasks where the placed
    pattern is a rotation or flip of the template rather than the template itself.
    """
    trigger = _find_kronecker_trigger(train)

    def fn(g: Grid) -> Grid | None:
        if not g or not g[0]:
            return None
        t = trigger
        if t is None:
            # Fall back: try non-zero trigger
            t_val = None
            h0, w0 = len(g), len(g[0])
            for r in range(h0):
                for c in range(w0):
                    if g[r][c] != 0:
                        t_val = g[r][c]
                        break
                if t_val is not None:
                    break
            if t_val is None:
                return None
            t = t_val
        tpl = transform_fn(g)
        if not tpl or not tpl[0]:
            return None
        h, w = len(g), len(g[0])
        th, tw = len(tpl), len(tpl[0])
        if h * th > 30 or w * tw > 30:
            return None
        out = [[0] * (w * tw) for _ in range(h * th)]
        for i in range(h):
            for j in range(w):
                if g[i][j] == t:
                    for di in range(th):
                        for dj in range(tw):
                            out[i * th + di][j * tw + dj] = tpl[di][dj]
        return out if any(out[r][c] != 0 for r in range(h * th) for c in range(w * tw)) else None

    return fn


def _mark_nz_neighbors_ul(g: Grid) -> Grid | None:
    """Mark the toroidal UP-LEFT neighbor of each non-zero cell with color 2.

    For each non-zero cell at (r, c), the cell at ((r-1)%h, (c-1)%w) is set
    to 2 if it is currently 0.  Enables compound ops like mark_nz_ul + tile_3.
    """
    if not g or not g[0]:
        return None
    h, w = len(g), len(g[0])
    result = [row[:] for row in g]
    changed = False
    for r in range(h):
        for c in range(w):
            if g[r][c] != 0:
                nr, nc = (r - 1) % h, (c - 1) % w
                if result[nr][nc] == 0:
                    result[nr][nc] = 2
                    changed = True
    return result if changed else None


def _kronecker_modal(g: Grid) -> Grid | None:
    """Kronecker tile triggered by the most-common color: blocks placed only at those positions.

    For each cell where input[i][j] equals the most frequent color, place a copy
    of the full input at block (i, j); other block positions stay zero.
    Unlike plain kronecker (triggered by non-zero), this respects the dominant
    color as the 'active' cell.
    """
    from collections import Counter

    if not g or not g[0]:
        return None
    counts: Counter[int] = Counter(g[r][c] for r in range(len(g)) for c in range(len(g[0])))
    modal = counts.most_common(1)[0][0]
    h, w = len(g), len(g[0])
    if h * h > 30 or w * w > 30:
        return None
    out = [[0] * (w * w) for _ in range(h * h)]
    for i in range(h):
        for j in range(w):
            if g[i][j] == modal:
                for di in range(h):
                    for dj in range(w):
                        out[i * h + di][j * w + dj] = g[di][dj]
    return out if any(out[r][c] != 0 for r in range(h * h) for c in range(w * w)) else None


def _kronecker_invert(g: Grid) -> Grid | None:
    """Fractal tile: non-zero cells place the COLOR-INVERTED grid; zero cells → zeros.

    Variant of _kronecker_tile where the placed template is invert_colors(g)
    instead of g itself.  Handles tasks where each activating cell produces
    the complement pattern rather than a copy of the original.
    """
    inv = _invert_colors(g)
    if inv is None:
        return None
    h, w = len(g), len(g[0])
    if h * h > 30 or w * w > 30:
        return None
    out = [[0] * (w * w) for _ in range(h * h)]
    for i in range(h):
        for j in range(w):
            if g[i][j] != 0:
                for di in range(h):
                    for dj in range(w):
                        out[i * h + di][j * w + dj] = inv[di][dj]
    return out if any(out[r][c] != 0 for r in range(h * h) for c in range(w * w)) else None


def _kronecker_color_mask(g: Grid) -> Grid | None:
    """Kronecker product where block (i,j) shows ONLY cells matching color g[i][j].

    At each meta-cell (i,j), place a masked copy of g where every cell whose
    value differs from g[i][j] is set to 0.  Background (0) meta-cells are
    skipped.  Handles ARC tasks where each pixel 'reveals' only the cells of
    its own color in the scaled output.
    """
    if not g or not g[0]:
        return None
    h, w = len(g), len(g[0])
    if h * h > 30 or w * w > 30:
        return None
    out = [[0] * (w * w) for _ in range(h * h)]
    placed = False
    for i in range(h):
        for j in range(w):
            c = g[i][j]
            if c == 0:
                continue
            for di in range(h):
                for dj in range(w):
                    if g[di][dj] == c:
                        out[i * h + di][j * w + dj] = c
                        placed = True
    return out if placed else None


def _tile_parity_transforms(g: Grid) -> Grid | None:
    """Kronecker product where the template at block (i,j) depends on (i%2, j%2).

    Uses the Klein four-group of reflections:
        (0,0) → rot180    (0,1) → flip_h
        (1,0) → flip_v    (1,1) → identity
    Handles ARC tasks whose output is a checkerboard of rotated/reflected copies
    of the input, with the transformation determined by the block's row/column parity.
    """
    if not g or not g[0]:
        return None
    h, w = len(g), len(g[0])
    if h * h > 30 or w * w > 30:
        return None
    templates = {
        (0, 0): _rot180(g),
        (0, 1): _flip_h(g),
        (1, 0): _flip_v(g),
        (1, 1): [r[:] for r in g],
    }
    out = [[0] * (w * w) for _ in range(h * h)]
    for i in range(h):
        for j in range(w):
            tpl = templates[(i % 2, j % 2)]
            for di in range(h):
                for dj in range(w):
                    out[i * h + di][j * w + dj] = tpl[di][dj]
    return out


def _tile_4_rect(g: Grid) -> Grid | None:
    """Tile 2x horizontally then 2x vertically, producing a 2x2 grid of copies.

    Equivalent to tile_2h followed by tile_2v.  Exposed as a single op so
    the DFS can find 2-op chains like invert + tile_4_rect that would otherwise
    require 3 hops (invert + tile_2h + tile_2v).
    """
    r = _tile_2_horiz(g)
    if r is None:
        return None
    return _tile_2_vert(r)


def _tile_4_rotations(g: Grid) -> Grid | None:
    """4-quadrant tile: place the 4 rotations of g at [TL|TR; BL|BR].

    Only valid for square inputs.  Layout:
        identity(g)   | CW_rot90(g)
        CCW_rot90(g)  | rot180(g)
    CW rot90 = flip_v(transpose(g)).  CCW rot90 = flip_h(transpose(g)).
    """
    if not g or not g[0]:
        return None
    h, w = len(g), len(g[0])
    if h != w:
        return None
    if h * 2 > 30:
        return None
    t = _transpose(g)
    cw = _flip_v(t)
    ccw = _flip_h(t)
    r180 = _rot180(g)
    top = [g[r] + cw[r] for r in range(h)]
    bot = [ccw[r] + r180[r] for r in range(h)]
    return top + bot


def _tile_3_alt_flip(g: Grid) -> Grid | None:
    """Tile 3x: even repetitions normal, odd repetitions flip each row horizontally.

    Produces alternating normal/flipped tiling: rows 0..h-1 normal, rows h..2h-1
    horizontally-reversed, rows 2h..3h-1 normal again.
    """
    if not g or not g[0]:
        return None
    h, w = len(g), len(g[0])
    if h * 3 > 30 or w * 3 > 30:
        return None
    result = []
    for rep in range(3):
        for row in g:
            result.append(row * 3 if rep % 2 == 0 else row[::-1] * 3)
    return result


def _outline_object(g: Grid) -> Grid | None:
    """Extract perimeter of non-zero regions: keep only non-zero cells that touch a 0 neighbor.

    Distinct from arc_solver's `border` (which copies outermost grid rows/cols).
    This extracts the OBJECT outline — interior non-zero cells become 0.
    """
    if not g or not g[0]:
        return None
    h, w = len(g), len(g[0])
    result = [[0] * w for _ in range(h)]
    changed = False
    for r in range(h):
        for c in range(w):
            if g[r][c] != 0 and any(
                nr < 0 or nr >= h or nc < 0 or nc >= w or g[nr][nc] == 0
                for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
            ):
                result[r][c] = g[r][c]
                changed = True
    return result if changed and result != g else None


def _extend_left(g: Grid) -> Grid | None:
    """Double width by prepending a horizontally-mirrored copy to the LEFT of each row.

    Complement of _extend_right: _extend_right produces row + reversed(row),
    _extend_left produces reversed(row) + row.
    """
    if not g or not g[0]:
        return None
    if len(g[0]) * 2 > 30:
        return None
    result = [r[::-1] + r for r in g]
    return result if result != g else None


def _extend_both(g: Grid) -> Grid | None:
    """2x scale in both axes: palindrome-extend right, then palindrome-extend down.

    Equivalent to extend_right followed by extend_down, but exposed as a single op
    so the PatternExtractor can find the common 4-quadrant mirror pattern
    (identity | flip_v; flip_h | rot180) without needing a 2-step chain.
    """
    r = _extend_right(g)
    if r is None:
        return None
    return _extend_down(r)


def _tile_3(g: Grid) -> Grid | None:
    """Tile the grid 3 times in both directions (3x3 repetition)."""
    if not g or not g[0]:
        return None
    h, w = len(g), len(g[0])
    if h * 3 > 30 or w * 3 > 30:
        return None
    result = []
    for _ in range(3):
        for row in g:
            result.append(row * 3)
    return result


def _tile_2_horiz(g: Grid) -> Grid | None:
    """Tile the grid twice horizontally (1x2 repetition)."""
    if not g or not g[0]:
        return None
    if len(g[0]) * 2 > 30:
        return None
    result = [row * 2 for row in g]
    return result if result != g else None


def _tile_2_vert(g: Grid) -> Grid | None:
    """Tile the grid twice vertically (2x1 repetition)."""
    if not g:
        return None
    if len(g) * 2 > 30:
        return None
    result = list(g) + [row[:] for row in g]
    return result if result != g else None


def _kronecker_tile(g: Grid) -> Grid | None:
    """Fractal self-tile: replace each non-zero cell with the full input; zero cells → zeros.

    Output shape is (h*h, w*w). Handles the ARC pattern where each pixel either
    'activates' (shows the whole grid) or stays blank.
    """
    if not g or not g[0]:
        return None
    h, w = len(g), len(g[0])
    if h * h > 30 or w * w > 30:
        return None
    out = [[0] * (w * w) for _ in range(h * h)]
    for i in range(h):
        for j in range(w):
            if g[i][j] != 0:
                for di in range(h):
                    for dj in range(w):
                        out[i * h + di][j * w + dj] = g[di][dj]
    return out if any(out[r][c] != 0 for r in range(h * h) for c in range(w * w)) else None


def _count_nonzero_to_row(g: Grid) -> Grid | None:
    """Count non-zero cells; output a 1xN row where N=count and all cells = that color.

    Handles single-color tasks like: 5 cells of color 4 → [[4,4,4,4,4]].
    Background is always 0 per ARC convention.
    """
    fg_cells = [g[r][c] for r in range(len(g)) for c in range(len(g[r])) if g[r][c] != 0]
    if not fg_cells:
        return None
    if len(set(fg_cells)) != 1:
        return None  # multiple colors
    color = fg_cells[0]
    n = len(fg_cells)
    if n > 30:
        return None
    return [[color] * n]


# Parametric color-map wrapper


def _color_map(g: Grid, train: list[dict[str, Grid]]) -> Grid | None:
    """Learn a color mapping from input->output statistics across all train pairs."""
    mapping: dict[int, int] = {}
    counts: dict[tuple[int, int], int] = {}
    for ex in train:
        inp, out = ex["input"], ex["output"]
        if len(inp) != len(out) or any(
            len(ir) != len(or_) for ir, or_ in zip(inp, out, strict=False)
        ):
            return None
        for r in range(len(inp)):
            for c in range(len(inp[0])):
                pair = (inp[r][c], out[r][c])
                counts[pair] = counts.get(pair, 0) + 1

    # Build deterministic mapping: pick most common output per input
    for (ic, oc), cnt in counts.items():
        if ic not in mapping or counts.get((ic, mapping[ic]), 0) < cnt:
            mapping[ic] = oc

    if not mapping or mapping == {k: k for k in mapping}:
        return None
    return [[mapping.get(cell, cell) for cell in row] for row in g]


# Parametric wrappers
def _make_replace(old: int, new: int):
    def fn(g: Grid) -> Grid | None:
        return _replace_color(g, old, new)

    return fn


def _make_color_map(train: list[dict[str, Grid]]):
    def fn(g: Grid) -> Grid | None:
        return _color_map(g, train)

    return fn


def _make_upsample(n: int):
    def fn(g: Grid) -> Grid | None:
        if not g:
            return None
        rows, cols = len(g), len(g[0]) if g else 0
        if rows * n > 30 or cols * n > 30:
            return None
        result = []
        for r in range(rows):
            new_row = []
            for c in range(cols):
                new_row.extend([g[r][c]] * n)
            for _ in range(n):
                result.append(new_row)
        return result

    return fn


def _make_downsample(n: int):
    def fn(g: Grid) -> Grid | None:
        if not g:
            return None
        rows, cols = len(g), len(g[0]) if g else 0
        if rows % n != 0 or cols % n != 0:
            return None
        return [[g[r][c] for c in range(0, cols, n)] for r in range(0, rows, n)]

    return fn


# ---------------------------------------------------------------------------
# Strategy builders
# ---------------------------------------------------------------------------


def _build_strategy(name: str, train: list[dict[str, Grid]]) -> list[tuple[str, Program]]:
    """Return a focused list of primitives for a named strategy."""
    base: list[tuple[str, Program]] = [
        ("identity", _identity),
        ("flip_h", _flip_h),
        ("flip_v", _flip_v),
        ("transpose", _transpose),
        ("rot90", _rot90),
        ("rot180", _rot180),
    ]

    color: list[tuple[str, Program]] = (
        base
        + [
            ("invert", _invert_colors),
            ("remove_bg", _remove_bg),
            ("fill_holes", _fill_holes),
            ("tile_4rect", _tile_4_rect),  # expose so invert+tile_4rect is 2-op
        ]
        + [
            (f"replace_{old}_{new}", _make_replace(old, new))
            for old in range(10)
            for new in range(10)
            if old != new
        ]
    )

    geo = [
        *base,
        ("grid_lines", _grid_lines),
        ("fill_modal", _fill_with_modal),
        ("mirror_h", _mirror_h),
        ("mirror_v", _mirror_v),
        ("extend_down", _extend_down),
        ("extend_right", _extend_right),
        ("extend_left", _extend_left),
        ("extend_both", _extend_both),
        ("tile_2h", _tile_2_horiz),
        ("tile_2v", _tile_2_vert),
        ("tile_4rect", _tile_4_rect),
        ("tile_4rot", _tile_4_rotations),
        ("tile_3", _tile_3),
        ("tile_3_altflip", _tile_3_alt_flip),
        ("kronecker", _kronecker_tile),
        ("kronecker_inv", _kronecker_invert),
        ("kronecker_modal", _kronecker_modal),
        ("kronecker_minority", _kronecker_minority),
        ("kronecker_color_mask", _kronecker_color_mask),
        ("tile_parity", _tile_parity_transforms),
        ("kronecker_learned", _make_kronecker_learned(train)),
        ("kronecker_rot90", _make_kronecker_template(_rot90, train)),
        ("kronecker_rot180", _make_kronecker_template(_rot180, train)),
        ("kronecker_flip_h", _make_kronecker_template(_flip_h, train)),
        ("kronecker_flip_v", _make_kronecker_template(_flip_v, train)),
        ("mark_nz_ul", _mark_nz_neighbors_ul),
    ]

    obj = [
        *base,
        ("fill_holes", _fill_holes),
        ("remove_bg", _remove_bg),
        ("fill_modal", _fill_with_modal),
        ("border_fill", _border_fill),
        ("shift_d1", _shift_down_1),
        ("gravity_d", _gravity_down),
        ("gravity_u", _gravity_up),
        ("crop_obj", _crop_to_object),
        ("crop_largest", _extract_largest_object),
        ("color_by_size", _color_objects_by_size),
        ("dedup_cols", _deduplicate_cols),
        ("count_row", _count_nonzero_to_row),
        ("outline", _outline_object),
    ]

    scale = [
        ("identity", _identity),
        *_make_parametric_scale(),
    ]

    cm = [*base, ("color_map", _make_color_map(train))]

    # Shape-aware strategy: only ops that keep size (no expand/shrink)
    transform = [
        *base,
        ("invert", _invert_colors),
        ("remove_bg", _remove_bg),
        ("fill_holes", _fill_holes),
        ("fill_modal", _fill_with_modal),
        ("border_fill", _border_fill),
        ("shift_d1", _shift_down_1),
        ("grid_lines", _grid_lines),
        ("gravity_d", _gravity_down),
        ("gravity_u", _gravity_up),
        ("mirror_h", _mirror_h),
        ("mirror_v", _mirror_v),
        ("color_map", _make_color_map(train)),
    ] + [
        (f"replace_{old}_{new}", _make_replace(old, new))
        for old in range(10)
        for new in range(10)
        if old != new
    ]

    return {
        "color": color,
        "geo": geo,
        "obj": obj,
        "scale": scale,
        "color_map": cm,
        "transform": transform,
        "all": [*color, *geo, *obj, *scale, *cm],
    }.get(name, base)


def _make_parametric_scale() -> list[tuple[str, Program]]:
    out: list[tuple[str, Program]] = []
    for n in (2, 3):
        out.append((f"upsample{n}", _make_upsample(n)))
        out.append((f"downsample{n}", _make_downsample(n)))
    return out


# ---------------------------------------------------------------------------
# Pattern Extractor
# ---------------------------------------------------------------------------


class PatternExtractor:
    """
    Extract ``CompoundRule`` objects from an ARC task using compound
    engineering consensus across multiple search strategies.

    Parameters
    ----------
    max_depth : int
        Maximum length of operation chain to test (default 3).
    budget_per_strategy : int
        Candidate program evaluations per strategy (default 800).
    consensus_threshold : int
        Minimum number of strategies that must agree on a rule for it to be
        emitted (default 1 — set >1 for strict consensus).
    codec : ARCCodec | None
        Optional encoder/decoder for latent-delta computation.
    """

    def __init__(
        self,
        max_depth: int = 3,
        budget_per_strategy: int = 800,
        consensus_threshold: int = 1,
        codec: ARCCodec | None = None,
    ) -> None:
        self.max_depth = max_depth
        self.budget = budget_per_strategy
        self.consensus_threshold = consensus_threshold
        self.codec = codec or ARCCodec()
        self._counter: list[int] = [0]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def extract(self, task: dict[str, Any]) -> list[CompoundRule]:
        """
        Extract all ``CompoundRule``<s> that explain the training examples.

        Returns a list sorted by descending confidence.
        """
        train: list[dict[str, Grid]] = task.get("train", [])
        if not train:
            return []

        # Shape-aware strategy selection: add specialised strategy first
        def _output_scale(examples: list[dict[str, Grid]]) -> str:
            """Determine dominant scale relationship from training examples."""
            h_in = len(examples[0]["input"])
            h_out = len(examples[0]["output"])
            w_in = len(examples[0]["input"][0]) if examples[0]["input"] else 1
            w_out = len(examples[0]["output"][0]) if examples[0]["output"] else 1
            if h_in == h_out and w_in == w_out:
                return "same"
            if h_out >= h_in and w_out >= w_in:
                return "up"
            return "down"

        scale_hint = _output_scale(train)
        if scale_hint == "same":
            strategies = ["transform", "color", "obj", "color_map", "geo", "all"]
        elif scale_hint == "up":
            strategies = ["geo", "scale", "color", "color_map", "all"]
        else:
            strategies = ["obj", "scale", "color", "color_map", "all"]
        vote_map: dict[tuple[str, ...], list[str]] = {}
        coverage_map: dict[tuple[str, ...], float] = {}
        hiho_map: dict[tuple[str, ...], float] = {}
        latent_map: dict[tuple[str, ...], list[float]] = {}

        for strat_name in strategies:
            ops = _build_strategy(strat_name, train)
            program = self._search(train, ops)
            if program is None:
                continue
            op_names = tuple(name for name, _ in program)
            vote_map.setdefault(op_names, []).append(strat_name)

            # Coverage
            coverage = self._coverage(train, program)
            coverage_map[op_names] = max(coverage_map.get(op_names, 0.0), coverage)

            # HIHO coherence (geometric validity of the transformation)
            hiho = self._compute_hiho(train, program)
            hiho_map[op_names] = max(hiho_map.get(op_names, 0.0), hiho)

            # Latent delta (FLUME 256-D analogy)
            latent = self._compute_latent_delta(train, program)
            latent_map[op_names] = latent  # overwrite with latest — deterministic per strat

        results: list[CompoundRule] = []
        for op_names, voters in vote_map.items():
            if len(voters) < self.consensus_threshold:
                continue
            sig = hashlib.sha256("->".join(op_names).encode()).hexdigest()[:16]
            results.append(
                CompoundRule(
                    name=" + ".join(op_names),
                    ops=op_names,
                    confidence=min(1.0, 0.5 + 0.1 * len(voters) + 0.3 * coverage_map[op_names]),
                    train_coverage=coverage_map[op_names],
                    strategy_votes=len(voters),
                    hiho_score=hiho_map.get(op_names, 0.5),
                    latent_delta=tuple(latent_map.get(op_names, [0.0] * 12)),
                    signature=sig,
                )
            )

        results.sort(key=lambda r: (r.confidence, r.strategy_votes, r.hiho_score), reverse=True)
        return results

    # ------------------------------------------------------------------
    # Search core
    # ------------------------------------------------------------------
    def _search(
        self, train: list[dict[str, Grid]], ops: list[tuple[str, Program]]
    ) -> list[tuple[str, Program]] | None:
        self._counter[0] = 0
        for depth in range(1, self.max_depth + 1):
            result = self._dfs(train, depth, ops)
            if result is not None:
                return result
        return None

    def _dfs(
        self,
        train: list[dict[str, Grid]],
        depth: int,
        ops: list[tuple[str, Program]],
    ) -> list[tuple[str, Program]] | None:
        if depth == 1:
            for name, op in ops:
                self._counter[0] += 1
                if self._counter[0] > self.budget:
                    return None
                if all(
                    (r := op(deepcopy(ex["input"]))) is not None and grids_equal(r, ex["output"])
                    for ex in train
                ):
                    return [(name, op)]
            return None

        for name, op in ops:
            transformed = []
            valid = True
            for ex in train:
                t = op(deepcopy(ex["input"]))
                if t is None:
                    valid = False
                    break
                transformed.append({"input": t, "output": ex["output"]})
            if not valid:
                continue
            sub = self._dfs(transformed, depth - 1, ops)
            if sub is not None:
                return [(name, op), *sub]
        return None

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------
    def _coverage(self, train: list[dict[str, Grid]], program: list[tuple[str, Program]]) -> float:
        """Fraction of train examples perfectly transformed by ``program``."""
        if not train:
            return 0.0
        matched = 0
        for ex in train:
            g = deepcopy(ex["input"])
            for _, op in program:
                g = op(g)
                if g is None:
                    break
            if g is not None and grids_equal(g, ex["output"]):
                matched += 1
        return matched / len(train)

    def _compute_hiho(
        self, train: list[dict[str, Grid]], program: list[tuple[str, Program]]
    ) -> float:
        """Average HIHO coherence over transformed outputs."""
        try:
            import numpy as np
        except Exception:
            return 0.5
        hihos = []
        for ex in train:
            g = deepcopy(ex["input"])
            for _, op in program:
                g = op(g)
                if g is None:
                    break
            if g is not None:
                enc = self.codec.encode(g)
                hihos.append(enc.get("hiho", 0.5))
        return float(np.mean(hihos)) if hihos else 0.5

    def _compute_latent_delta(
        self, train: list[dict[str, Grid]], program: list[tuple[str, Program]]
    ) -> list[float]:
        """Mean latent_12 delta between input and output across train examples."""
        try:
            import numpy as np
        except Exception:
            return [0.0] * 12
        deltas = []
        for ex in train:
            g = deepcopy(ex["input"])
            for _, op in program:
                g = op(g)
                if g is None:
                    break
            if g is not None:
                enc_in = self.codec.encode(ex["input"])
                enc_out = self.codec.encode(g)
                if enc_in.get("latent_12") is not None and enc_out.get("latent_12") is not None:
                    deltas.append(np.array(enc_out["latent_12"]) - np.array(enc_in["latent_12"]))
        if not deltas:
            return [0.0] * 12
        mean = np.mean(deltas, axis=0)
        return [round(float(v), 6) for v in mean.tolist()]

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def save_rules(self, rules: list[CompoundRule], path: str | Path) -> None:
        Path(path).write_text(json.dumps([r.to_dict() for r in rules], indent=2))

    def load_rules(self, path: str | Path) -> list[CompoundRule]:
        data = json.loads(Path(path).read_text())
        return [CompoundRule.from_dict(d) for d in data]


# ---------------------------------------------------------------------------
# CLI sanity check
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Simple synthetic task: invert colors
    task = {
        "train": [
            {"input": [[0, 1, 0], [1, 0, 1]], "output": [[1, 0, 1], [0, 1, 0]]},
            {"input": [[1, 1], [0, 0]], "output": [[0, 0], [1, 1]]},
        ],
        "test": [{"input": [[0, 0, 1], [1, 0, 0]], "output": [[0, 0, 0]]}],
    }
    extractor = PatternExtractor(max_depth=1, budget_per_strategy=200)
    rules = extractor.extract(task)
    print(f"Extracted {len(rules)} rule(s)")
    for r in rules:
        hiho = r.hiho_score
        print(f"  {r.name} | conf={r.confidence:.2f} | votes={r.strategy_votes} | hiho={hiho:.3f}")
    # Expect invert to appear with high confidence
    if not any("invert" in r.name for r in rules):
        raise SystemExit("Expected invert rule not found")
    print("PatternExtractor OK")
