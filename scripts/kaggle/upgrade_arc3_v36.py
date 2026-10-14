"""Script to upgrade cohezion-arc-agi-3-autoharness-solver.ipynb to SOTA v36."""

import json
from pathlib import Path

nb_path = Path("scripts/kaggle/cohezion-arc-agi-3-autoharness-solver/cohezion-arc-agi-3-autoharness-solver.ipynb")
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# 1. Update Cell 1
cell1 = "".join(nb["cells"][1]["source"])
cell1 = cell1.replace("Cohezion ARC-AGI-3 SOTA v35", "Cohezion ARC-AGI-3 SOTA v36")
cell1 = cell1.replace("max_evals = 200", "max_evals = 600")

old_action_logic = """                # Soft-Affordance BFS advice bonus
                if grid is not None:
                    suggested_act = soft_bfs_suggested_action(grid, (pr, pc), (tr, tc), bg_color)
                    if suggested_act and suggested_act in preferred_scores:
                        preferred_scores[suggested_act] -= 15.0"""

new_action_logic = """                # Soft-Affordance BFS advice bonus
                if grid is not None:
                    suggested_act = soft_bfs_suggested_action(grid, (pr, pc), (tr, tc), bg_color)
                    if suggested_act and suggested_act in preferred_scores:
                        preferred_scores[suggested_act] -= 15.0

                # Action 5 (Interact/Push) proximity bonus when adjacent to affordance component
                if 5 in preferred_scores and (abs(dr) + abs(dc)) <= 1:
                    preferred_scores[5] -= 16.0"""

if old_action_logic in cell1:
    cell1 = cell1.replace(old_action_logic, new_action_logic)
    print("✓ Cell 1: Action 5 proximity bonus injected.")
else:
    print("⚠️ Cell 1: old_action_logic not matched exactly.")

old_cycle_logic = """            action_penalties = {}
            for act_id in simple_ids:"""

new_cycle_logic = """            action_penalties = {}
            untried = [a for a in simple_ids if a not in known]
            for act_id in simple_ids:"""

if old_cycle_logic in cell1:
    cell1 = cell1.replace(old_cycle_logic, new_cycle_logic)
    print("✓ Cell 1: Untried set defined.")

old_penalty_end = """                # Frequency of (s, a) execution penalty
                sa_count = self.state_action_visits.get((curr_hash, act_id), 0)
                penalty += 1.5 * sa_count"""

new_penalty_end = """                # Frequency of (s, a) execution penalty
                sa_count = self.state_action_visits.get((curr_hash, act_id), 0)
                penalty += 1.5 * sa_count

                # Orthogonal escape pulse on stubborn cycles
                if is_cycle and self.consecutive_loops >= 3 and act_id in untried:
                    penalty -= 80.0"""

if old_penalty_end in cell1:
    cell1 = cell1.replace(old_penalty_end, new_penalty_end)
    print("✓ Cell 1: Orthogonal escape pulse injected.")

nb["cells"][1]["source"] = [line + "\n" for line in cell1.splitlines()]

# 2. Update Cell 2
cell2 = "".join(nb["cells"][2]["source"])
cell2 = cell2.replace("step < 35", "step < 75")
cell2 = cell2.replace('getattr(agent, "consecutive_loops", 0) >= 4', 'getattr(agent, "consecutive_loops", 0) >= 8')
cell2 = cell2.replace("4 consecutive cycle traps", "8 consecutive cycle traps")
cell2 = cell2.replace("SOTA v32: RHAE 35-Step Cap", "SOTA v36: 75-Step Dynamic Horizon")
nb["cells"][2]["source"] = [line + "\n" for line in cell2.splitlines()]
print("✓ Cell 2: Step cap raised to 75 and watchdog loosened to 8.")

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)
print("✓ Saved upgraded notebook successfully.")
