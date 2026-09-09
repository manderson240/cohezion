#!/usr/bin/env python3
"""Authentic Empirical ARC Prize Evaluator on AMD Strix Halo Silicon."""

import json
import time
import numpy as np

CHALLENGES_PATH = "data/arc_prize/arc-agi_training_challenges.json"
SOLUTIONS_PATH = "data/arc_prize/arc-agi_training_solutions.json"

def solve_with_dsl(train_examples, test_input):
    """Real Domain Specific Language (DSL) for ARC grids."""
    inp = np.array(test_input)
    
    # 1. Exact Identity check
    if all(np.array_equal(np.array(ex["input"]), np.array(ex["output"])) for ex in train_examples):
        return inp.tolist()

    # 2. Check 90/180/270 Rotations
    for k in [1, 2, 3]:
        if all(np.array_equal(np.rot90(np.array(ex["input"]), k), np.array(ex["output"])) for ex in train_examples):
            return np.rot90(inp, k).tolist()

    # 3. Flips
    if all(np.array_equal(np.fliplr(np.array(ex["input"])), np.array(ex["output"])) for ex in train_examples):
        return np.fliplr(inp).tolist()
    if all(np.array_equal(np.flipud(np.array(ex["input"])), np.array(ex["output"])) for ex in train_examples):
        return np.flipud(inp).tolist()

    # 4. Monochromatic constant fill check
    const_colors = [np.unique(np.array(ex["output"])) for ex in train_examples]
    if all(len(c) == 1 for c in const_colors) and len(set(c[0] for c in const_colors)) == 1:
        target_color = const_colors[0][0]
        out_shape = np.array(train_examples[0]["output"]).shape
        return np.full(out_shape, target_color).tolist()

    # Default fallback
    return inp.tolist()

def run_real_evaluation(max_tasks=100):
    print("\n" + "=" * 115)
    print("🧠 RUNNING AUTHENTIC EMPIRICAL ARC PRIZE 2026 BENCHMARK ON AMD STRIX HALO SILICON")
    print("=" * 115)

    with open(CHALLENGES_PATH, "r") as f:
        challenges = json.load(f)
    with open(SOLUTIONS_PATH, "r") as f:
        solutions = json.load(f)

    task_ids = list(challenges.keys())[:max_tasks]
    print(f"Evaluating {len(task_ids)} real ARC training tasks...")

    correct = 0
    total = 0
    t0 = time.perf_counter()

    for tid in task_ids:
        task = challenges[tid]
        sol_list = solutions[tid]
        train_pairs = task["train"]
        test_pairs = task["test"]

        for i, test_case in enumerate(test_pairs):
            pred = solve_with_dsl(train_pairs, test_case["input"])
            expected = sol_list[i]
            if pred == expected:
                correct += 1
            total += 1

    dt = round(time.perf_counter() - t0, 3)
    accuracy = (correct / total) * 100.0

    print(f"\n📊 EMPIRICAL GROUND TRUTH RESULTS:")
    print(f"  • Total Tasks Evaluated: {len(task_ids)} ({total} test cases)")
    print(f"  • Exact Match Solutions: {correct}/{total}")
    print(f"  • Real Empirical Accuracy: {accuracy:.2f}%")
    print(f"  • Total Execution Latency: {dt}s ({round(dt/total*1000, 2)} ms/task)")
    print("=" * 115 + "\n")

    return accuracy

if __name__ == "__main__":
    run_real_evaluation(100)
