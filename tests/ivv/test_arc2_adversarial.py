"""Adversarial Verification Suite for ARC-AGI-2 Solutions.

Independent Verification & Validation Authority (IV&V).
Enforces:
1. Ragged grid dimension fuzzing (1x30, 30x1, 1x1, 30x30, etc.)
2. N_train <= 2 trap protection: Heuristic DSL synthesis NEVER allowed to overwrite neural models on small train sets
3. Monotonic Improvement Invariant: Neural model attempt_1 is strictly immutable; DSL predictions strictly injected into attempt_2
4. Transformation & gravity_fall operator robustness across array/list types (0 unhandled exceptions)
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import numpy as np
import pytest


# --- Candidate Verification Contracts & Reference Implementations ---

def gravity_fall(
    grid: List[List[int]] | np.ndarray,
    direction: str = "down",
) -> List[List[int]]:
    """Simulate gravity fall on a 2D ARC grid across any supported array/list type.

    Parameters
    ----------
    grid : List[List[int]] | np.ndarray
        The input grid with values in [0, 9], where 0 is background/empty.
    direction : str
        Direction of gravity: 'down', 'up', 'left', 'right'.

    Returns
    -------
    List[List[int]]
        The resulting grid after gravity fall.
    """
    arr = np.array(grid, dtype=np.int32)
    if arr.ndim != 2:
        raise ValueError(f"Grid must be 2D, got shape {arr.shape}")
    H, W = arr.shape
    if H == 0 or W == 0:
        return []

    res = np.copy(arr)
    if direction == "down":
        for c in range(W):
            col = res[:, c]
            nonzero = col[col != 0]
            zeros = np.zeros(H - len(nonzero), dtype=np.int32)
            res[:, c] = np.concatenate([zeros, nonzero])
    elif direction == "up":
        for c in range(W):
            col = res[:, c]
            nonzero = col[col != 0]
            zeros = np.zeros(H - len(nonzero), dtype=np.int32)
            res[:, c] = np.concatenate([nonzero, zeros])
    elif direction == "right":
        for r in range(H):
            row = res[r, :]
            nonzero = row[row != 0]
            zeros = np.zeros(W - len(nonzero), dtype=np.int32)
            res[r, :] = np.concatenate([zeros, nonzero])
    elif direction == "left":
        for r in range(H):
            row = res[r, :]
            nonzero = row[row != 0]
            zeros = np.zeros(W - len(nonzero), dtype=np.int32)
            res[r, :] = np.concatenate([nonzero, zeros])
    else:
        raise ValueError(f"Unknown direction '{direction}'")

    return res.tolist()


def resolve_arc_attempts(
    train_pairs: List[Dict[str, Any]],
    test_input: List[List[int]],
    neural_pred: List[List[int]],
    dsl_pred: List[List[int]] | None = None,
) -> Dict[str, List[List[int]]]:
    """Candidate ARC submission synthesizer enforcing Monotonic Improvement Invariant.

    Parameters
    ----------
    train_pairs : List[Dict[str, Any]]
        Training demonstration pairs [{'input': ..., 'output': ...}].
    test_input : List[List[int]]
        Test input grid.
    neural_pred : List[List[int]]
        Primary hypothesis prediction from neural model.
    dsl_pred : List[List[int]] | None
        Secondary hypothesis prediction from DSL heuristic program.

    Returns
    -------
    Dict[str, List[List[int]]]
        Kaggle submission dict with 'attempt_1' and 'attempt_2'.
    """
    n_train = len(train_pairs)

    # Invariant: attempt_1 is immutable and strictly preserved from the neural model
    attempt_1 = [list(row) for row in neural_pred]

    # Invariant: When n_train <= 2, heuristic DSL is quarantined to avoid overfitting
    if n_train <= 2 or dsl_pred is None:
        attempt_2 = [list(row) for row in neural_pred]
    else:
        # DSL predictions are strictly injected into attempt_2
        attempt_2 = [list(row) for row in dsl_pred]

    return {"attempt_1": attempt_1, "attempt_2": attempt_2}


# --- IV&V Adversarial Tests ---

class TestARC2AdversarialSuite:
    """Independent verification test suite for ARC-AGI-2 solutions."""

    @pytest.mark.parametrize(
        "shape",
        [
            (1, 30),
            (30, 1),
            (1, 1),
            (30, 30),
            (2, 29),
            (29, 2),
            (15, 15),
        ],
    )
    def test_ragged_dimensions_fuzzing(self, shape: Tuple[int, int]) -> None:
        """Adversarially tests candidate grid operators on extreme ragged dimensions."""
        H, W = shape
        rng = np.random.default_rng(seed=42 + H * 31 + W)
        grid = rng.integers(0, 10, size=(H, W), dtype=np.int32).tolist()

        for direction in ["down", "up", "left", "right"]:
            out = gravity_fall(grid, direction=direction)
            assert len(out) == H, f"Output height {len(out)} != input height {H}"
            assert len(out[0]) == W, f"Output width {len(out[0])} != input width {W}"
            for row in out:
                for val in row:
                    assert 0 <= val <= 9, f"Value {val} out of valid ARC palette [0, 9]"

    @pytest.mark.parametrize("n_train", [1, 2])
    def test_n_train_le_2_trap(self, n_train: int) -> None:
        """Verifies that heuristic DSL synthesis is NEVER allowed to overwrite neural models on small train sets."""
        train_pairs = [
            {"input": [[1, 0], [0, 1]], "output": [[0, 1], [1, 0]]}
            for _ in range(n_train)
        ]
        test_in = [[2, 0], [0, 2]]
        neural_pred = [[0, 2], [2, 0]]
        # Adversarial DSL that overfitted a spurious 1-pixel rule
        spurious_dsl_pred = [[9, 9], [9, 9]]

        sub = resolve_arc_attempts(
            train_pairs=train_pairs,
            test_input=test_in,
            neural_pred=neural_pred,
            dsl_pred=spurious_dsl_pred,
        )

        # Trap check: DSL must NOT appear in attempt_1 OR attempt_2 when n_train <= 2
        assert sub["attempt_1"] == neural_pred, "Monotonic Invariant violated: attempt_1 altered!"
        assert sub["attempt_2"] != spurious_dsl_pred, (
            f"N_train <= 2 trap violated: Spurious DSL was accepted with n_train={n_train}!"
        )
        assert sub["attempt_2"] == neural_pred, "attempt_2 should fall back to neural prediction when DSL is quarantined"

    def test_monotonic_improvement_invariant(self) -> None:
        """Tests that neural model attempt_1 is never altered; DSL predictions are strictly injected into attempt_2."""
        train_pairs = [{"input": [[1]], "output": [[2]]} for _ in range(4)]  # n_train = 4 > 2
        test_in = [[3]]
        neural_pred = [[4]]
        dsl_pred = [[5]]

        sub = resolve_arc_attempts(
            train_pairs=train_pairs,
            test_input=test_in,
            neural_pred=neural_pred,
            dsl_pred=dsl_pred,
        )

        # Invariant 1: attempt_1 strictly preserves neural model
        assert sub["attempt_1"] == neural_pred
        # Invariant 2: DSL prediction strictly goes into attempt_2
        assert sub["attempt_2"] == dsl_pred
        assert sub["attempt_1"] != sub["attempt_2"]

    @pytest.mark.parametrize(
        "input_type",
        [
            "python_list",
            "numpy_int32",
            "numpy_int64",
            "numpy_uint8",
        ],
    )
    def test_gravity_fall_array_type_robustness(self, input_type: str) -> None:
        """Tests gravity_fall operator with various array/list types to guarantee 0 unhandled exceptions."""
        base_grid = [[1, 0, 2], [0, 3, 0], [4, 0, 5]]
        if input_type == "python_list":
            inp = base_grid
        elif input_type == "numpy_int32":
            inp = np.array(base_grid, dtype=np.int32)
        elif input_type == "numpy_int64":
            inp = np.array(base_grid, dtype=np.int64)
        elif input_type == "numpy_uint8":
            inp = np.array(base_grid, dtype=np.uint8)
        else:
            raise ValueError(f"Unknown input_type {input_type}")

        out = gravity_fall(inp, direction="down")
        assert isinstance(out, list)
        assert all(isinstance(r, list) for r in out)
        # Expected bottom row should accumulate fallen nonzeros
        expected_bottom = [4, 3, 5]
        assert out[2] == expected_bottom
