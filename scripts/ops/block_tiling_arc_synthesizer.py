#!/usr/bin/env python3
"""Block-Tiling & Alternating Reflection Synthesizer for ARC-AGI."""

import json
import time
import itertools
import numpy as np

CHALLENGES_PATH = "data/arc_prize/arc-agi_training_challenges.json"
SOLUTIONS_PATH = "data/arc_prize/arc-agi_training_solutions.json"

def synthesize_block_tiling_program(train_pairs):
    """Detects 2x2, 3x3, 4x4 block tiling with combinations of (identity, fliplr, flipud, rot90, rot180, rot270, transpose)."""
    tr_in = [np.array(ex["input"]) for ex in train_pairs]
    tr_out = [np.array(ex["output"]) for ex in train_pairs]

    in_h, in_w = tr_in[0].shape
    out_h, out_w = tr_out[0].shape

    # Check if integer multiple tiling
    if out_h % in_h != 0 or out_w % in_w != 0:
        return None

    kh = out_h // in_h
    kw = out_w // in_w

    if kh > 5 or kw > 5:
        return None

    transforms = [
        ("id", lambda x: x),
        ("fliplr", np.fliplr),
        ("flipud", np.flipud),
        ("rot90", lambda x: np.rot90(x, 1)),
        ("rot180", lambda x: np.rot90(x, 2)),
        ("rot270", lambda x: np.rot90(x, 3)),
        ("T", lambda x: x.T if x.shape[0] == x.shape[1] else x)
    ]

    # For each cell in the kh x kw grid, find the transform that holds across all train examples
    grid_transforms = []
    for r in range(kh):
        row_transforms = []
        for c in range(kw):
            matched_tf = None
            for name, tf in transforms:
                try:
                    if all(np.array_equal(tf(inp), out[r*in_h:(r+1)*in_h, c*in_w:(c+1)*in_w]) for inp, out in zip(tr_in, tr_out)):
                        matched_tf = tf
                        break
                except Exception:
                    continue
            if matched_tf is None:
                return None
            row_transforms.append(matched_tf)
        grid_transforms.append(row_transforms)

    def apply_tiling(grid):
        arr = np.array(grid)
        rows_blocks = []
        for r in range(kh):
            row_blocks = [grid_transforms[r][c](arr) for c in range(kw)]
            rows_blocks.append(np.hstack(row_blocks))
        return np.vstack(rows_blocks).tolist()

    return apply_tiling

def run_tiling_benchmark():
    with open(CHALLENGES_PATH) as f: challenges = json.load(f)
    with open(SOLUTIONS_PATH) as f: solutions = json.load(f)

    solved = 0
    total = len(challenges)
    t0 = time.perf_counter()

    for tid, task in challenges.items():
        prog = synthesize_block_tiling_program(task["train"])
        if prog:
            pred = prog(task["test"][0]["input"])
            expected = solutions[tid][0]
            if pred == expected:
                solved += 1

    dt = round(time.perf_counter() - t0, 3)
    print(f"📊 Block-Tiling Synthesizer Results: Solved {solved}/{total} ({solved/total*100:.2f}%) in {dt}s")

if __name__ == "__main__":
    run_tiling_benchmark()
