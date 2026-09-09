#!/usr/bin/env python3
"""Multi-Threaded Breadth & Depth ARC Synthesizer on 1,000 Official Tasks."""

import asyncio
import json
import logging
import os
import time
from concurrent.futures import ProcessPoolExecutor
from cohezion.competitions.arc.deep_compositional_solver import DeepCompositionalSynthesizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [ARC_PARALLEL] %(message)s")
logger = logging.getLogger("arc_parallel")

def solve_chunk(tasks_chunk: list[tuple[str, dict, list]]) -> tuple[int, int, list[str]]:
    solver = DeepCompositionalSynthesizer()
    solved = 0
    solved_ids = []
    for tid, tdata, gt in tasks_chunk:
        try:
            pred = solver.solve(tdata)
            if pred == gt:
                solved += 1
                solved_ids.append(tid)
        except Exception:
            pass
    return solved, len(tasks_chunk), solved_ids

async def main():
    print("\n" + "=" * 105)
    print("⚡ PARALLEL BREADTH & DEPTH ARC BENCHMARK (16 CORES / 32 THREADS)")
    print("=" * 105)

    challenges_path = "data/kaggle/arc2/arc-agi_training_challenges.json"
    solutions_path = "data/kaggle/arc2/arc-agi_training_solutions.json"

    with open(challenges_path, "r", encoding="utf-8") as f:
        challenges = json.load(f)
    with open(solutions_path, "r", encoding="utf-8") as f:
        solutions = json.load(f)

    all_tasks = [(tid, tdata, solutions.get(tid, [[]])[0]) for tid, tdata in challenges.items()]
    num_workers = min(16, os.cpu_count() or 4)
    chunk_size = (len(all_tasks) + num_workers - 1) // num_workers
    chunks = [all_tasks[i : i + chunk_size] for i in range(0, len(all_tasks), chunk_size)]

    logger.info("Spawning %d parallel workers across %d total tasks...", len(chunks), len(all_tasks))
    t0 = time.perf_counter()

    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [loop.run_in_executor(executor, solve_chunk, chunk) for chunk in chunks]
        results = await asyncio.gather(*futures)

    dt = time.perf_counter() - t0
    total_solved = sum(r[0] for r in results)
    total_tested = sum(r[1] for r in results)
    all_solved_ids = [tid for r in results for tid in r[2]]
    acc = (total_solved / total_tested) * 100.0

    print("\n" + "-" * 105)
    print("🏆 PARALLEL BREADTH & DEPTH RESULTS")
    print("-" * 105)
    print(f"• Total Tasks Evaluated      : {total_tested}")
    print(f"• Exactly Solved (100% Match): {total_solved} / {total_tested} ({acc:.2f}%)")
    print(f"• Execution Time             : {dt:.2f} seconds ({total_tested / dt:.1f} tasks/sec)")
    print(f"• Solved Task IDs ({len(all_solved_ids)}): {all_solved_ids[:25]}")
    print("=" * 105 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
