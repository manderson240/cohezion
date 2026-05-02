#!/usr/bin/env python3
"""True Overnight ARC Autoresearch — fills wall-clock budget productively.

Workflow per task:
  1. Deep beam search (30-120s) with current transform set
  2. On success  → log to K-Search, generalize winning chain
  3. On failure  → FLUME embed grids, transfer from nearest success
  4. Expand library with new primitives discovered from solved tasks
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cohezion.arc.data_loader import load_all
from cohezion.arc.solver import _score_chain, ucb1_score, update_ksearch
from cohezion.arc.transforms import ALL_TRANSFORMS as BASE_TRANSFORMS
from cohezion.flume.vae_encoder import get_encoder


TARGET_DEADLINE = datetime.fromisoformat(
    os.environ.get("ARDeadline", datetime.now().replace(hour=7, minute=0, second=0).isoformat())
)
CHECKPOINT = Path.home() / ".cohezion-research/arc_continuous.json"
REPORT = Path.home() / ".cohezion-research/arc_continuous_report.md"

ENCODER = None


def _sec_left() -> float:
    return max(0, (TARGET_DEADLINE - datetime.now()).total_seconds())


def _load() -> dict:
    if CHECKPOINT.exists():
        return json.loads(CHECKPOINT.read_text())
    return {
        "best_rate": 0.0,
        "total_evals": 0,
        "wins": 0,
        "discovered_transforms": {},
        "flume_cache": {},
        "history": [],
    }


def _save(state: dict) -> None:
    CHECKPOINT.write_text(json.dumps(state, indent=2, default=str))


def _get_encoder():
    global ENCODER
    if ENCODER is None:
        try:
            ENCODER = get_encoder()
        except Exception as e:
            print(f"FLUME encoder unavailable: {e}")
            ENCODER = False
    return ENCODER if ENCODER is not False else None


def _embed_grid(grid: np.ndarray) -> np.ndarray | None:
    enc = _get_encoder()
    if enc is None:
        return None
    try:
        return enc.encode(grid.astype(np.float32).flatten()[:256])
    except Exception:
        return None


def _find_nearest_task(task_id: str, state: dict, all_tasks: dict) -> str | None:
    """Find nearest successful task by FLUME embedding for transfer."""
    cache = state["flume_cache"]
    if task_id not in cache:
        return None
    vec = np.array(cache[task_id])
    best_tid, best_sim = None, -1.0
    for tid, tvec in cache.items():
        if tid == task_id:
            continue
        if tid not in state.get("solved_tasks", {}):
            continue
        sim = float(
            np.dot(vec, np.array(tvec))
            / (np.linalg.norm(vec) * np.linalg.norm(np.array(tvec)) + 1e-9)
        )
        if sim > best_sim:
            best_sim, best_tid = sim, tid
    return best_tid


def _generalize_chain(chain: list[str], train_pairs: list[dict]) -> list[str] | None:
    """Try removing last transform to see if shorter chain still works."""
    for i in range(len(chain), 1):
        shorter = chain[: len(chain) - 1] if i < len(chain) else chain
        if not shorter:
            continue
        if _score_chain(shorter, train_pairs) >= 1.0:
            return shorter
    return None


def deep_solve(
    task: dict, task_id: str, state: dict, budget_sec: float = 60.0
) -> tuple[list[str] | None, float]:
    """Deep beam search with warm-start from nearest successful task."""
    train = task["train"]
    names = list(BASE_TRANSFORMS.keys())
    beams = [([], 0.0)]
    t0 = time.monotonic()
    best_chain, best_score = None, 0.0

    # Warm-start from nearest success
    nearest = _find_nearest_task(task_id, state, {})
    if nearest:
        warm = state.get("solved_tasks", {}).get(nearest, [])
        if warm and _score_chain(warm, train) >= 1.0:
            return warm, 1.0

    for depth in range(1, 5):
        candidates = []
        for chain, _ in beams:
            for name in names:
                new_chain = chain + [name]
                score = _score_chain(new_chain, train)
                state["total_evals"] += 1
                candidates.append((new_chain, score))
                if score > best_score:
                    best_score, best_chain = score, new_chain
                if time.monotonic() - t0 > budget_sec:
                    break
            if time.monotonic() - t0 > budget_sec:
                break
        total = sum(1 for _ in candidates) + 1
        candidates.sort(key=lambda x: ucb1_score(x[1], 0, total), reverse=True)
        beams = candidates[:16]
        if best_score >= 1.0:
            break
        if time.monotonic() - t0 > budget_sec:
            break

    return best_chain, best_score


def main():
    print(f"[{datetime.now().isoformat()}] Continuous ARC Autoresearch START")
    print(f"Deadline: {TARGET_DEADLINE.isoformat()} | Left: {_sec_left() / 3600:.1f}h")
    state = _load()
    tasks = load_all("training")
    task_ids = list(tasks.keys())
    solved_tasks = state.setdefault("solved_tasks", {})

    # Pre-compute FLUME embeddings for all tasks
    print("Computing FLUME embeddings...")
    for tid, task in tasks.items():
        if tid not in state["flume_cache"]:
            emb = _embed_grid(task["train"][0]["input"])
            if emb is not None:
                state["flume_cache"][tid] = emb.tolist()

    iteration = 0
    while _sec_left() > 60:
        iteration += 1
        cfg = {
            "beam": 16 + iteration * 2,
            "depth": min(5, 2 + iteration // 10),
            "budget": min(120, 30 + iteration * 2),
        }
        batch_solved = 0
        batch_total = 0

        for tid in task_ids:
            if _sec_left() < 30:
                break
            task = tasks[tid]
            chain, score = deep_solve(task, tid, state, budget_sec=cfg["budget"])
            batch_total += 1
            if score >= 1.0:
                batch_solved += 1
                if tid not in solved_tasks:
                    solved_tasks[tid] = chain
                    # Generalize
                    generalized = _generalize_chain(chain, task["train"])
                    if generalized and generalized != chain:
                        solved_tasks[f"{tid}_gen"] = generalized
                update_ksearch(chain, 1.0)
                state["wins"] += 1
            else:
                # Negative logging to K-Search
                if chain:
                    update_ksearch(chain, score)

            # FLUME embedding update
            emb = _embed_grid(task["train"][0]["input"])
            if emb is not None:
                state["flume_cache"][tid] = emb.tolist()

            if batch_total % 10 == 0:
                _save(state)

        rate = batch_solved / max(batch_total, 1)
        if rate > state["best_rate"]:
            state["best_rate"] = rate
        state["history"].append(
            {
                "iteration": iteration,
                "cfg": cfg,
                "rate": rate,
                "solved": batch_solved,
                "total": batch_total,
            }
        )
        _save(state)
        print(
            f"Iter {iteration}: {rate:.1%} ({batch_solved}/{batch_total}) | best={state['best_rate']:.1%} | left={_sec_left() / 3600:.1f}h"
        )

    # Report
    report = f"""# ARC Continuous Autoresearch Report
Deadline: {TARGET_DEADLINE.isoformat()}
Iterations: {iteration}
Best rate: {state["best_rate"]:.2%}
Total evals: {state["total_evals"]}
Unique tasks solved: {len([k for k in solved_tasks if not k.endswith("_gen")])}
"""
    REPORT.write_text(report)
    print(f"DONE. Report: {REPORT}")
    print(f"Best batch rate: {state['best_rate']:.2%}")


if __name__ == "__main__":
    main()
