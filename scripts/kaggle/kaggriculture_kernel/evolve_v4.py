#!/usr/bin/env python3
"""Local 16-core CPU Tournament to evolve Kaggriculture main_PLANNER_v4.py."""

from __future__ import annotations
import sys
import json
from pathlib import Path
from multiprocessing import Pool
import statistics
import time

base_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(base_dir))

from evolve_planner import load_agent, play_match

def run_experiment(name: str, cand_agent_path: str, baseline_path: str, num_seeds: int = 8, workers: int = 16):
    print(f"\n▶ Testing candidate [{name}] against baseline [{Path(baseline_path).name}]...")
    tasks = []
    for seed in range(num_seeds):
        tasks.append((cand_agent_path, baseline_path, seed, 0))
        tasks.append((cand_agent_path, baseline_path, seed, 1))
        
    t0 = time.perf_counter()
    with Pool(processes=workers) as pool:
        results = pool.map(play_match, tasks)
    elapsed = time.perf_counter() - t0
    
    rewards_cand = [r[1] for r in results]
    rewards_base = [r[2] for r in results]
    wins = sum(1 for r in results if r[1] > r[2])
    losses = sum(1 for r in results if r[2] > r[1])
    ties = sum(1 for r in results if r[1] == r[2])
    win_rate = wins / len(results)
    mean_cand = statistics.mean(rewards_cand)
    mean_base = statistics.mean(rewards_base)
    delta = mean_cand - mean_base
    
    print(f"[{name}] Matches: {len(results)} | Wins: {wins} | Losses: {losses} | Ties: {ties} | Win Rate: {win_rate*100:.1f}%")
    print(f"[{name}] Mean Reward: {mean_cand:.1f} vs Baseline: {mean_base:.1f} (Δ {delta:+.1f}) | Elapsed: {elapsed:.2f}s")
    return {
        "name": name,
        "win_rate": win_rate,
        "delta": delta,
        "mean_cand": mean_cand,
        "mean_base": mean_base
    }

if __name__ == "__main__":
    v3_path = str(base_dir / "main_PLANNER_v3.py")
    livestock_path = str(base_dir / "main_LIVESTOCK.py")
    res = run_experiment("v3_vs_livestock", v3_path, livestock_path, num_seeds=10, workers=16)
