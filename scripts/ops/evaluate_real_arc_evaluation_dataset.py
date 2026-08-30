#!/usr/bin/env python3
"""Rigorous Ground-Truth Benchmark on Real ARC-AGI Evaluation Challenges.

Tests our 21-primitive ARCDSLSynthesizer + Poincaré Geodesic Pruner against all
100 real evaluation tasks in `arc-agi_evaluation_challenges.json` vs `arc-agi_evaluation_solutions.json`.
"""

import json
import logging
import os
import time
from cohezion.competitions.arc.dsl_synthesizer import ARCDSLSynthesizer
from cohezion.competitions.arc.frontier_arc_primitives import (
    sort_components_by_area, geodesic_bfs_propagation, conv_pattern_replacement
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [ARC_BENCHMARK] %(message)s")
logger = logging.getLogger("arc_benchmark")

def main():
    print("\n" + "=" * 105)
    print("🔥 REAL ARC-AGI EVALUATION DATASET BENCHMARK (100 REAL GROUND-TRUTH CHALLENGES)")
    print("=" * 105)

    challenges_path = "data/kaggle/arc2/arc-agi_evaluation_challenges.json"
    solutions_path = "data/kaggle/arc2/arc-agi_evaluation_solutions.json"

    with open(challenges_path, "r", encoding="utf-8") as f:
        challenges = json.load(f)
    with open(solutions_path, "r", encoding="utf-8") as f:
        solutions = json.load(f)

    print(f"• Loaded {len(challenges)} Official Evaluation Tasks.")
    print(f"• Loaded {len(solutions)} Ground-Truth Solutions.\n")

    synth = ARCDSLSynthesizer()
    # Register additional frontier primitives
    synth.primitives.extend([
        ("ccl_sort_area", sort_components_by_area),
        ("geodesic_bfs", geodesic_bfs_propagation),
        ("conv_stencil_cross", conv_pattern_replacement)
    ])

    solved_exact = 0
    total_tasks = len(challenges)
    t0 = time.perf_counter()

    solved_task_ids = []

    for idx, (task_id, task_data) in enumerate(challenges.items(), 1):
        ground_truth = solutions.get(task_id, [[]])[0]
        try:
            pred = synth.synthesize(task_data)
            if pred == ground_truth:
                solved_exact += 1
                solved_task_ids.append(task_id)
                print(f"  [Task {idx:03d}/{total_tasks}] 🟢 SOLVED EXACT: `{task_id}`")
        except Exception:
            pass

    dt = time.perf_counter() - t0
    accuracy = (solved_exact / total_tasks) * 100.0
    throughput = total_tasks / dt

    print("\n" + "-" * 105)
    print(f"🏆 REAL EVALUATION RESULTS")
    print("-" * 105)
    print(f"  • Total Evaluation Tasks Tested : {total_tasks}")
    print(f"  • Exact Matches (Ground Truth)  : {solved_exact} / {total_tasks} ({accuracy:.2f}%)")
    print(f"  • Total Benchmark Runtime       : {dt:.3f} seconds ({throughput:.1f} tasks/sec)")
    print(f"  • Solved Task IDs               : {solved_task_ids}")
    print("=" * 105 + "\n")

if __name__ == "__main__":
    main()
