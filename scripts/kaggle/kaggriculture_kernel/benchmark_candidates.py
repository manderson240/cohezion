#!/usr/bin/env python3
"""Evaluate candidate parameter sets for main_PLANNER_v3."""

import os, time, json, statistics, importlib.util, copy
from multiprocessing import Pool
from pathlib import Path

try:
    os.nice(10)
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent

# Load base main_PLANNER_v2 module
spec = importlib.util.spec_from_file_location("planner_v2", str(BASE_DIR / "main_PLANNER_v2.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Load baseline LIVESTOCK
spec_l = importlib.util.spec_from_file_location("livestock", str(BASE_DIR / "main_LIVESTOCK.py"))
mod_l = importlib.util.module_from_spec(spec_l)
spec_l.loader.exec_module(mod_l)
LIVESTOCK_AGENT = mod_l.agent

CANDIDATES = {
    "v2_baseline": {"care": True, "num_cows": 4},
    "v3_early_hire": {
        "care": True,
        "num_cows": 4,
        "hire_tiers": [(600, 5), (250, 3), (100, 1)],
        "cash_floor": 100,
    },
    "v3_scale_6hands": {
        "care": True,
        "num_cows": 4,
        "hire_tiers": [(800, 6), (350, 4), (150, 2)],
        "max_hands_seed": 8,
    },
    "v3_deep_wheat": {"care": True, "num_cows": 4, "wheat_buffer_mult": 3, "cash_floor": 120},
    "v3_cow5_deep_wheat": {"care": True, "num_cows": 5, "wheat_buffer_mult": 3, "cash_floor": 180},
}


def create_agent_with_P(P_override):
    P = mod._p_of(P_override)

    def custom_agent(obs):
        return mod.controller(obs, P)

    return custom_agent


def evaluate_match(args):
    from kaggle_environments import make

    cand_name, P_dict, seed, seat = args
    agent_cand = create_agent_with_P(P_dict)

    players = [agent_cand, LIVESTOCK_AGENT] if seat == 0 else [LIVESTOCK_AGENT, agent_cand]
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run(players)

    reward_cand = env.steps[-1][seat].reward
    reward_base = env.steps[-1][1 - seat].reward
    return cand_name, reward_cand, reward_base


def run():
    seeds = list(range(10))  # 10 seeds x 2 seats = 20 games per candidate
    tasks = []
    for c_name, c_p in CANDIDATES.items():
        for s in seeds:
            tasks.append((c_name, c_p, s, 0))
            tasks.append((c_name, c_p, s, 1))

    print(f"Starting evaluation of {len(CANDIDATES)} candidates over {len(tasks)} total matches...")
    t0 = time.time()
    with Pool(processes=6) as p:
        results = p.map(evaluate_match, tasks)
    dt = time.time() - t0

    by_cand = {}
    for c_name, r_c, r_b in results:
        by_cand.setdefault(c_name, []).append((r_c, r_b))

    summary = {}
    for c_name, scores in by_cand.items():
        c_scores = [s[0] for s in scores]
        b_scores = [s[1] for s in scores]
        wins = sum(1 for s in scores if s[0] > s[1])
        summary[c_name] = {
            "win_rate": f"{100.0 * wins / len(scores):.1f}%",
            "mean_reward": round(statistics.mean(c_scores), 1),
            "min_reward": min(c_scores),
            "max_reward": max(c_scores),
            "advantage_over_baseline": round(
                statistics.mean(c_scores) - statistics.mean(b_scores), 1
            ),
        }
    print(json.dumps(summary, indent=2))
    print(f"Completed {len(tasks)} games in {dt:.2f}s ({len(tasks) / dt:.2f} games/s)")


if __name__ == "__main__":
    run()
