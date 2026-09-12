"""AutoHarness Invariant Verifier and Quantile Diversified Ranker for ARC-AGI-2 & ARC-AGI-3.

Based on Grandmaster neuro-symbolic research (arXiv:2603.03329v1 & arXiv:2609.03807):
Transforms raw stochastic candidate guesses into high-precision, verified submissions by:
1. Deriving deterministic shape invariants across training demonstration pairs.
2. Checking palette conservation and background preservation.
3. Scoring candidates via Minimum Description Length (MDL / Occam's Razor).
4. Selecting Attempt 1 (top verified) and Attempt 2 (maximally diverse verified alternative).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class ShapeInvariant:
    """Shape rule observed across all training demonstrations of a task."""

    rule_type: str  # "identity" | "constant" | "scaled" | "dynamic"
    target_shape: tuple[int, int] | None = None
    scale_factor: tuple[float, float] | None = None

    def validate(self, input_shape: tuple[int, int], candidate_shape: tuple[int, int]) -> bool:
        """Verify whether candidate output matches the derived shape invariant."""
        if self.rule_type == "identity":
            return candidate_shape == input_shape
        elif self.rule_type == "constant" and self.target_shape is not None:
            return candidate_shape == self.target_shape
        elif self.rule_type == "scaled" and self.scale_factor is not None:
            expected = (
                round(input_shape[0] * self.scale_factor[0]),
                round(input_shape[1] * self.scale_factor[1]),
            )
            return candidate_shape == expected
        # Dynamic / complex - allow if within valid ARC limits
        return 0 < candidate_shape[0] <= 30 and 0 < candidate_shape[1] <= 30


class TaskInvariantAnalyzer:
    """Extracts formal invariants from training demonstration pairs."""

    @staticmethod
    def derive_shape_invariant(train_pairs: Sequence[dict[str, Any]]) -> ShapeInvariant:
        if not train_pairs:
            return ShapeInvariant(rule_type="dynamic")

        shapes_in = [np.shape(p["input"]) for p in train_pairs]
        shapes_out = [np.shape(p["output"]) for p in train_pairs]

        # 1. Identity shape: H_out == H_in and W_out == W_in for all pairs
        if all(s_in == s_out for s_in, s_out in zip(shapes_in, shapes_out)):
            return ShapeInvariant(rule_type="identity")

        # 2. Constant scaling factor: H_out / H_in == c1 and W_out / W_in == c2
        try:
            scale_r = shapes_out[0][0] / shapes_in[0][0]
            scale_c = shapes_out[0][1] / shapes_in[0][1]
            if (scale_r != 1.0 or scale_c != 1.0) and all(
                math.isclose(s_out[0] / s_in[0], scale_r, rel_tol=1e-3)
                and math.isclose(s_out[1] / s_in[1], scale_c, rel_tol=1e-3)
                for s_in, s_out in zip(shapes_in, shapes_out)
            ):
                return ShapeInvariant(rule_type="scaled", scale_factor=(scale_r, scale_c))
        except ZeroDivisionError:
            pass

        # 3. Constant shape: all outputs have identical fixed (H, W)
        first_out = shapes_out[0]
        if all(s_out == first_out for s_out in shapes_out):
            return ShapeInvariant(rule_type="constant", target_shape=first_out)

        return ShapeInvariant(rule_type="dynamic")

    @staticmethod
    def derive_allowed_colors(train_pairs: Sequence[dict[str, Any]]) -> set[int]:
        """Extract set of allowable colors across training pairs."""
        colors: set[int] = set()
        for p in train_pairs:
            colors.update(int(c) for c in np.unique(p["output"]))
            colors.update(int(c) for c in np.unique(p["input"]))
        return colors


# -----------------------------------------------------------------------------
# D4 Dihedral Symmetry Predicates & Palette Utilities
# -----------------------------------------------------------------------------
def is_horizontal_reflection(g: np.ndarray) -> bool:
    return bool(np.array_equal(g, np.fliplr(g)))


def is_vertical_reflection(g: np.ndarray) -> bool:
    return bool(np.array_equal(g, np.flipud(g)))


def is_180_rotation(g: np.ndarray) -> bool:
    return bool(np.array_equal(g, np.rot90(g, 2)))


def is_main_diagonal_reflection(g: np.ndarray) -> bool:
    if g.shape[0] != g.shape[1]:
        return False
    return bool(np.array_equal(g, g.T))


def is_anti_diagonal_reflection(g: np.ndarray) -> bool:
    if g.shape[0] != g.shape[1]:
        return False
    return bool(np.array_equal(g, np.fliplr(np.flipud(g)).T))


def is_symmetry_trivial(name: str, g: np.ndarray) -> bool:
    h, w = int(g.shape[0]), int(g.shape[1])
    if name == "horizontal":
        return bool(w <= 1)
    if name == "vertical":
        return bool(h <= 1)
    if name in ("main_diagonal", "anti_diagonal"):
        return bool(h != w or h <= 1)
    if name == "rotation_180":
        return bool(h <= 1 and w <= 1)
    return False


SYMMETRY_PREDICATES = {
    "horizontal": is_horizontal_reflection,
    "vertical": is_vertical_reflection,
    "rotation_180": is_180_rotation,
    "main_diagonal": is_main_diagonal_reflection,
    "anti_diagonal": is_anti_diagonal_reflection,
}


def get_common_symmetries(train_outputs: list[np.ndarray]) -> set[str]:
    if not train_outputs:
        return set()
    common = set(SYMMETRY_PREDICATES.keys())
    for out in train_outputs:
        common = {name for name in common if SYMMETRY_PREDICATES[name](out)}
        if not common:
            break
    non_trivial = set()
    for name in common:
        if any(not is_symmetry_trivial(name, out) for out in train_outputs):
            non_trivial.add(name)
    return non_trivial


def get_constant_new_colors(
    train_inputs: list[np.ndarray], train_outputs: list[np.ndarray]
) -> set[int]:
    if not train_inputs or not train_outputs:
        return set()
    new_sets = []
    for inp, out in zip(train_inputs, train_outputs):
        in_c = set(np.unique(inp)) - {0}
        out_c = set(np.unique(out)) - {0}
        new_sets.append(out_c - in_c)
    if not new_sets:
        return set()
    common = set(new_sets[0])
    for s in new_sets[1:]:
        common &= s
    return common


class AutoHarnessCandidateVerifier:
    """Verifies and ranks candidate ARC solution grids."""

    def __init__(self, task_dict: dict[str, Any]):
        self.task_dict = task_dict
        self.train_pairs = task_dict.get("train", [])
        self.train_inputs = [np.asarray(p["input"]) for p in self.train_pairs]
        self.train_outputs = [np.asarray(p["output"]) for p in self.train_pairs]
        self.shape_inv = TaskInvariantAnalyzer.derive_shape_invariant(self.train_pairs)
        self.allowed_colors = TaskInvariantAnalyzer.derive_allowed_colors(self.train_pairs)
        self.common_symmetries = get_common_symmetries(self.train_outputs)
        self.constant_new_colors = get_constant_new_colors(self.train_inputs, self.train_outputs)

    def verify_candidate(
        self, test_input: np.ndarray, candidate: np.ndarray
    ) -> tuple[bool, float, str]:
        """Verify candidate solution against task invariants.

        Returns
        -------
        (passed, penalty_or_bonus, reason)
        """
        if not isinstance(candidate, np.ndarray) or candidate.ndim != 2:
            return False, -100.0, "invalid_array_type"

        # 1. Bounds check
        h, w = candidate.shape
        if h <= 0 or h > 30 or w <= 0 or w > 30:
            return False, -100.0, "out_of_bounds"

        # 2. Shape invariant check
        in_shape = test_input.shape
        cand_shape = candidate.shape
        if not self.shape_inv.validate(in_shape, cand_shape):
            return False, -50.0, f"bad_shape_{cand_shape}_vs_{self.shape_inv.rule_type}"

        # 3. Color conservation check
        cand_colors = set(np.unique(candidate))
        unknown_colors = cand_colors - self.allowed_colors
        if unknown_colors:
            return False, -30.0, f"unallowed_colors_{unknown_colors}"

        # 4. D4 Dihedral Symmetry Invariant Pruning
        if self.common_symmetries:
            for sym_name in self.common_symmetries:
                if not SYMMETRY_PREDICATES[sym_name](candidate):
                    return False, -40.0, f"violated_symmetry_{sym_name}"

        # 5. Soft Color Histogram Conservation
        local_allowed = (set(np.unique(test_input)) - {0}) | self.constant_new_colors | {0}
        bad_cells = sum(1 for cell in candidate.flat if cell not in local_allowed)
        color_penalty = (bad_cells / float(h * w)) * 10.0

        # 6. Occam MDL / Entropy smoothness
        diff_h = np.sum(candidate[1:, :] != candidate[:-1, :])
        diff_w = np.sum(candidate[:, 1:] != candidate[:, :-1])
        total_edges = (h - 1) * w + h * (w - 1)
        smoothness = 1.0 - (diff_h + diff_w) / max(total_edges, 1)

        # 7. 12-Parameter Quadrature HIHO 0.50 Coherence Reranker
        # Fabric 1 (Space): Foreground spatial geometry overlap
        mask_in = test_input != 0
        mask_cand = candidate != 0
        if test_input.shape == candidate.shape:
            inter = float(np.sum(mask_in & mask_cand))
            union = float(np.sum(mask_in | mask_cand))
            sigma_space = inter / max(union, 1.0)
        else:
            sigma_space = 0.50

        # Fabric 2 (Field): Color field conservation / retention
        if test_input.shape == candidate.shape:
            sigma_field = float(np.mean(candidate == test_input))
        else:
            in_colors = set(np.unique(test_input))
            cand_colors = set(np.unique(candidate))
            sigma_field = len(in_colors & cand_colors) / max(len(in_colors | cand_colors), 1)

        # Fabric 3 (Control): Group-theoretic D4 symmetry activation
        sym_count = sum(1 for sym_fn in SYMMETRY_PREDICATES.values() if sym_fn(candidate))
        sigma_control = sym_count / float(len(SYMMETRY_PREDICATES))

        # Fabric 4 (Precipitation): Foreground active matter density
        sigma_precip = float(np.count_nonzero(candidate)) / float(h * w)

        coherence = 0.25 * (sigma_space + sigma_field + sigma_control + sigma_precip)
        phi_hiho = max(0.0, 1.0 - 4.0 * ((coherence - 0.5) ** 2))
        dissonance = abs(coherence - 0.5) * 2.0
        hiho_bonus = 2.0 * phi_hiho - 1.0 * dissonance

        bonus = float(smoothness * 2.0 + hiho_bonus - color_penalty)
        return True, bonus, "passed"


def rank_and_select_candidates(
    test_input: np.ndarray,
    candidates: Sequence[np.ndarray | dict[str, Any]],
    task_dict: dict[str, Any],
    n_guesses: int = 2,
    diversity_threshold: float = 0.25,
) -> list[list[list[int]]]:
    """Rank candidates with AutoHarness invariant verification and diversity ensembling.

    Parameters
    ----------
    test_input : np.ndarray
        The input grid for this test query.
    candidates : Sequence
        List of candidate grids (or dictionaries with 'solution' key).
    task_dict : dict
        The full task JSON containing 'train' pairs.
    n_guesses : int
        Number of distinct attempts to return (usually 2).
    diversity_threshold : float
        Minimum normalized Hamming distance for Attempt 2 relative to Attempt 1.
    """
    verifier = AutoHarnessCandidateVerifier(task_dict)

    # Normalize candidate grids
    grid_list: list[np.ndarray] = []
    base_scores: list[float] = []

    for item in candidates:
        if isinstance(item, dict) and "solution" in item:
            grid = np.asarray(item["solution"], dtype=np.int32)
            score = float(item.get("beam_score", 1.0))
        elif isinstance(item, (np.ndarray, list)):
            grid = np.asarray(item, dtype=np.int32)
            score = 1.0
        else:
            continue
        grid_list.append(grid)
        base_scores.append(score)

    if not grid_list:
        # Fallback to copy test input
        default = test_input.tolist()
        return [default] * n_guesses

    # Verify each candidate
    scored_candidates = []
    for idx, (grid, b_score) in enumerate(zip(grid_list, base_scores)):
        passed, bonus, _ = verifier.verify_candidate(test_input, grid)
        # Total rank score: passed (+100) + base_score + bonus
        total_score = (100.0 if passed else -100.0) + b_score + bonus
        scored_candidates.append((total_score, passed, idx, grid))

    # Sort descending by score
    scored_candidates.sort(key=lambda x: x[0], reverse=True)

    selected: list[np.ndarray] = []

    # 1. Pick Attempt 1 (best verified, or top fallback)
    best = scored_candidates[0][3]
    selected.append(best)

    # 2. Pick Attempt 2 with diversity clustering
    if n_guesses > 1:
        attempt_2 = None
        for _, _, _, cand in scored_candidates[1:]:
            # Check shape inequality or Hamming divergence from Attempt 1
            if cand.shape != best.shape:
                attempt_2 = cand
                break
            else:
                # Same shape: compute normalized pixel difference
                diff = np.mean(cand != best)
                if diff >= diversity_threshold:
                    attempt_2 = cand
                    break

        if attempt_2 is None:
            # If no sufficiently diverse candidate, pick the second best directly
            for _, _, _, cand in scored_candidates[1:]:
                if not np.array_equal(cand, best):
                    attempt_2 = cand
                    break

        if attempt_2 is None:
            attempt_2 = best

        selected.append(attempt_2)

    return [g.tolist() for g in selected[:n_guesses]]
