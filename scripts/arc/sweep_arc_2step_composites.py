#!/usr/bin/env python3
"""Cohezion ARC-AGI 2-Step Composite Program Synthesis Sweep.

Evaluates 2-step composite symbolic primitive pipelines f2(f1(x)) across
ARC training and evaluation tasks to discover automated deterministic solvers.
Throttled to 6 workers with os.nice(10) for 100% host responsiveness.
"""

from __future__ import annotations

import os
import sys
import time
import json
import itertools
from multiprocessing import Pool
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple
import numpy as np

try:
    os.nice(10)
except Exception:
    pass


# --- Atomic Primitives ---
def p_identity(g: np.ndarray) -> np.ndarray:
    return np.copy(g)


def p_rot90(g: np.ndarray) -> np.ndarray:
    return np.rot90(g, 1)


def p_rot180(g: np.ndarray) -> np.ndarray:
    return np.rot90(g, 2)


def p_rot270(g: np.ndarray) -> np.ndarray:
    return np.rot90(g, 3)


def p_fliplr(g: np.ndarray) -> np.ndarray:
    return np.fliplr(g)


def p_flipud(g: np.ndarray) -> np.ndarray:
    return np.flipud(g)


def p_transpose(g: np.ndarray) -> np.ndarray:
    return np.transpose(g)


def p_gravity_down(g: np.ndarray) -> np.ndarray:
    res = np.copy(g)
    h, w = res.shape
    for c in range(w):
        col = res[:, c]
        non_zeros = col[col != 0]
        zeros = np.zeros(h - len(non_zeros), dtype=col.dtype)
        res[:, c] = np.concatenate([zeros, non_zeros])
    return res


def p_gravity_up(g: np.ndarray) -> np.ndarray:
    res = np.copy(g)
    h, w = res.shape
    for c in range(w):
        col = res[:, c]
        non_zeros = col[col != 0]
        zeros = np.zeros(h - len(non_zeros), dtype=col.dtype)
        res[:, c] = np.concatenate([non_zeros, zeros])
    return res


def p_gravity_left(g: np.ndarray) -> np.ndarray:
    res = np.copy(g)
    h, w = res.shape
    for r in range(h):
        row = res[r, :]
        non_zeros = row[row != 0]
        zeros = np.zeros(w - len(non_zeros), dtype=row.dtype)
        res[r, :] = np.concatenate([non_zeros, zeros])
    return res


def p_gravity_right(g: np.ndarray) -> np.ndarray:
    res = np.copy(g)
    h, w = res.shape
    for r in range(h):
        row = res[r, :]
        non_zeros = row[row != 0]
        zeros = np.zeros(w - len(non_zeros), dtype=row.dtype)
        res[r, :] = np.concatenate([zeros, non_zeros])
    return res


def p_crop_bbox(g: np.ndarray) -> np.ndarray:
    non_zero_coords = np.argwhere(g != 0)
    if non_zero_coords.size == 0:
        return g
    min_r, min_c = non_zero_coords.min(axis=0)
    max_r, max_c = non_zero_coords.max(axis=0) + 1
    return g[min_r:max_r, min_c:max_c]


def p_fill_enclosed_holes(g: np.ndarray) -> np.ndarray:
    res = np.copy(g)
    h, w = res.shape
    if h <= 2 or w <= 2:
        return res
    internal = res[1:-1, 1:-1]
    counts = np.bincount(res.flatten())
    if len(counts) > 1:
        dominant = int(counts[1:].argmax() + 1)
        res[1:-1, 1:-1] = np.where(internal == 0, dominant, internal)
    return res


def p_upscale_2x(g: np.ndarray) -> np.ndarray:
    return np.repeat(np.repeat(g, 2, axis=0), 2, axis=1)


def p_upscale_3x(g: np.ndarray) -> np.ndarray:
    return np.repeat(np.repeat(g, 3, axis=0), 3, axis=1)


def p_invert_colors(g: np.ndarray) -> np.ndarray:
    res = np.copy(g)
    colors = [c for c in np.unique(res) if c != 0]
    if len(colors) == 1:
        res = np.where(res == colors[0], 0, colors[0])
    elif len(colors) == 2:
        c1, c2 = colors
        mask1 = res == c1
        mask2 = res == c2
        res[mask1] = c2
        res[mask2] = c1
    return res


PRIMITIVES: dict[str, Callable[[np.ndarray], np.ndarray]] = {
    "identity": p_identity,
    "rot90": p_rot90,
    "rot180": p_rot180,
    "rot270": p_rot270,
    "fliplr": p_fliplr,
    "flipud": p_flipud,
    "transpose": p_transpose,
    "gravity_down": p_gravity_down,
    "gravity_up": p_gravity_up,
    "gravity_left": p_gravity_left,
    "gravity_right": p_gravity_right,
    "crop_bbox": p_crop_bbox,
    "fill_enclosed_holes": p_fill_enclosed_holes,
    "upscale_2x": p_upscale_2x,
    "upscale_3x": p_upscale_3x,
    "invert_colors": p_invert_colors,
}

# Precompute 2-step primitive pairs
PAIR_KEYS = []
# 1-step first
for k in PRIMITIVES:
    PAIR_KEYS.append((k, "identity"))
# 2-step distinct pairs
for k1 in PRIMITIVES:
    if k1 == "identity":
        continue
    for k2 in PRIMITIVES:
        if k2 == "identity":
            continue
        PAIR_KEYS.append((k1, k2))


def evaluate_task_2step(args: tuple[str, dict[str, Any]]) -> dict[str, Any]:
    task_id, task_data = args
    train_pairs = task_data.get("train", [])
    if not train_pairs:
        return {"task_id": task_id, "status": "no_train"}

    inputs = [np.array(p["input"]) for p in train_pairs]
    outputs = [np.array(p["output"]) for p in train_pairs]

    solved_by = []

    for k1, k2 in PAIR_KEYS:
        fn1 = PRIMITIVES[k1]
        fn2 = PRIMITIVES[k2]
        matches = True

        for inp, out in zip(inputs, outputs):
            try:
                mid = fn1(inp)
                pred = fn2(mid)
                if pred.shape != out.shape or not np.array_equal(pred, out):
                    matches = False
                    break
            except Exception:
                matches = False
                break

        if matches:
            prog_name = k1 if k2 == "identity" else f"{k1} -> {k2}"
            solved_by.append(prog_name)

    return {
        "task_id": task_id,
        "train_pairs_count": len(train_pairs),
        "solved_by": solved_by,
        "has_solution": len(solved_by) > 0,
    }


def run_composite_sweep(dataset_path: str, max_workers: int = 6):
    print(f"=== Sweeping ARC 2-Step Composites on {dataset_path} ===")
    with open(dataset_path) as f:
        data = json.load(f)
    print(
        f"Loaded {len(data)} tasks. Pairs to evaluate: {len(PAIR_KEYS)}. Workers: {max_workers} (nice=10)"
    )

    start_time = time.time()
    with Pool(processes=max_workers) as pool:
        results = pool.map(evaluate_task_2step, list(data.items()))
    duration = time.time() - start_time

    total = len(results)
    solved_cnt = sum(1 for r in results if r.get("has_solution"))
    solved_details = {r["task_id"]: r["solved_by"] for r in results if r.get("has_solution")}

    summary = {
        "dataset": Path(dataset_path).name,
        "total_tasks": total,
        "pair_space_size": len(PAIR_KEYS),
        "solved_count": solved_cnt,
        "solved_pct": f"{100.0 * solved_cnt / total:.2f}%",
        "duration_sec": f"{duration:.2f}s",
        "tasks_per_sec": f"{total / max(duration, 0.001):.1f}",
        "sample_solutions": list(solved_details.items())[:15],
    }

    out_dir = Path("data/arc_synthesis")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"sweep_2step_{Path(dataset_path).stem}.json"
    with open(out_file, "w") as f:
        json.dump(
            {"summary": summary, "solved_tasks": solved_details, "all_results": results},
            f,
            indent=2,
        )

    print(json.dumps(summary, indent=2))
    print(f"✓ Composite report saved to {out_file}")
    return summary


if __name__ == "__main__":
    eval_path = "archives/backups/tools/kaggle-skill/data/arc-agi_evaluation_challenges.json"
    train_path = "archives/backups/tools/kaggle-skill/data/arc-agi_training_challenges.json"

    if os.path.exists(eval_path):
        run_composite_sweep(eval_path)
    if os.path.exists(train_path):
        run_composite_sweep(train_path)
