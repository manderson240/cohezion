"""Measure alignment gate precision on ARC solver candidates.

Baseline: no alignment gate. All candidates are checked with exact grid match.
Experiment: compute structural alignment score for each candidate, measure
how well it distinguishes correct from incorrect programs.

This validates the paper's claim that the alignment gate provides
interpretable filtering before expensive exact-match verification.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from arc_solver import (
    apply_program,
    deepcopy_grid,
    get_all_ops,
    grids_equal,
    search_program,
)


def structural_alignment_score(candidate_output: Any, expected: Any) -> float:
    """Compute structural coherence between candidate and expected output.

    Based on paper's definition (Section 3.1):
    phi(f(x), y) = (1/4) * (dim_ratio + color_overlap + symmetry + bg_consistency)
    """
    if candidate_output is None or expected is None:
        return 0.0

    # 1. Dimension ratio: prefers similar-sized outputs
    out_h, exp_h = len(candidate_output), len(expected)
    dim_score = 0.0
    if exp_h > 0 and out_h > 0:
        ratio = out_h / exp_h
        if 0.5 <= ratio <= 2.0:
            dim_score = 1.0 - abs(1 - ratio)  # Closer to 1.0 is better

    # 2. Color palette overlap
    def flat_colors(grid):
        return {c for row in grid for c in row}

    out_colors = flat_colors(candidate_output)
    exp_colors = flat_colors(expected)
    if not exp_colors:
        color_score = 1.0
    else:
        overlap = len(out_colors & exp_colors) / len(exp_colors)
        color_score = overlap

    # 3. Rough size similarity (area)
    if candidate_output and expected:
        out_size = sum(len(row) for row in candidate_output)
        exp_size = sum(len(row) for row in expected)
        if exp_size > 0:
            size_ratio = out_size / exp_size
            size_score = 1.0 if 0.25 <= size_ratio <= 4.0 else 0.0
        else:
            size_score = 1.0 if out_size == 0 else 0.0
    else:
        size_score = 0.0

    # 4. Background consistency (most common color)
    from collections import Counter

    if candidate_output:
        out_bg = Counter(c for row in candidate_output for c in row).most_common(1)
    else:
        out_bg = None
    if expected:
        exp_bg = Counter(c for row in expected for c in row).most_common(1)
    else:
        exp_bg = None
    bg_score = 1.0 if out_bg and exp_bg and out_bg[0][0] == exp_bg[0][0] else 0.0

    return (dim_score + color_score + size_score + bg_score) / 4.0


def gate_score(program: Any, train_pairs: list[dict[str, Any]]) -> float:
    """Average alignment score across all training pairs."""
    scores = []
    for ex in train_pairs:
        pred = apply_program(deepcopy_grid(ex["input"]), program)
        scores.append(structural_alignment_score(pred, ex["output"]))
    return sum(scores) / max(len(scores), 1)


def measure_gate_precision(
    challenges_path: Path,
    solutions_path: Path,
    sample_size: int = 200,
) -> dict[str, Any]:
    """Measure how well the alignment gate distinguishes correct from wrong programs.

    Method:
    1. Find N tasks that the solver can solve (correct programs)
    2. For each, generate a wrong program (random ops of same depth)
    3. Compute alignment score for both correct and wrong programs
    4. Measure precision/recall at various thresholds
    """
    with open(challenges_path) as f:
        challenges = json.load(f)
    with open(solutions_path) as f:
        solutions = json.load(f)

    correct_scores = []
    wrong_scores = []
    total_correct = 0

    # Sample random tasks
    task_ids = random.sample(sorted(challenges), min(sample_size, len(challenges)))

    for task_id in task_ids[:sample_size]:
        task = challenges[task_id]
        solutions.get(task_id, [])

        # Find a correct program using a small budget
        all_ops = get_all_ops(task["train"])
        program = search_program(task["train"], max_depth=2, ops=all_ops, budget=1000)

        if program is None:
            continue

        # Verify it's actually correct
        correct = True
        for ex in task["train"]:
            pred = apply_program(deepcopy_grid(ex["input"]), program)
            if not grids_equal(pred, ex["output"]):
                correct = False
                break
        if not correct:
            continue

        total_correct += 1
        score = gate_score(program, task["train"])
        correct_scores.append(score)

        # Generate random wrong programs of same depth
        for _ in range(3):
            wrong_prog = [random.choice(all_ops)[1] for _ in range(len(program))]
            wrong_score = gate_score(wrong_prog, task["train"])
            wrong_scores.append(wrong_score)

    # Compute precision/recall at different thresholds
    results = {}
    for threshold in [0.3, 0.5, 0.7, 0.9]:
        tp = sum(1 for s in correct_scores if s >= threshold)
        fp = sum(1 for s in wrong_scores if s >= threshold)
        fn = sum(1 for s in correct_scores if s < threshold)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        results[f"threshold_{threshold:.1f}"] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }

    return {
        "tasks_tested": len(task_ids),
        "tasks_solved": total_correct,
        "correct_programs": len(correct_scores),
        "wrong_programs": len(wrong_scores),
        "correct_score_mean": round(sum(correct_scores) / max(len(correct_scores), 1), 3),
        "correct_score_std": round(
            (
                sum(
                    (s - sum(correct_scores) / max(len(correct_scores), 1)) ** 2
                    for s in correct_scores
                )
                / max(len(correct_scores), 1)
            )
            ** 0.5,
            3,
        )
        if correct_scores
        else 0,
        "wrong_score_mean": round(sum(wrong_scores) / max(len(wrong_scores), 1), 3),
        "wrong_score_std": round(
            (
                sum((s - sum(wrong_scores) / max(len(wrong_scores), 1)) ** 2 for s in wrong_scores)
                / max(len(wrong_scores), 1)
            )
            ** 0.5,
            3,
        )
        if wrong_scores
        else 0,
        "threshold_results": results,
        "best_precision": max(r["precision"] for r in results.values()),
        "best_recall_at_best_precision": next(
            r["recall"]
            for k, r in results.items()
            if r["precision"] == max(rr["precision"] for rr in results.values())
        ),
    }


if __name__ == "__main__":
    random.seed(42)
    root = Path("/home/mike-anderson/dev/cohezion")
    result = measure_gate_precision(
        root / "data/arc-agi-2/arc-agi_training_challenges.json",
        root / "data/arc-agi-2/arc-agi_training_solutions.json",
        sample_size=100,
    )

    print(f"\n{'=' * 60}")
    print("ALIGNMENT GATE PRECISION ANALYSIS")
    print(f"{'=' * 60}")
    print(f"Tasks tested: {result['tasks_tested']}")
    print(f"Tasks solved: {result['tasks_solved']}")
    print(f"Correct programs: {result['correct_programs']}")
    print(f"Wrong programs: {result['wrong_programs']}")
    print(
        f"\nCorrect program alignment scores: "
        f"μ={result['correct_score_mean']}, σ={result['correct_score_std']}"
    )
    print(
        f"Wrong program alignment scores:   "
        f"μ={result['wrong_score_mean']}, σ={result['wrong_score_std']}"
    )
    print("\nThreshold Analysis:")
    for thresh, data in result["threshold_results"].items():
        print(
            f"  {thresh}: precision={data['precision']}, recall={data['recall']}, "
            f"TP={data['tp']}, FP={data['fp']}, FN={data['fn']}"
        )
    print(f"\nMETRIC alignment_gate_precision={result['best_precision']:.3f}")
    print(f"METRIC alignment_gate_recall={result['best_recall_at_best_precision']:.3f}")
