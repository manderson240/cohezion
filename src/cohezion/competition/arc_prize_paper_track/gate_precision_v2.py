"""Measure alignment gate precision by intercepting solver search.

We patch _search_depth_bfs to collect alignment scores for:
1. Programs that pass exact match (correct)
2. Programs that fail exact match (wrong)

This gives us a real distribution of alignment scores for both classes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import arc_solver
from arc_solver import deepcopy_grid, grids_equal


def structural_alignment_score(candidate_output: Any, expected: Any) -> float:
    """Structural coherence between candidate and expected output."""
    if candidate_output is None or expected is None:
        return 0.0

    # Dimension ratio
    out_h, exp_h = len(candidate_output), len(expected)
    dim_score = 0.0
    if exp_h > 0 and out_h > 0:
        ratio = out_h / exp_h
        if 0.5 <= ratio <= 2.0:
            dim_score = 1.0 - abs(1 - ratio)

    # Color overlap
    out_colors = {c for row in candidate_output for c in row}
    exp_colors = {c for row in expected for c in row}
    color_score = len(out_colors & exp_colors) / max(len(exp_colors), 1) if exp_colors else 1.0

    # Size similarity
    out_size = sum(len(row) for row in candidate_output)
    exp_size = sum(len(row) for row in expected)
    size_score = 1.0 if exp_size > 0 and 0.25 <= out_size / exp_size <= 4.0 else 0.0

    # Background consistency
    from collections import Counter

    out_bg = Counter(c for row in candidate_output for c in row).most_common(1)
    exp_bg = Counter(c for row in expected for c in row).most_common(1)
    bg_score = 1.0 if out_bg and exp_bg and out_bg[0][0] == exp_bg[0][0] else 0.0

    return (dim_score + color_score + size_score + bg_score) / 4.0


# Monkey-patch _search_depth_bfs to collect scores
original_search = arc_solver._search_depth_bfs
COLLECTED = {"correct": [], "wrong": []}


def collecting_search(train, depth, ops, budget, visited, global_counter=None):
    if global_counter is None:
        global_counter = [0]

    if depth == 1:
        for name, op in ops:
            global_counter[0] += 1
            if global_counter[0] > budget:
                return None

            is_correct = True
            scores = []
            for ex in train:
                pred = op(deepcopy_grid(ex["input"]))
                score = structural_alignment_score(pred, ex["output"])
                scores.append(score)
                if not grids_equal(pred, ex["output"]):
                    is_correct = False

            avg_score = sum(scores) / len(scores)
            if is_correct:
                COLLECTED["correct"].append((name, avg_score))
                return [op]
            else:
                COLLECTED["wrong"].append((name, avg_score))
        return None

    for name, op in ops:
        transformed = []
        valid = True
        for ex in train:
            t = op(deepcopy_grid(ex["input"]))
            if t is None:
                valid = False
                break
            transformed.append({"input": t, "output": ex["output"]})
        if not valid:
            continue
        sub = collecting_search(transformed, depth - 1, ops, budget, visited, global_counter)
        if sub is not None:
            return [op, *sub]
    return None


arc_solver._search_depth_bfs = collecting_search


if __name__ == "__main__":
    root = Path("/home/mike-anderson/dev/cohezion")
    with open(root / "data/arc-agi-2/arc-agi_training_challenges.json") as f:
        challenges = json.load(f)
    with open(root / "data/arc-agi-2/arc-agi_training_solutions.json") as f:
        solutions = json.load(f)

    # Run solver on first 50 tasks
    task_ids = sorted(challenges)[:50]
    for task_id in task_ids:
        task = challenges[task_id]
        ops = arc_solver.get_all_ops(task["train"])
        _ = arc_solver.search_program(task["train"], max_depth=3, ops=ops, budget=5000)

    correct_scores = [s for _, s in COLLECTED["correct"]]
    wrong_scores = [s for _, s in COLLECTED["wrong"]]

    print(f"\n{'=' * 60}")
    print("ALIGNMENT GATE PRECISION (50 tasks, budget=5000)")
    print(f"{'=' * 60}")
    print(f"Correct programs tested: {len(correct_scores)}")
    print(f"Wrong programs tested:   {len(wrong_scores)}")

    if correct_scores:
        print(
            f"Correct scores: μ={sum(correct_scores) / len(correct_scores):.3f}, "
            f"min={min(correct_scores):.3f}, max={max(correct_scores):.3f}"
        )
    if wrong_scores:
        print(
            f"Wrong scores:   μ={sum(wrong_scores) / len(wrong_scores):.3f}, "
            f"min={min(wrong_scores):.3f}, max={max(wrong_scores):.3f}"
        )

    # Threshold analysis
    best_f1 = 0
    best_thresh = 0
    for t in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        tp = sum(1 for s in correct_scores if s >= t)
        fp = sum(1 for s in wrong_scores if s >= t)
        fn = sum(1 for s in correct_scores if s < t)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = t
        print(f"  t={t:.1f}: P={precision:.3f}, R={recall:.3f}, F1={f1:.3f}, TP={tp}, FP={fp}")

    print(f"\nBest: threshold={best_thresh:.1f}, F1={best_f1:.3f}")
    print(f"METRIC alignment_gate_precision={best_f1:.3f}")
