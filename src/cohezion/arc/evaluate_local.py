#!/usr/bin/env python3
"""Local ARC evaluation harness — score predictions against known solutions.

This prevents blind Kaggle submissions by scoring locally first.
"""

import json
from pathlib import Path


def load_data(data_dir: Path) -> tuple[dict, dict, dict]:
    """Load evaluation challenges + solutions + test challenges."""
    eval_chal = json.loads((data_dir / "arc-agi_evaluation_challenges.json").read_text())
    eval_sol = json.loads((data_dir / "arc-agi_evaluation_solutions.json").read_text())
    test_chal = json.loads((data_dir / "arc-agi_test_challenges.json").read_text())
    return eval_chal, eval_sol, test_chal


def grids_equal(a: list[list[int]], b: list[list[int]]) -> bool:
    """Check if two grids are identical."""
    if len(a) != len(b):
        return False
    return all(row_a == row_b for row_a, row_b in zip(a, b))


def score_submission(submission: dict, eval_chal: dict, eval_sol: dict) -> dict:
    """Score submission against evaluation solutions.

    Returns dict with accuracy, per-task results, and attempt breakdown.
    """
    results = {
        "total_eval_tasks": len(eval_sol),
        "attempted": 0,
        "correct_attempt_1": 0,
        "correct_attempt_2": 0,
        "correct_either": 0,
        "per_task": {},
    }

    for tid, solution in eval_sol.items():
        if tid not in submission:
            results["per_task"][tid] = {"status": "missing", "correct": False}
            continue

        preds = submission[tid]
        if not isinstance(preds, list) or len(preds) == 0:
            results["per_task"][tid] = {"status": "empty", "correct": False}
            continue

        results["attempted"] += 1
        pred = preds[0]  # First prediction

        a1 = pred.get("attempt_1")
        a2 = pred.get("attempt_2")

        correct_1 = grids_equal(a1, solution) if a1 else False
        correct_2 = grids_equal(a2, solution) if a2 else False

        if correct_1:
            results["correct_attempt_1"] += 1
        if correct_2:
            results["correct_attempt_2"] += 1
        if correct_1 or correct_2:
            results["correct_either"] += 1

        results["per_task"][tid] = {
            "status": "submitted",
            "correct_1": correct_1,
            "correct_2": correct_2,
            "correct": correct_1 or correct_2,
        }

    total = results["total_eval_tasks"]
    results["accuracy_attempt_1"] = results["correct_attempt_1"] / total if total else 0
    results["accuracy_either"] = results["correct_either"] / total if total else 0

    return results


def print_scorecard(results: dict, top_n: int = 10) -> None:
    """Print formatted scorecard."""
    print("=" * 60)
    print("ARC LOCAL EVALUATION SCORECARD")
    print("=" * 60)
    print(f"Total eval tasks:     {results['total_eval_tasks']}")
    print(f"Attempted:            {results['attempted']}")
    print(
        f"Correct (attempt 1):  {results['correct_attempt_1']} ({results['accuracy_attempt_1']:.2%})"
    )
    print(f"Correct (either):      {results['correct_either']} ({results['accuracy_either']:.2%})")
    print("-" * 60)

    # Per-task breakdown for correct tasks
    correct_tasks = [(tid, r) for tid, r in results["per_task"].items() if r.get("correct")]
    print(f"\nCorrect tasks ({len(correct_tasks)}):")
    for tid, r in correct_tasks[:top_n]:
        print(f"  {tid}: attempt_1={r['correct_1']}, attempt_2={r['correct_2']}")

    # Wrong tasks
    wrong_tasks = [
        (tid, r)
        for tid, r in results["per_task"].items()
        if r.get("status") == "submitted" and not r.get("correct")
    ]
    print(f"\nWrong tasks ({len(wrong_tasks)}):")
    for tid, _ in wrong_tasks[:top_n]:
        print(f"  {tid}")

    # Missing tasks
    missing = [(tid, r) for tid, r in results["per_task"].items() if r.get("status") == "missing"]
    print(f"\nMissing tasks: {len(missing)}")


if __name__ == "__main__":
    import sys

    data_dir = Path("/tmp/arc_data")
    submission_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/arc_submission.json")

    print(f"Loading data from {data_dir}...")
    eval_chal, eval_sol, test_chal = load_data(data_dir)

    print(f"Loading submission from {submission_path}...")
    submission = json.loads(submission_path.read_text())

    print(f"Scoring {len(submission)} predictions against {len(eval_sol)} eval tasks...")
    results = score_submission(submission, eval_chal, eval_sol)
    print_scorecard(results)
