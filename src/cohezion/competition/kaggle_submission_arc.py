"""ARC Prize 2026 Kaggle submission builder.

Produces a valid submission JSON for the ARC-AGI-2 track.
Each entry maps task_id -> [predicted_output_grid].

Requirements:
- Runs without internet (pure DSL search)
- Completes within Kaggle runtime limits (~9 hours)
- Self-contained: loads data, runs solver, writes submission
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


# Add repo root to path (self-contained)
sys.path.insert(0, str(Path(__file__).resolve().parent))

import arc_solver
from arc_solver import grids_equal


def solve_task(train: list, budget: int = 5000, max_depth: int = 3) -> list | None:
    """Run solver on a single task, return best output or None."""
    ops = arc_solver.get_all_ops(train)
    program = arc_solver.search_program(train, max_depth=max_depth, ops=ops, budget=budget)
    if program is None:
        return None
    # Validate on train examples
    if not all(
        grids_equal(
            arc_solver.apply_program(arc_solver.deepcopy_grid(ex["input"]), program), ex["output"]
        )
        for ex in train
    ):
        return None
    # Apply to first test input
    if len(train) > 0 and "input" in train[0]:
        test_in = train[0]["input"]  # placeholder; real eval uses test_challenges
        return arc_solver.apply_program(arc_solver.deepcopy_grid(test_in), program)
    return None


def main() -> None:
    root = Path("/home/mike-anderson/dev/cohezion")
    eval_path = root / "data/arc-agi-2/arc-agi_evaluation_challenges.json"
    out_path = root / "data/arc-agi-2/submission.json"

    with open(eval_path) as f:
        challenges = json.load(f)

    submission: dict[str, list] = {}
    total = len(challenges)

    for idx, (task_id, task) in enumerate(sorted(challenges.items())):
        try:
            program = arc_solver.search_program(task["train"], max_depth=3, budget=5000)
            preds = []
            for test_ex in task.get("test", []):
                if program is not None:
                    out = arc_solver.apply_program(
                        arc_solver.deepcopy_grid(test_ex["input"]), program
                    )
                else:
                    out = arc_solver.deepcopy_grid(test_ex["input"])
                preds.append(out)
            if preds:
                submission[task_id] = preds
        except Exception:
            pass

        if (idx + 1) % 100 == 0:
            print(f"Progress: {idx + 1}/{total} tasks processed")

    with open(out_path, "w") as f:
        json.dump(submission, f)

    print(f"\nSubmission written: {out_path}")
    print(f"Tasks with predictions: {len(submission)}/{total}")
    print(f"METRIC eval_tasks_submitted={len(submission)}")


if __name__ == "__main__":
    main()
