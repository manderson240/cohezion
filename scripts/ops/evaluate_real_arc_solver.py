#!/usr/bin/env python3
"""Run real DSL program synthesis search on ARC evaluation tasks."""

import json
import time
import sys
from pathlib import Path

sys.path.insert(0, "src/cohezion/competition")
import arc_solver

CHALLENGES_PATH = "data/arc_prize/arc-agi_training_challenges.json"
SOLUTIONS_PATH = "data/arc_prize/arc-agi_training_solutions.json"

def evaluate_real_dsl_solver(num_tasks=25):
    print("\n" + "=" * 115)
    print("🧩 EVALUATING REAL ARC-SOLVER DSL SYNTHESIZER ON 25 REAL ARC TASKS (AMD SILICON)")
    print("=" * 115)

    with open(CHALLENGES_PATH) as f:
        challenges = json.load(f)
    with open(SOLUTIONS_PATH) as f:
        solutions = json.load(f)

    task_ids = list(challenges.keys())[:num_tasks]
    solved = 0
    total = 0
    t0 = time.perf_counter()

    for idx, tid in enumerate(task_ids):
        task = challenges[tid]
        sol_list = solutions[tid]
        
        t_start = time.perf_counter()
        program = arc_solver.search_program(task["train"], max_depth=3, budget=3000)
        dt_task = round((time.perf_counter() - t_start) * 1000, 2)

        if program:
            # Check test prediction
            pred = arc_solver.apply_program(arc_solver.deepcopy_grid(task["test"][0]["input"]), program)
            expected = sol_list[0]
            if arc_solver.grids_equal(pred, expected):
                solved += 1
                status = f"✅ SOLVED in {dt_task} ms"
            else:
                status = f"⚠️ Program found but test failed ({dt_task} ms)"
        else:
            status = f"❌ Search exhausted ({dt_task} ms)"

        total += 1
        print(f"  [{idx+1:02d}/{num_tasks:02d}] Task `{tid}`: {status}")

    total_time = round(time.perf_counter() - t0, 2)
    acc = (solved / total) * 100.0

    print("\n" + "=" * 115)
    print(f"📊 REAL ARC-SOLVER RESULTS:")
    print(f"  • Tasks Evaluated: {total}")
    print(f"  • Tasks Solved: {solved}/{total} ({acc:.1f}%)")
    print(f"  • Total Time: {total_time}s ({round(total_time/total*1000, 1)} ms/task)")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    evaluate_real_dsl_solver(25)
