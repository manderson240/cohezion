import json
import numpy as np

CHALLENGES_PATH = "data/arc_prize/arc-agi_training_challenges.json"
SOLUTIONS_PATH = "data/arc_prize/arc-agi_training_solutions.json"

with open(CHALLENGES_PATH) as f: challenges = json.load(f)
with open(SOLUTIONS_PATH) as f: solutions = json.load(f)

task = challenges["009d5c81"]
sol = solutions["009d5c81"]

for i, ex in enumerate(task["train"]):
    inp = np.array(ex["input"])
    out = np.array(ex["output"])
    rows, cols = np.where(inp == 1)
    bbox = (inp[rows.min():rows.max()+1, cols.min():cols.max()+1] == 1).astype(int)
    print(f"Train {i} Blue Shape:\n{bbox}\nOutput Color: {np.unique(out[out != 0])}\n")

# Test shape
inp_test = np.array(task["test"][0]["input"])
rows, cols = np.where(inp_test == 1)
bbox_test = (inp_test[rows.min():rows.max()+1, cols.min():cols.max()+1] == 1).astype(int)
print(f"Test Blue Shape:\n{bbox_test}\n")
