#!/usr/bin/env python3
"""Kronecker Fractal Meta-Tiling Synthesizer for ARC-AGI."""

import json
import time
import numpy as np

CHALLENGES_PATH = "data/arc_prize/arc-agi_training_challenges.json"
SOLUTIONS_PATH = "data/arc_prize/arc-agi_training_solutions.json"

def synthesize_kronecker_meta_tiler(train_pairs):
    """Detects Kronecker self-similarity fractal expansions (input grid tiles onto non-zero elements of itself)."""
    tr_in = [np.array(ex["input"]) for ex in train_pairs]
    tr_out = [np.array(ex["output"]) for ex in train_pairs]

    in_h, in_w = tr_in[0].shape
    out_h, out_w = tr_out[0].shape

    if out_h != in_h * in_h or out_w != in_w * in_w:
        return None

    def apply_kronecker(grid):
        arr = np.array(grid)
        h, w = arr.shape
        out = np.zeros((h * h, w * w), dtype=int)
        for r in range(h):
            for c in range(w):
                if arr[r, c] != 0:
                    out[r*h:(r+1)*h, c*w:(c+1)*w] = arr
        return out.tolist()

    if all(apply_kronecker(ex["input"]) == ex["output"] for ex in train_pairs):
        return apply_kronecker

    return None

def run_kronecker_benchmark():
    with open(CHALLENGES_PATH) as f: challenges = json.load(f)
    with open(SOLUTIONS_PATH) as f: solutions = json.load(f)

    solved = 0
    total = len(challenges)
    t0 = time.perf_counter()

    for tid, task in challenges.items():
        prog = synthesize_kronecker_meta_tiler(task["train"])
        if prog:
            pred = prog(task["test"][0]["input"])
            expected = solutions[tid][0]
            if pred == expected:
                solved += 1

    dt = round(time.perf_counter() - t0, 3)
    print(f"📊 Kronecker Fractal Synthesizer Results: Solved {solved}/{total} ({solved/total*100:.2f}%) in {dt}s")

if __name__ == "__main__":
    run_kronecker_benchmark()
