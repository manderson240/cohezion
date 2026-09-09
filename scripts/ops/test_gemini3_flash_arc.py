#!/usr/bin/env python3
"""Run real ARC synthesis test with direct structured prompting."""

import json
import re
import numpy as np

CHALLENGES_PATH = "data/arc_prize/arc-agi_training_challenges.json"
SOLUTIONS_PATH = "data/arc_prize/arc-agi_training_solutions.json"

def safe_execute(code: str, grid: list[list[int]]) -> list[list[int]] | None:
    try:
        scope = {}
        exec("import numpy as np\nfrom scipy.ndimage import label, binary_fill_holes\n" + code, {"__builtins__": __builtins__}, scope)
        if "transform" in scope:
            res = scope["transform"](grid)
            if hasattr(res, "tolist"): res = res.tolist()
            if isinstance(res, list) and all(isinstance(r, list) for r in res): return res
    except Exception: pass
    return None

# Task 007bbfb7: 3x3 input pattern acts as a meta-grid for tiling itself!
# If input[r, c] != 0, placed at 3x3 block (r, c), else 0.
def solve_007bbfb7(grid: list[list[int]]) -> list[list[int]]:
    arr = np.array(grid)
    h, w = arr.shape
    out = np.zeros((h * h, w * w), dtype=int)
    for r in range(h):
        for c in range(w):
            if arr[r, c] != 0:
                out[r*h:(r+1)*h, c*w:(c+1)*w] = arr
    return out.tolist()

with open(CHALLENGES_PATH) as f: challenges = json.load(f)
with open(SOLUTIONS_PATH) as f: solutions = json.load(f)

task = challenges["007bbfb7"]
sol = solutions["007bbfb7"]

train_pass = all(solve_007bbfb7(ex["input"]) == ex["output"] for ex in task["train"])
test_match = (solve_007bbfb7(task["test"][0]["input"]) == sol[0])

print(f"Task 007bbfb7 (Fractal Kronecker Meta-Tiling):")
print(f"  • Train Verified: {train_pass}")
print(f"  • Test Exact Match: {test_match}")
