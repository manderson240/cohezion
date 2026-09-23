import time
import statistics
import importlib.util
from pathlib import Path
from kaggle_environments import make

def load_agent(filepath):
    spec = importlib.util.spec_from_file_location("agent_mod_" + str(abs(hash(filepath))), filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent

def test_matchups():
    print("Loading agents...")
    p_gm = "scripts/kaggle/kaggriculture_kernel/main_GM_41ROUTE.py"
    p_sota = "scripts/kaggle/kaggriculture_kernel/main_SOTA_2945.py"
    
    agent_gm = load_agent(p_gm)
    agent_sota = load_agent(p_sota)
    
    print("Running Head-to-Head: GM 41-Route vs SOTA 2945 (4 seeds, both seats)...")
    seeds = [100, 2945, 42, 7]
    gm_w = sota_w = ties = errs = 0
    scores_gm = []
    scores_sota = []
    
    for sd in seeds:
        # Seat 0: GM, Seat 1: SOTA
        env = make('kaggriculture', configuration={'seed': sd}, debug=True)
        env.run([agent_gm, agent_sota])
        last = env.steps[-1]
        for s in last:
            if s.status not in ("DONE", "ACTIVE", "INACTIVE"):
                errs += 1
        r_gm, r_sota = last[0].reward, last[1].reward
        scores_gm.append(r_gm)
        scores_sota.append(r_sota)
        if r_gm > r_sota:
            gm_w += 1
            res = "GM win"
        elif r_sota > r_gm:
            sota_w += 1
            res = "SOTA win"
        else:
            ties += 1
            res = "Tie"
        print(f"Seed {sd} (GM seat 0): GM={r_gm:.0f} vs SOTA={r_sota:.0f} -> {res}")
        
        # Seat 0: SOTA, Seat 1: GM
        env = make('kaggriculture', configuration={'seed': sd}, debug=True)
        env.run([agent_sota, agent_gm])
        last = env.steps[-1]
        for s in last:
            if s.status not in ("DONE", "ACTIVE", "INACTIVE"):
                errs += 1
        r_sota, r_gm = last[0].reward, last[1].reward
        scores_gm.append(r_gm)
        scores_sota.append(r_sota)
        if r_gm > r_sota:
            gm_w += 1
            res = "GM win"
        elif r_sota > r_gm:
            sota_w += 1
            res = "SOTA win"
        else:
            ties += 1
            res = "Tie"
        print(f"Seed {sd} (GM seat 1): GM={r_gm:.0f} vs SOTA={r_sota:.0f} -> {res}")
        
    print(f"\nSummary across {len(scores_gm)} games:")
    print(f"GM Wins: {gm_w}, SOTA Wins: {sota_w}, Ties: {ties}, Errors: {errs}")
    print(f"GM Mean Reward: {statistics.mean(scores_gm):.1f}")
    print(f"SOTA Mean Reward: {statistics.mean(scores_sota):.1f}")

if __name__ == "__main__":
    test_matchups()
