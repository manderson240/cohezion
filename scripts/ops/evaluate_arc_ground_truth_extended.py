#!/usr/bin/env python3
"""Extended Real ARC Evaluation Benchmark with Indicator Cropping & Dynamic Subgrid Search."""

import json
import logging
import time
from cohezion.competitions.arc.dsl_synthesizer import ARCDSLSynthesizer
from cohezion.competitions.arc.advanced_grid_reasoner import (
    extract_subgrid_by_indicator, extract_most_frequent_subgrid_pattern
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [ARC_BENCHMARK] %(message)s")
logger = logging.getLogger("arc_benchmark")

def dynamic_solve_task(task: dict, synth: ARCDSLSynthesizer) -> list[list[int]]:
    train = task.get("train", [])
    test_in = task.get("test", [{}])[0].get("input", [[0]])

    # 1. Indicator Box Framing Hypothesis
    ind_match = True
    for p in train:
        extracted = extract_subgrid_by_indicator(p.get("input", []))
        if extracted != p.get("output", []):
            ind_match = False
            break
    if ind_match and len(train) > 0:
        res = extract_subgrid_by_indicator(test_in)
        if res:
            return res

    # 2. Standard 2-Depth Symbolic DSL Synthesis
    return synth.synthesize(task)

def main():
    print("\n" + "=" * 105)
    print("🔥 REAL GROUND-TRUTH ARC BENCHMARK WITH ADVANCED SUBGRID ISOLATION")
    print("=" * 105)

    challenges_path = "data/kaggle/arc2/arc-agi_evaluation_challenges.json"
    solutions_path = "data/kaggle/arc2/arc-agi_evaluation_solutions.json"

    with open(challenges_path, "r", encoding="utf-8") as f:
        challenges = json.load(f)
    with open(solutions_path, "r", encoding="utf-8") as f:
        solutions = json.load(f)

    synth = ARCDSLSynthesizer()
    total = len(challenges)
    solved = 0
    t0 = time.perf_counter()

    for idx, (tid, tdata) in enumerate(challenges.items(), 1):
        gt = solutions.get(tid, [[]])[0]
        try:
            pred = dynamic_solve_task(tdata, synth)
            if pred == gt:
                solved += 1
                print(f"  [Task {idx:03d}/{total}] 🟢 EXACT SOLVE: `{tid}`")
        except Exception:
            pass

    dt = time.perf_counter() - t0
    print("\n" + "-" * 105)
    print(f"• Total Tasks Tested : {total}")
    print(f"• Exact Ground Truth : {solved} / {total} ({(solved/total)*100:.2f}%)")
    print(f"• Runtime Duration   : {dt:.2f}s ({total/dt:.1f} tasks/sec)")
    print("=" * 105 + "\n")

if __name__ == "__main__":
    main()
