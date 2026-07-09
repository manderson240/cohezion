#!/usr/bin/env python3
"""
ARC Prize Solver Evaluation Harness

Evaluates arc_solver.py against the 120 ARC-AGI-2 evaluation tasks with known solutions.
Returns solve_rate (0.0-1.0) as the reward signal for autoresearch.

Usage:
    python scripts/eval_arc_solver.py [path/to/solver.py]
    python scripts/eval_arc_solver.py --solver kaggle-dataset/arc_solver_tcrao_86c906f8.py

Output format (parseable by TCRAO):
    SOLVE_RATE: 0.1250
    CORRECT: 15/120
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
import traceback
from pathlib import Path


# Paths
COHEZION_ROOT = Path.home() / "dev" / "cohezion"
ARC_DATA_DIR = COHEZION_ROOT / "data" / "arc-agi-2"
DEFAULT_SOLVER = COHEZION_ROOT / "kaggle-dataset" / "arc_solver.py"


def load_arc_solver(solver_path: Path):
    """Dynamically import arc_solver module."""
    spec = importlib.util.spec_from_file_location("arc_solver", solver_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def grids_equal(a: list, b: list) -> bool:
    if len(a) != len(b):
        return False
    for ra, rb in zip(a, b):
        if len(ra) != len(rb):
            return False
        for ca, cb in zip(ra, rb):
            if ca != cb:
                return False
    return True


def grid_similarity(pred: list[list[int]] | None, sol: list[list[int]]) -> float:
    """Calculate continuous similarity (0.0-1.0) between predicted and solution grid."""
    if not pred or not isinstance(pred, list) or not all(isinstance(r, list) for r in pred):
        return 0.0
    h_pred = len(pred)
    if h_pred == 0:
        return 0.0
    w_pred = len(pred[0])
    if w_pred == 0 or not all(len(r) == w_pred for r in pred):
        return 0.0

    h_sol = len(sol)
    w_sol = len(sol[0]) if h_sol > 0 else 0
    if h_sol == 0 or w_sol == 0:
        return 0.0

    # Calculate match count in overlapping region
    matches = 0
    min_h = min(h_pred, h_sol)
    min_w = min(w_pred, w_sol)
    for r in range(min_h):
        for c in range(min_w):
            if pred[r][c] == sol[r][c]:
                matches += 1

    # Similarity is overlap matches divided by total elements of the larger grid
    max_elements = max(h_pred * w_pred, h_sol * w_sol)
    return matches / max_elements if max_elements > 0 else 0.0


def evaluate_solver(
    solver_module,
    tasks: dict,
    solutions: dict,
    max_tasks: int | None = None,
    budget: int = 5000,
    max_depth: int = 3,
) -> tuple[float, int, int]:
    """
    Evaluate solver on ARC tasks.

    Args:
        solver_module: Imported arc_solver module
        tasks: Dict mapping task_id -> {"train": [...], "test": [...]}}
        solutions: Dict mapping task_id -> [[output_grid]]
        max_tasks: Cap on number of tasks to evaluate (None = all)
        budget: Search budget per task
        max_depth: Max program depth

    Returns:
        (average_similarity_float, correct_count, total_count)
    """
    task_ids = sorted(tasks.keys())[:max_tasks] if max_tasks else sorted(tasks.keys())
    total = len(task_ids)
    correct = 0
    total_similarity = 0.0

    for _, task_id in enumerate(task_ids):
        try:
            task = tasks[task_id]
            solution = solutions.get(task_id)
            if not solution:
                continue

            # Get solver primitives
            ops_func = getattr(solver_module, "get_all_ops", None)
            search_func = getattr(solver_module, "search_program", None)

            if not search_func:
                print("WARNING: search_program not found in solver")
                break

            # Extract operations (or use default if get_all_ops not available)
            ops = ops_func(task["train"]) if ops_func else None
            program = search_func(task["train"], max_depth=max_depth, ops=ops, budget=budget)

            if program is None:
                continue

            # Check all test outputs
            test_inputs = task.get("test", [])
            if not test_inputs:
                continue

            task_similarities = []
            all_match = True
            for t_idx, test_ex in enumerate(test_inputs):
                if t_idx >= len(solution):
                    all_match = False
                    task_similarities.append(0.0)
                    break

                pred = solver_module.apply_program(
                    solver_module.deepcopy_grid(test_ex["input"]), program
                )
                sim = grid_similarity(pred, solution[t_idx])
                task_similarities.append(sim)
                if not grids_equal(pred, solution[t_idx]):
                    all_match = False

            if task_similarities:
                task_sim = sum(task_similarities) / len(task_similarities)
            else:
                task_sim = 0.0

            total_similarity += task_sim
            if all_match:
                correct += 1

        except KeyboardInterrupt:
            raise
        except Exception:
            # Log but continue
            traceback.print_exc()
            continue

    solve_rate = total_similarity / total if total else 0.0
    return solve_rate, correct, total


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--solver", type=Path, default=DEFAULT_SOLVER, help="Path to arc_solver.py variant"
    )
    parser.add_argument(
        "--max-tasks", type=int, default=None, help="Max tasks to evaluate (for quick smoke test)"
    )
    parser.add_argument("--budget", type=int, default=5000, help="Search budget per task")
    parser.add_argument("--max-depth", type=int, default=3, help="Max program depth")
    args = parser.parse_args()

    print(f"Loading solver: {args.solver}")
    if not args.solver.exists():
        print(f"ERROR: Solver not found: {args.solver}")
        sys.exit(1)

    solver = load_arc_solver(args.solver)

    print(f"Loading evaluation data from {ARC_DATA_DIR}...")
    challenges = json.loads((ARC_DATA_DIR / "arc-agi_evaluation_challenges.json").read_text())
    solutions = json.loads((ARC_DATA_DIR / "arc-agi_evaluation_solutions.json").read_text())

    print(f"Tasks: {len(challenges)} solutions: {len(solutions)}")
    print(f"Evaluating on {args.max_tasks or len(challenges)} tasks...")
    print()

    start = time.time()
    solve_rate, correct, total = evaluate_solver(
        solver,
        challenges,
        solutions,
        max_tasks=args.max_tasks,
        budget=args.budget,
        max_depth=args.max_depth,
    )
    elapsed = time.time() - start

    print()
    print("=== RESULTS ===")
    print(f"SOLVE_RATE: {solve_rate:.4f}")
    print(f"CORRECT: {correct}/{total}")
    print(f"WALL_TIME_S: {elapsed:.1f}")
    print("=== END ===")


if __name__ == "__main__":
    main()
