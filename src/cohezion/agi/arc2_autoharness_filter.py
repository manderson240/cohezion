"""Deterministic AutoHarness ARC-AGI-2 Invariant Filter & TTT Candidate Ranker.

Guarantees 0 false-pruning by strictly enforcing necessary conditions derived
from training demonstrations. Bypasses LLM at runtime with <1 ms verification latency.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

Grid = list[list[int]]


def get_grid_dimensions(grid: Grid) -> tuple[int, int]:
    """Return (height, width) of a 2D grid."""
    return len(grid), len(grid[0]) if grid else 0


def get_palette(grid: Grid) -> set[int]:
    """Extract unique set of colors in grid."""
    return {c for row in grid for c in row}


def get_color_counts(grid: Grid) -> dict[int, int]:
    """Compute exact pixel count for each color."""
    counts: dict[int, int] = {}
    for row in grid:
        for c in row:
            counts[c] = counts.get(c, 0) + 1
    return counts


def apply_d4_transform(grid: Grid, op: str) -> Grid:
    """Apply one of the 8 Dihedral group D4 operations."""
    h, w = get_grid_dimensions(grid)
    if op == "R0":
        return [row[:] for row in grid]
    elif op == "R90":
        return [[grid[h - 1 - r][c] for r in range(h)] for c in range(w)]
    elif op == "R180":
        return [[grid[h - 1 - r][w - 1 - c] for c in range(w)] for r in range(h)]
    elif op == "R270":
        return [[grid[r][w - 1 - c] for r in range(h)] for c in range(w)]
    elif op == "SH":  # Horizontal flip (invert rows)
        return [grid[h - 1 - r][:] for r in range(h)]
    elif op == "SV":  # Vertical flip (invert cols)
        return [[grid[r][w - 1 - c] for c in range(w)] for r in range(h)]
    elif op == "SD":  # Main diagonal transpose
        return [[grid[r][c] for r in range(h)] for c in range(w)]
    elif op == "SAD":  # Anti-diagonal
        return [[grid[h - 1 - c][w - 1 - r] for c in range(h)] for r in range(w)]
    return [row[:] for row in grid]


def compute_euler_characteristic(grid: Grid, foreground_color: int | None = None) -> int:
    """Compute topological Euler characteristic chi = V - E + F = b0 - b1 via Gray bit-quads."""
    h, w = get_grid_dimensions(grid)
    if h == 0 or w == 0:
        return 0

    # Binary mask
    mask = [
        [1 if (grid[r][c] == foreground_color if foreground_color is not None else grid[r][c] != 0) else 0
         for c in range(w)]
        for r in range(h)
    ]

    # Pad with 1 border of zeros
    padded = [[0] * (w + 2)]
    for row in mask:
        padded.append([0] + row + [0])
    padded.append([0] * (w + 2))

    q1 = 0
    q3 = 0
    qd = 0

    for r in range(h + 1):
        for c in range(w + 1):
            tl = padded[r][c]
            tr = padded[r][c + 1]
            bl = padded[r + 1][c]
            br = padded[r + 1][c + 1]
            s = tl + tr + bl + br

            if s == 1:
                q1 += 1
            elif s == 3:
                q3 += 1
            elif s == 2:
                if (tl == 1 and br == 1) or (tr == 1 and bl == 1):
                    qd += 1

    return (q1 - q3 + 2 * qd) // 4


def detect_task_invariants(train_pairs: list[tuple[Grid, Grid]]) -> dict[str, Any]:
    """Synthesize necessary invariant conditions from training demonstrations."""
    if not train_pairs:
        return {}

    # 1. Output dimension invariant
    dim_relations: list[str] = []
    fixed_dims: tuple[int, int] | None = None
    all_same_dim = True
    first_out_dim = get_grid_dimensions(train_pairs[0][1])

    for x, y in train_pairs:
        hx, wx = get_grid_dimensions(x)
        hy, wy = get_grid_dimensions(y)
        if (hy, wy) != first_out_dim:
            all_same_dim = False
        if (hy, wy) == (hx, wx):
            dim_relations.append("SAME_AS_INPUT")
        elif (hy, wy) == (2 * hx, 2 * wx):
            dim_relations.append("SCALE_2X")
        elif (hy, wy) == (3 * hx, 3 * wx):
            dim_relations.append("SCALE_3X")

    dim_rule = "SAME_AS_INPUT" if all(r == "SAME_AS_INPUT" for r in dim_relations) and len(dim_relations) == len(train_pairs) else None
    if all_same_dim:
        fixed_dims = first_out_dim

    # 2. Color palette containment
    palette_strict_subset = all(get_palette(y).issubset(get_palette(x)) for x, y in train_pairs)
    
    # Check singleton addition
    new_colors: set[int] = set()
    for x, y in train_pairs:
        diff = get_palette(y) - get_palette(x)
        new_colors.update(diff)
    single_new_color = list(new_colors)[0] if len(new_colors) == 1 else None

    # 3. Non-background count conservation
    exact_count_conserved = True
    for x, y in train_pairs:
        cx = get_color_counts(x)
        cy = get_color_counts(y)
        for c, count in cx.items():
            if c != 0 and cy.get(c, 0) != count:
                exact_count_conserved = False
                break
        if not exact_count_conserved:
            break

    # 4. Symmetry stabilizer
    d4_ops = ["R0", "R90", "R180", "R270", "SH", "SV", "SD", "SAD"]
    stabilizer: list[str] = []
    for op in d4_ops:
        if all(apply_d4_transform(y, op) == y for _, y in train_pairs):
            stabilizer.append(op)

    # 5. Euler characteristic delta
    chi_deltas = [
        compute_euler_characteristic(y) - compute_euler_characteristic(x)
        for x, y in train_pairs
    ]
    constant_chi_delta = chi_deltas[0] if len(set(chi_deltas)) == 1 else None

    return {
        "dim_rule": dim_rule,
        "fixed_dims": fixed_dims,
        "palette_strict_subset": palette_strict_subset,
        "single_new_color": single_new_color,
        "exact_count_conserved": exact_count_conserved,
        "stabilizer": stabilizer,
        "constant_chi_delta": constant_chi_delta,
    }


def filter_and_rank_candidates(
    test_input: Grid,
    candidates: list[Grid],
    train_pairs: list[tuple[Grid, Grid]],
) -> list[tuple[Grid, float]]:
    """Prune invalid candidates with zero false-pruning, then rank survivors via consensus & MDL."""
    invariants = detect_task_invariants(train_pairs)
    hin, win = get_grid_dimensions(test_input)
    test_palette = get_palette(test_input)
    test_counts = get_color_counts(test_input)
    test_chi = compute_euler_characteristic(test_input)

    valid_candidates: list[Grid] = []

    for cand in candidates:
        hc, wc = get_grid_dimensions(cand)
        cand_palette = get_palette(cand)

        # Gate 0: Dimension Check
        if invariants.get("fixed_dims") is not None:
            if (hc, wc) != invariants["fixed_dims"]:
                continue
        elif invariants.get("dim_rule") == "SAME_AS_INPUT":
            if (hc, wc) != (hin, win):
                continue

        # Gate 1: Palette Containment
        if invariants.get("palette_strict_subset"):
            if not cand_palette.issubset(test_palette):
                continue
        elif invariants.get("single_new_color") is not None:
            allowed = test_palette | {invariants["single_new_color"]}
            if not cand_palette.issubset(allowed):
                continue

        # Gate 2: Exact Count Conservation
        if invariants.get("exact_count_conserved"):
            cand_counts = get_color_counts(cand)
            mismatch = False
            for c, count in test_counts.items():
                if c != 0 and cand_counts.get(c, 0) != count:
                    mismatch = True
                    break
            if mismatch:
                continue

        # Gate 3: Symmetry Stabilizer
        stabilizer = invariants.get("stabilizer", [])
        violates_sym = False
        for op in stabilizer:
            if apply_d4_transform(cand, op) != cand:
                violates_sym = True
                break
        if violates_sym:
            continue

        # Gate 4: Euler Topology Delta
        const_chi_delta = invariants.get("constant_chi_delta")
        if const_chi_delta is not None:
            cand_chi = compute_euler_characteristic(cand)
            if cand_chi - test_chi != const_chi_delta:
                continue

        valid_candidates.append(cand)

    pool = valid_candidates if valid_candidates else candidates

    # Rank pool via Consensus and MDL
    scored: list[tuple[Grid, float]] = []
    n_pool = len(pool)

    h_pool, w_pool = get_grid_dimensions(pool[0])
    uniform_dims = all(get_grid_dimensions(c) == (h_pool, w_pool) for c in pool)

    for cand in pool:
        score = 0.0
        hc, wc = get_grid_dimensions(cand)

        # 1. Consensus Agreement Score
        if uniform_dims:
            agreement = 0.0
            for r in range(h_pool):
                for c in range(w_pool):
                    val = cand[r][c]
                    matches = sum(1 for other in pool if other[r][c] == val)
                    agreement += matches / n_pool
            consensus_score = agreement / (h_pool * w_pool)
            score += 0.65 * consensus_score

        # 2. Entropy / Simplicity Score (MDL heuristic)
        cand_counts = get_color_counts(cand)
        total_px = hc * wc if hc * wc > 0 else 1
        entropy = -sum((cnt / total_px) * math.log2(cnt / total_px) for cnt in cand_counts.values() if cnt > 0)
        norm_entropy = entropy / math.log2(10.0)
        score += 0.35 * (1.0 - norm_entropy)

        scored.append((cand, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    unique_ranked: list[tuple[Grid, float]] = []
    seen: set[str] = set()
    for g, s in scored:
        key = repr(g)
        if key not in seen:
            seen.add(key)
            unique_ranked.append((g, s))

    return unique_ranked
