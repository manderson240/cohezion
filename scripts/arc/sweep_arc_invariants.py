#!/usr/bin/env python3
"""Cohezion ARC-AGI Invariant & Program Synthesis Sweep.

Mines mathematical & topological invariants and evaluates deterministic
symbolic primitive sequences across ARC training and evaluation sets.
Throttled to 6 workers with os.nice(10) for 100% host responsiveness.
"""

from __future__ import annotations

import os
import sys
import time
import json
import hashlib
from multiprocessing import Pool
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np

try:
    os.nice(10)
except Exception:
    pass


# --- Primitives ---
def p_identity(g):
    return np.copy(g)


def p_rot90(g):
    return np.rot90(g, 1)


def p_rot180(g):
    return np.rot90(g, 2)


def p_rot270(g):
    return np.rot90(g, 3)


def p_fliplr(g):
    return np.fliplr(g)


def p_flipud(g):
    return np.flipud(g)


def p_transpose(g):
    return np.transpose(g)


def p_gravity_down(g):
    res = np.copy(g)
    h, w = res.shape
    for c in range(w):
        col = res[:, c]
        non_zeros = col[col != 0]
        zeros = np.zeros(h - len(non_zeros), dtype=col.dtype)
        res[:, c] = np.concatenate([zeros, non_zeros])
    return res


def p_gravity_up(g):
    res = np.copy(g)
    h, w = res.shape
    for c in range(w):
        col = res[:, c]
        non_zeros = col[col != 0]
        zeros = np.zeros(h - len(non_zeros), dtype=col.dtype)
        res[:, c] = np.concatenate([non_zeros, zeros])
    return res


def p_fill_enclosed_holes(g):
    res = np.copy(g)
    h, w = res.shape
    if h <= 2 or w <= 2:
        return res
    border_colors = set(res[0, :]) | set(res[-1, :]) | set(res[:, 0]) | set(res[:, -1])
    bg = 0 if 0 in border_colors else min(border_colors)
    internal = res[1:-1, 1:-1]
    dominant = int(np.bincount(res.flatten()).argmax())
    res[1:-1, 1:-1] = np.where(internal == 0, dominant, internal)
    return res


PRIMITIVES = {
    "identity": p_identity,
    "rot90": p_rot90,
    "rot180": p_rot180,
    "rot270": p_rot270,
    "fliplr": p_fliplr,
    "flipud": p_flipud,
    "transpose": p_transpose,
    "gravity_down": p_gravity_down,
    "gravity_up": p_gravity_up,
    "fill_enclosed_holes": p_fill_enclosed_holes,
}


def analyze_task(args: tuple[str, dict[str, Any]]) -> dict[str, Any]:
    task_id, task_data = args
    train_pairs = task_data.get("train", [])
    if not train_pairs:
        return {"task_id": task_id, "status": "no_train"}

    # 1. Derive Invariants
    shapes_in = [np.shape(p["input"]) for p in train_pairs]
    shapes_out = [np.shape(p["output"]) for p in train_pairs]

    shape_preserved = all(s_in == s_out for s_in, s_out in zip(shapes_in, shapes_out))

    colors_in = [set(np.unique(p["input"])) for p in train_pairs]
    colors_out = [set(np.unique(p["output"])) for p in train_pairs]
    palette_preserved = all(c_out.issubset(c_in) for c_in, c_out in zip(colors_in, colors_out))

    # 2. Test Primitive Solvers
    solved_by = []
    for prim_name, prim_fn in PRIMITIVES.items():
        matches_all = True
        for p in train_pairs:
            inp = np.array(p["input"])
            out = np.array(p["output"])
            try:
                pred = prim_fn(inp)
                if not np.array_equal(pred, out):
                    matches_all = False
                    break
            except Exception:
                matches_all = False
                break
        if matches_all:
            solved_by.append(prim_name)

    return {
        "task_id": task_id,
        "shape_preserved": shape_preserved,
        "palette_preserved": palette_preserved,
        "train_pairs_count": len(train_pairs),
        "solved_by": solved_by,
        "has_solution": len(solved_by) > 0,
    }


def run_sweep(dataset_path: str, max_workers: int = 6):
    print(f"=== Sweeping ARC Invariants on {dataset_path} ===")
    with open(dataset_path) as f:
        data = json.load(f)
    print(f"Loaded {len(data)} tasks. Workers: {max_workers} (nice=10)")

    start_time = time.time()
    with Pool(processes=max_workers) as pool:
        results = pool.map(analyze_task, list(data.items()))
    duration = time.time() - start_time

    total = len(results)
    shape_preserved_cnt = sum(1 for r in results if r.get("shape_preserved"))
    palette_preserved_cnt = sum(1 for r in results if r.get("palette_preserved"))
    solved_cnt = sum(1 for r in results if r.get("has_solution"))

    solved_details = {r["task_id"]: r["solved_by"] for r in results if r.get("has_solution")}

    summary = {
        "dataset": Path(dataset_path).name,
        "total_tasks": total,
        "shape_preserved_count": shape_preserved_cnt,
        "shape_preserved_pct": f"{100.0 * shape_preserved_cnt / total:.1f}%",
        "palette_preserved_count": palette_preserved_cnt,
        "palette_preserved_pct": f"{100.0 * palette_preserved_cnt / total:.1f}%",
        "fully_solved_by_single_primitive": solved_cnt,
        "fully_solved_pct": f"{100.0 * solved_cnt / total:.1f}%",
        "duration_sec": f"{duration:.2f}s",
        "tasks_per_sec": f"{total / max(duration, 0.001):.1f}",
        "sample_solved_tasks": list(solved_details.items())[:10],
    }

    out_file = Path("data/arc_synthesis") / f"sweep_{Path(dataset_path).stem}.json"
    with open(out_file, "w") as f:
        json.dump(
            {"summary": summary, "solved_tasks": solved_details, "all_results": results},
            f,
            indent=2,
        )
    print(json.dumps(summary, indent=2))
    print(f"✓ Full report saved to {out_file}")
    return summary


if __name__ == "__main__":
    train_path = "archives/backups/tools/kaggle-skill/data/arc-agi_training_challenges.json"
    eval_path = "archives/backups/tools/kaggle-skill/data/arc-agi_evaluation_challenges.json"
    if os.path.exists(eval_path):
        run_sweep(eval_path)
    if os.path.exists(train_path):
        run_sweep(train_path)
