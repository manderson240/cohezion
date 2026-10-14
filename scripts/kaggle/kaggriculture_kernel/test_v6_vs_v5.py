#!/usr/bin/env python3
"""Refined v6_opt vs v5 head-to-head test."""

import kaggle_environments
import importlib.util

spec = importlib.util.spec_from_file_location("v5_sub", "scripts/kaggle/kaggriculture_kernel/submission.py")
v5_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v5_mod)
v5_agent = v5_mod.agent

def v6_opt_agent(observation, configuration=None):
    action = v5_agent(observation, configuration)
    try:
        step = int(observation['step'])
        m = action.get("market") or []
        
        # Only freeze SLOW crops that cannot mature even with fertilizer:
        # Melon: 6 days (3 days fertilized = 72 steps). Freeze at step 648 (Day 27+).
        # Tomato: 5 days (2.5 days fertilized = 60 steps). Freeze at step 660.
        filtered_orders = []
        for o in m:
            if not o or len(o) < 2:
                filtered_orders.append(o)
                continue
            op, item = o[0], o[1]
            if op == "BUY_SEED":
                if item == "MELON" and step >= 648:
                    continue
                if item == "TOMATO" and step >= 660:
                    continue
            filtered_orders.append(o)
            
        action = dict(action, market=filtered_orders)
    except Exception:
        pass
    return action

print("Running head-to-head match: v6_opt (Player 0) vs v5 (Player 1)...", flush=True)
env = kaggle_environments.make("kaggriculture")
env.run([v6_opt_agent, v5_agent])

r0 = env.state[0].reward
r1 = env.state[1].reward
print(f"Results: v6_opt reward = {r0:.1f} | v5 reward = {r1:.1f}")
print(f"Delta: {r0 - r1:+.1f} coins for v6_opt!")
