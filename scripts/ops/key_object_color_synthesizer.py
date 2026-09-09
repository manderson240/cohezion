#!/usr/bin/env python3
"""Key-Object Shape Indexing & Inductive Recolor Synthesizer for ARC-AGI."""

import json
import time
import numpy as np

CHALLENGES_PATH = "data/arc_prize/arc-agi_training_challenges.json"
SOLUTIONS_PATH = "data/arc_prize/arc-agi_training_solutions.json"

def get_canonical_shape_bytes(arr: np.ndarray, color: int):
    rows, cols = np.where(arr == color)
    if len(rows) == 0:
        return None
    crop = (arr[rows.min():rows.max()+1, cols.min():cols.max()+1] == color).astype(np.uint8)
    return crop.tobytes()

def synthesize_key_object_recolor(train_pairs):
    """Detects tasks where a small 'key' object controls the recoloring of the main foreground object."""
    shape_to_color = {}
    
    # 1. Identify which input color is the persistent structure vs. the key
    tr_in = [np.array(ex["input"]) for ex in train_pairs]
    tr_out = [np.array(ex["output"]) for ex in train_pairs]
    
    # Check if all pairs have 2 non-zero input colors and 1 non-zero output color
    for inp, out in zip(tr_in, tr_out):
        if len(set(np.unique(inp)) - {0}) != 2 or len(set(np.unique(out)) - {0}) != 1:
            return None

    # Usually, the smaller pixel count is the key object
    key_colors = []
    main_colors = []
    
    for inp, out in zip(tr_in, tr_out):
        c1, c2 = list(set(np.unique(inp)) - {0})
        cnt1 = np.sum(inp == c1)
        cnt2 = np.sum(inp == c2)
        if cnt1 < cnt2:
            kc, mc = c1, c2
        else:
            kc, mc = c2, c1
            
        key_colors.append(kc)
        main_colors.append(mc)
        out_col = list(set(np.unique(out)) - {0})[0]
        
        s_bytes = get_canonical_shape_bytes(inp, kc)
        if s_bytes is None:
            return None
            
        if s_bytes in shape_to_color and shape_to_color[s_bytes] != out_col:
            return None
        shape_to_color[s_bytes] = int(out_col)

    def solve(grid):
        arr = np.array(grid)
        in_cols = list(set(np.unique(arr)) - {0})
        if len(in_cols) < 2:
            return arr.tolist()
            
        c1, c2 = in_cols[0], in_cols[1]
        cnt1 = np.sum(arr == c1)
        cnt2 = np.sum(arr == c2)
        kc, mc = (c1, c2) if cnt1 < cnt2 else (c2, c1)
        
        s_bytes = get_canonical_shape_bytes(arr, kc)
        target_color = shape_to_color.get(s_bytes)
        
        if target_color is None:
            # Fallback to nearest/first mapped color
            target_color = list(shape_to_color.values())[0]
            
        out_arr = np.zeros_like(arr)
        out_arr[arr == mc] = target_color
        return out_arr.tolist()

    if all(solve(ex["input"]) == ex["output"] for ex in train_pairs):
        return solve

    return None

def run_key_object_benchmark():
    with open(CHALLENGES_PATH) as f: challenges = json.load(f)
    with open(SOLUTIONS_PATH) as f: solutions = json.load(f)

    solved = 0
    total = len(challenges)
    t0 = time.perf_counter()

    for tid, task in challenges.items():
        prog = synthesize_key_object_recolor(task["train"])
        if prog:
            pred = prog(task["test"][0]["input"])
            expected = solutions[tid][0]
            if pred == expected:
                solved += 1

    dt = round(time.perf_counter() - t0, 3)
    print(f"📊 Key-Object Inductive Synthesizer Results: Solved {solved}/{total} ({solved/total*100:.2f}%) in {dt}s")

if __name__ == "__main__":
    run_key_object_benchmark()
