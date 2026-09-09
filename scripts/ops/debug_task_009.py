import json
import numpy as np

with open("data/arc_prize/arc-agi_training_challenges.json") as f: challenges = json.load(f)
task = challenges["009d5c81"]

for i, ex in enumerate(task["train"]):
    inp, out = np.array(ex["input"]), np.array(ex["output"])
    in_colors = set(np.unique(inp)) - {0}
    out_colors = set(np.unique(out)) - {0}
    disappeared = in_colors - out_colors
    print(f"Train {i}: in_colors={in_colors}, out_colors={out_colors}, disappeared={disappeared}")
