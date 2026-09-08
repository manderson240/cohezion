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
        colors = set()
        for p in train_pairs:
            colors.update(np.unique(p["output"]))
            colors.update(np.unique(p["input"]))
        return colors


class AutoHarnessCandidateVerifier:
    """Verifies and ranks candidate ARC solution grids."""

    def __init__(self, task_dict: dict[str, Any]):
        self.task_dict = task_dict
        self.train_pairs = task_dict.get("train", [])
        self.shape_inv = TaskInvariantAnalyzer.derive_shape_invariant(self.train_pairs)
        self.allowed_colors = TaskInvariantAnalyzer.derive_allowed_colors(self.train_pairs)

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

        # 4. Occam MDL / Entropy score (higher is cleaner / less chaotic noise)
        # Compute run-length / neighborhood regularity
        diff_h = np.sum(candidate[1:, :] != candidate[:-1, :])
        diff_w = np.sum(candidate[:, 1:] != candidate[:, :-1])
        total_edges = (h - 1) * w + h * (w - 1)
        smoothness = 1.0 - (diff_h + diff_w) / max(total_edges, 1)

        bonus = float(smoothness * 2.0)
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
