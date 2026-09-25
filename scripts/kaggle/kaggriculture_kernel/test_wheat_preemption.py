#!/usr/bin/env python3
"""Tests Predatory Morning Wheat Preemption wrapper on Kaggriculture."""

import copy
import statistics
import importlib.util
from kaggle_environments import make

def load_agent(filepath):
    spec = importlib.util.spec_from_file_location("agent_mod_" + str(abs(hash(filepath))), filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent

base_agent = load_agent("scripts/kaggle/kaggriculture_kernel/submission.py")
rival_sota = load_agent("scripts/kaggle/kaggriculture_kernel/main_SOTA_2945.py")
rival_gm = load_agent("scripts/kaggle/kaggriculture_kernel/main_GM_41ROUTE.py")

# Create Predatory Morning Wheat Preemption wrapper
def make_predatory_agent(parent_agent, buy_tranche=3, min_money=600):
    def predatory_agent(observation, configuration=None):
        action = parent_agent(observation, configuration)
        step = int(observation["step"])
        hour = step % 24
        
        # Only consider dawn hours 0-1 when morning inventory opens
        if hour in (0, 1) and step < 648:
            player = int(observation["player"])
            farm = observation["farms"][player]
            money = farm["money"]
            shed = farm["shed"]
            shed_occupancy = sum(shed.values())
            
            # If money is comfortable and shed has room
            if money >= min_money and shed_occupancy <= 90:
                orders = list(action.get("market") or [])
                # Check if we already have wheat orders
                has_wheat = any(len(o) >= 2 and o[1] == "WHEAT" for o in orders)
                if not has_wheat and len(orders) < 9:
                    wheat_inv = int(observation["market"]["inventory"].get("WHEAT", 0))
                    if wheat_inv >= 2:
                        qty = min(buy_tranche, wheat_inv, (100 - shed_occupancy))
                        if qty > 0:
                            # Prepend wheat buy to front-run the morning queue
                            orders = [["BUY_PRODUCT", "WHEAT", qty]] + orders
                            action = dict(action, market=orders)
        return action
    return predatory_agent

predatory_agent_v1 = make_predatory_agent(base_agent, buy_tranche=2, min_money=500)
predatory_agent_v2 = make_predatory_agent(base_agent, buy_tranche=4, min_money=750)

seeds = [42, 100, 7, 2945]
print("=== BENCHMARK: Baseline submission vs SOTA 2945 ===")
base_scores = []
rival_scores = []
for sd in seeds:
    env = make("kaggriculture", configuration={"seed": sd}, debug=False)
    env.run([base_agent, rival_sota])
    r0, r1 = env.steps[-1][0].reward, env.steps[-1][1].reward
    base_scores.append(r0)
    rival_scores.append(r1)
    print(f"Seed {sd}: Base={r0:.0f} vs SOTA={r1:.0f} (delta={r0 - r1:+.0f})")

print(f"Baseline Mean Reward: {statistics.mean(base_scores):.1f} | SOTA Mean: {statistics.mean(rival_scores):.1f} | Mean Delta: {statistics.mean([b - r for b, r in zip(base_scores, rival_scores)]):+.1f}\n")

print("=== BENCHMARK: Predatory v1 (tranche=2) vs SOTA 2945 ===")
p1_scores = []
p1_rival = []
for sd in seeds:
    env = make("kaggriculture", configuration={"seed": sd}, debug=False)
    env.run([predatory_agent_v1, rival_sota])
    r0, r1 = env.steps[-1][0].reward, env.steps[-1][1].reward
    p1_scores.append(r0)
    p1_rival.append(r1)
    print(f"Seed {sd}: PredatoryV1={r0:.0f} vs SOTA={r1:.0f} (delta={r0 - r1:+.0f})")

print(f"PredatoryV1 Mean Reward: {statistics.mean(p1_scores):.1f} | SOTA Mean: {statistics.mean(p1_rival):.1f} | Mean Delta: {statistics.mean([b - r for b, r in zip(p1_scores, p1_rival)]):+.1f}\n")
