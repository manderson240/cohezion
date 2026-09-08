#!/usr/bin/env python3
"""Kaggriculture Parallel Tournament & Macro-Strategy Evolve Engine.

Evaluates candidate livestock & farmhand macro-strategies against
main_LIVESTOCK baseline across multiple deterministic seeds using Python multiprocessing.
Throttled to 6 workers with os.nice(10) to preserve 100% desktop responsiveness.
"""

from __future__ import annotations

import os
import time
import json
import statistics
import importlib.util
from multiprocessing import Pool
from pathlib import Path

try:
    os.nice(10)
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent

def load_agent(filepath: str):
    spec = importlib.util.spec_from_file_location(f"mod_{abs(hash(filepath))}", filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent

def play_match(args: tuple[str, str, int, int]) -> tuple[int, float, float, int]:
    path_a, path_b, seed, seat_a = args
    from kaggle_environments import make
    
    agent_a = load_agent(path_a)
    agent_b = load_agent(path_b)
    
    players = [agent_a, agent_b] if seat_a == 0 else [agent_b, agent_a]
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run(players)
    
    last = env.steps[-1]
    errs = sum(1 for s in last if s.status not in ("DONE", "ACTIVE", "INACTIVE"))
    
    reward_a = last[seat_a].reward
    reward_b = last[1 - seat_a].reward
    
    return seed, reward_a, reward_b, errs

def run_tournament(agent_a_path: str, baseline_path: str, num_seeds: int = 12, max_workers: int = 6):
    print(f"=== Running Kaggriculture Tournament ({Path(agent_a_path).name} vs {Path(baseline_path).name}) ===")
    print(f"Seeds: {num_seeds} | Workers: {max_workers} (nice=10)")
    
    tasks = []
    for seed in range(num_seeds):
        tasks.append((agent_a_path, baseline_path, seed, 0))
        tasks.append((agent_a_path, baseline_path, seed, 1))
        
    start_time = time.time()
    with Pool(processes=max_workers) as pool:
        results = pool.map(play_match, tasks)
        
    duration = time.time() - start_time
    
    rewards_a = [r[1] for r in results]
    rewards_b = [r[2] for r in results]
    total_errors = sum(r[3] for r in results)
    
    wins_a = sum(1 for r in results if r[1] > r[2])
    wins_b = sum(1 for r in results if r[2] > r[1])
    ties = sum(1 for r in results if r[1] == r[2])
    
    summary = {
        "agent": Path(agent_a_path).name,
        "baseline": Path(baseline_path).name,
        "matches": len(results),
        "wins_a": wins_a,
        "wins_b": wins_b,
        "ties": ties,
        "win_rate": wins_a / len(results),
        "mean_reward_a": statistics.mean(rewards_a),
        "mean_reward_b": statistics.mean(rewards_b),
        "min_reward_a": min(rewards_a),
        "max_reward_a": max(rewards_a),
        "errors": total_errors,
        "duration_sec": duration,
        "matches_per_sec": len(results) / max(duration, 0.001)
    }
    
    print(json.dumps(summary, indent=2))
    return summary

if __name__ == "__main__":
    v2_path = str(BASE_DIR / "main_PLANNER_v2.py")
    livestock_path = str(BASE_DIR / "main_LIVESTOCK.py")
    run_tournament(v2_path, livestock_path, num_seeds=12, max_workers=6)
