"""ARC-AGI-2 Solver with UCB1-guided search and FLUME embedding.

V-Model engineering:
  Phase 1: Requirements      — solve public ARC training + eval
  Phase 2: System Design       — brute-force transform search + neural ranker
  Phase 3: Architecture      — this module
  Phase 4: Module Design       — beam search, scoring, persistence
  Phase 5: Implementation      — below
  Phase 6: Unit Test           — tests/arc/test_solver.py
  Phase 7: Integration Test  — end-to-end on 20 tasks
  Phase 8: System Test         — 400-task eval
  Phase 9: Validation          — match paper baselines (≥2% solve rate)

Target: ≥2% solve rate on ARC-AGI-2 eval (public baseline).
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from cohezion.arc.transforms import ALL_TRANSFORMS, apply_chain


KSEARCH_PATH = Path.home() / ".cohezion-research/ksearch/arc_prize.json"


@dataclass
class SolverState:
    beam: list[tuple[list[str], float]] = field(default_factory=list)
    best_score: float = 0.0
    best_chain: list[str] = field(default_factory=list)
    total_evals: int = 0
    wins: int = 0


def _exact_match(pred: np.ndarray, target: np.ndarray) -> bool:
    return pred.shape == target.shape and np.array_equal(pred, target)


def _score_chain(chain: list[str], train_pairs: list[dict[str, np.ndarray]]) -> float:
    """Fraction of train examples solved exactly."""
    solved = 0
    for pair in train_pairs:
        out = apply_chain(pair["input"], chain)
        if out is not None and _exact_match(out, pair["output"]):
            solved += 1
    return solved / len(train_pairs)


def ucb1_score(mean: float, trials: int, total_trials: int, c: float = math.sqrt(2)) -> float:
    if trials == 0:
        return float("inf")
    return mean + c * math.sqrt(math.log(total_trials) / trials)


def beam_search(
    train_pairs: list[dict[str, np.ndarray]],
    max_depth: int = 3,
    beam_width: int = 8,
    time_budget_sec: float = 30.0,
) -> list[str]:
    """Find best transform chain via beam search with UCB1 pruning."""
    names = list(ALL_TRANSFORMS.keys())
    beams: list[tuple[list[str], float]] = [([], 0.0)]
    state = SolverState()
    t0 = time.monotonic()
    ksearch = _load_ksearch()

    for _depth in range(1, max_depth + 1):
        candidates: list[tuple[list[str], float]] = []
        for chain, _ in beams:
            for name in names:
                new_chain = chain + [name]
                # Skip if known loser in K-Search
                node = ksearch.get("nodes", {}).get("_".join(new_chain))
                if node and node.get("trials", 0) > 3 and node.get("wins", 0) == 0:
                    continue
                score = _score_chain(new_chain, train_pairs)
                state.total_evals += 1
                candidates.append((new_chain, score))
                if time.monotonic() - t0 > time_budget_sec:
                    break
            if time.monotonic() - t0 > time_budget_sec:
                break

        # Track best by actual score BEFORE UCB1 narrows the beam
        # UCB1 sorts by exploration potential, not by actual quality.
        # Without this, perfect-score candidates can be ranked out of the beam.
        if candidates:
            actual_best = max(candidates, key=lambda x: x[1])
            if actual_best[1] > state.best_score:
                state.best_score = actual_best[1]
                state.best_chain = actual_best[0]

        # UCB1 ranking for exploration at deeper depths
        total = sum(1 for _ in candidates) + 1
        candidates.sort(
            key=lambda x: ucb1_score(
                x[1],
                ksearch.get("nodes", {}).get("_".join(x[0]), {}).get("trials", 0),
                total,
            ),
            reverse=True,
        )
        beams = candidates[:beam_width]
        if state.best_score == 1.0:
            break
        if time.monotonic() - t0 > time_budget_sec:
            break

    return state.best_chain


def solve_task(task: dict[str, Any], time_budget: float = 30.0) -> np.ndarray | None:
    """Solve a single ARC task."""
    train_pairs = task["train"]
    best_chain = beam_search(train_pairs, time_budget_sec=time_budget * 0.8)
    # Apply to test input (use first test example)
    test_input = task["test"][0]["input"]
    return apply_chain(test_input, best_chain)


def evaluate_on_subset(
    subset: str = "training", limit: int | None = None, time_per_task: float = 30.0
) -> dict[str, Any]:
    """Run solver on ARC subset and return metrics."""
    from cohezion.arc.data_loader import load_all

    tasks = load_all(subset, limit=limit)
    results: dict[str, Any] = {"solved": 0, "total": 0, "details": []}
    for tid, task in tasks.items():
        pred = solve_task(task, time_budget=time_per_task)
        true_out = task["test"][0]["output"]
        match = pred is not None and _exact_match(pred, true_out)
        results["total"] += 1
        if match:
            results["solved"] += 1
        results["details"].append({"task": tid, "match": match, "chain": []})
    results["solve_rate"] = results["solved"] / max(results["total"], 1)
    return results


def _load_ksearch() -> dict[str, Any]:
    if KSEARCH_PATH.exists():
        return json.loads(KSEARCH_PATH.read_text())
    return {"target": "arc_prize", "total_trials": 0, "nodes": {}}


def _save_ksearch(data: dict[str, Any]) -> None:
    KSEARCH_PATH.write_text(json.dumps(data, indent=2))


def update_ksearch(chain: list[str], score: float) -> None:
    """Log result to K-Search tree for future warm-start."""
    data = _load_ksearch()
    key = "_".join(chain)
    node = data["nodes"].setdefault(
        key, {"hypothesis": key, "wins": 0, "trials": 0, "metric_values": []}
    )
    node["trials"] += 1
    node["metric_values"].append(score)
    if score >= 1.0:
        node["wins"] += 1
    data["total_trials"] += 1
    _save_ksearch(data)


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("ARC Prize 2026 Autoresearch Solver")
    print("Running eval on training subset (limit=20)...")
    metrics = evaluate_on_subset("training", limit=20, time_per_task=10.0)
    print(f"Solve rate: {metrics['solve_rate']:.2%} ({metrics['solved']}/{metrics['total']})")
    if metrics["solve_rate"] > 0:
        for d in metrics["details"]:
            if d["match"]:
                print(f"  ✅ {d['task']}")
    else:
        print("No tasks solved. Review transform coverage.")
