"""Evaluate ARC solver on training data (where solutions are known)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from arc_solver import grids_equal, search_program


def evaluate() -> None:
    root = Path("/home/mike-anderson/dev/cohezion")

    # Evaluate on eval set (120 tasks with known solutions) for validation
    challenges_path = root / "data" / "arc-agi-2" / "arc-agi_evaluation_challenges.json"
    solutions_path = root / "data" / "arc-agi-2" / "arc-agi_evaluation_solutions.json"

    with challenges_path.open() as f:
        challenges = json.load(f)
    with solutions_path.open() as f:
        solutions = json.load(f)

    total = len(challenges)
    correct = 0
    solved_with_search = 0
    times = []

    for idx, task_id in enumerate(sorted(challenges)):
        task = challenges[task_id]
        task["id"] = task_id
        task_sols = solutions[task_id]

        start = time.monotonic()
        program = search_program(task["train"], max_depth=3, budget=5000)
        elapsed = time.monotonic() - start
        times.append(elapsed)

        if program is not None:
            solved_with_search += 1

        if task_sols and task.get("test"):
            expected = task_sols[0]
            pred_input = task["test"][0]["input"]
            if program:
                from arc_solver import apply_program

                pred_attempt1 = apply_program(pred_input, program)
            else:
                pred_attempt1 = pred_input
            if pred_attempt1 and grids_equal(pred_attempt1, expected):
                correct += 1

        if idx % 30 == 29:
            current_rate = correct / (idx + 1) * 100
            print(f"  Progress {idx + 1}/{total}: {current_rate:.1f}%", flush=True)

    print(f"Evaluation tasks: {total}")
    print(
        f"Solved by search (depth <= 3): {solved_with_search} ({solved_with_search / total * 100:.1f}%)"
    )
    print(f"Correct on eval test: {correct} ({correct / total * 100:.1f}%)")
    print(f"Avg solve time: {sum(times) / len(times):.3f}s")
    print(f"90th percentile time: {sorted(times)[int(len(times) * 0.9)]:.3f}s")


if __name__ == "__main__":
    evaluate()
