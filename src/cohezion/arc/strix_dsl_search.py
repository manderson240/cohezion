"""Strix Halo High-Throughput Multithreaded DSL Search Engine for ARC-AGI-2 & ARC-AGI-3.

Optimized for Framework Desktop (AMD Ryzen AI MAX+ 395, 16 Cores / 32 Threads, 122 GiB Unified Memory).
Implements:
1. Grid-hash state deduplication (icecuber memoization) to collapse redundant branches.
2. Fast C/NumPy grid primitives (D8 dihedral group, color remap, gravity, convex hull, symmetry reflect).
3. Exact demonstration-pair verifier gating: f(x_train) == y_train.
4. Multithreaded parallel beam search across all 32 hardware threads.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from cohezion.arc.transforms import ALL_TRANSFORMS


def grid_hash(grid: np.ndarray) -> str:
    """Fast deterministic MD5 hash of a 2D integer numpy grid."""
    return hashlib.md5(np.ascontiguousarray(grid).tobytes(), usedforsecurity=False).hexdigest()


@dataclass(slots=True)
class CandidateProgram:
    """A symbolic sequence of transform names."""

    ops: tuple[str, ...]
    cost: int = 1

    def apply(self, grid: np.ndarray) -> np.ndarray | None:
        curr = grid
        for op in self.ops:
            fn = ALL_TRANSFORMS.get(op)
            if fn is None:
                return None
            nxt = fn(curr)
            if nxt is None:
                return None
            curr = nxt
        return curr


class StrixHaloDSLEngine:
    """Symbolic Beam Search with State Deduplication across Strix Halo 32 threads."""

    def __init__(
        self,
        max_depth: int = 3,
        beam_width: int = 40,
        n_threads: int = 32,
    ):
        self.max_depth = max_depth
        self.beam_width = beam_width
        self.n_threads = n_threads
        # Selected high-yield primitive names from ALL_TRANSFORMS
        self.primitive_names: list[str] = [
            "rotate_90",
            "rotate_180",
            "rotate_270",
            "flip_horizontal",
            "flip_vertical",
            "transpose",
            "gravity_drop",
            "gravity_left",
            "gravity_right",
            "gravity_up",
            "grid_symmetry_reflect_h",
            "grid_symmetry_reflect_v",
            "object_center_of_mass",
            "color_background",
            "color_majority",
            "recolor_interior",
            "recolor_enclosed",
        ]

    def _verify_program_on_train(
        self, prog: CandidateProgram, train_pairs: Sequence[dict[str, Any]]
    ) -> tuple[bool, float]:
        """Verify candidate program on all training demonstrations.

        Returns (all_exact_match, partial_cell_match_ratio)
        """
        if not train_pairs:
            return False, 0.0

        total_cells = 0
        matching_cells = 0

        for pair in train_pairs:
            inp = np.array(pair["input"], dtype=np.int32)
            tgt = np.array(pair["output"], dtype=np.int32)
            pred = prog.apply(inp)
            if pred is None or pred.shape != tgt.shape:
                return False, 0.0

            total_cells += tgt.size
            matching_cells += int(np.sum(pred == tgt))

            if not np.array_equal(pred, tgt):
                return False, matching_cells / max(total_cells, 1)

        return True, 1.0

    def solve_single_task(
        self, task_dict: dict[str, Any]
    ) -> tuple[CandidateProgram | None, list[dict[str, Any]]]:
        """Run state-deduplicated beam search for a single task.

        Returns (best_exact_program_if_found, candidate_test_predictions)
        """
        train_pairs = task_dict.get("train", [])
        test_inputs = [np.array(t["input"], dtype=np.int32) for t in task_dict.get("test", [])]

        if not train_pairs or not test_inputs:
            return None, []

        # Beam state: list of (CandidateProgram, partial_score)
        beam: list[tuple[CandidateProgram, float]] = [(CandidateProgram(ops=()), 0.0)]
        visited_hashes: set[str] = set()

        exact_solution: CandidateProgram | None = None

        for _depth in range(1, self.max_depth + 1):
            next_candidates: list[tuple[CandidateProgram, float]] = []

            for prog, _ in beam:
                for op in self.primitive_names:
                    new_ops = (*prog.ops, op)
                    new_prog = CandidateProgram(ops=new_ops, cost=len(new_ops))

                    # Evaluate on first training input to hash resulting state
                    first_in = np.array(train_pairs[0]["input"], dtype=np.int32)
                    first_out = new_prog.apply(first_in)
                    if first_out is None:
                        continue

                    h = grid_hash(first_out)
                    if h in visited_hashes:
                        continue  # State deduplication (icecuber memoization)
                    visited_hashes.add(h)

                    # Verify on all training pairs
                    exact, partial_score = self._verify_program_on_train(new_prog, train_pairs)
                    if exact:
                        exact_solution = new_prog
                        break

                    next_candidates.append((new_prog, partial_score))

                if exact_solution is not None:
                    break

            if exact_solution is not None:
                break

            if not next_candidates:
                break

            # Sort by partial score descending and prune to beam_width
            next_candidates.sort(key=lambda x: x[1], reverse=True)
            beam = next_candidates[: self.beam_width]

        # Generate test predictions
        predictions = []
        for test_in in test_inputs:
            if exact_solution is not None:
                pred = exact_solution.apply(test_in)
                sol = pred.tolist() if pred is not None else test_in.tolist()
                predictions.append(
                    {"solution": sol, "beam_score": 10.0, "source": "strix_exact_dsl"}
                )
            elif beam and beam[0][1] > 0.5:
                # Use top partial candidate as a proposal
                pred = beam[0][0].apply(test_in)
                sol = pred.tolist() if pred is not None else test_in.tolist()
                predictions.append(
                    {
                        "solution": sol,
                        "beam_score": float(beam[0][1] * 3.0),
                        "source": "strix_partial_dsl",
                    }
                )
            else:
                predictions.append(
                    {
                        "solution": test_in.tolist(),
                        "beam_score": 0.1,
                        "source": "strix_identity_fallback",
                    }
                )

        return exact_solution, predictions

    def solve_task_batch_parallel(
        self, tasks: dict[str, dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Solve a batch of tasks in parallel across Strix Halo 32 threads."""
        results: dict[str, list[dict[str, Any]]] = {}

        def _worker(item: tuple[str, dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
            t_id, t_dict = item
            _, preds = self.solve_single_task(t_dict)
            return t_id, preds

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.n_threads) as executor:
            future_to_task = {
                executor.submit(_worker, (task_id, task_dict)): task_id
                for task_id, task_dict in tasks.items()
            }
            for future in concurrent.futures.as_completed(future_to_task):
                task_id, preds = future.result()
                results[task_id] = preds

        return results
