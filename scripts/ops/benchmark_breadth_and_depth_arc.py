#!/usr/bin/env python3
"""Evaluates Breadth & Depth Synthesizer across 1,000 Real ARC Tasks."""

import json
import logging
import time
from cohezion.competitions.arc.deep_compositional_solver import DeepCompositionalSynthesizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [ARC_DEEP] %(message)s")
logger = logging.getLogger("arc_deep")

def main():
    print("\n" + "=" * 105)
    print("🚀 BREADTH & DEPTH ARC PROGRAM SYNTHESIS BENCHMARK (1,000 OFFICIAL TASKS)")
    print("=" * 105)

    challenges_path = "data/kaggle/arc2/arc-agi_training_challenges.json"
    solutions_path = "data/kaggle/arc2/arc-agi_training_solutions.json"

    with open(challenges_path, "r", encoding="utf-8") as f:
        challenges = json.load(f)
    with open(solutions_path, "r", encoding="utf-8") as f:
        solutions = json.load(f)

    solver = DeepCompositionalSynthesizer()
    total = len(challenges)
    solved = 0
    t0 = time.perf_counter()

    for idx, (tid, tdata) in enumerate(challenges.items(), 1):
        gt = solutions.get(tid, [[]])[0]
        pred = solver.solve(tdata)
        if pred == gt:
            solved += 1

    dt = time.perf_counter() - t0
    acc = (solved / total) * 100.0

    print("\n" + "-" * 105)
    print("🏆 BREADTH & DEPTH BENCHMARK RESULTS")
    print("-" * 105)
    print(f"• Total Tasks Tested         : {total}")
    print(f"• Solved Exactly (Ground Truth): {solved} / {total} ({acc:.2f}%)")
    print(f"• Duration                   : {dt:.2f}s ({total/dt:.1f} tasks/sec)")
    print("=" * 105 + "\n")

if __name__ == "__main__":
    main()
