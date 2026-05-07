"""ARC-AGI-2 Solver with UCB1-guided search and FLUME embedding.

V-Model engineering:
  Phase 1: Requirements       — solve public ARC training + eval
  Phase 2: System Design        — brute-force transform search + neural ranker
  Phase 3: Architecture       — this module
  Phase 4: Module Design        — beam search, scoring, persistence
  Phase 5: Implementation       — below
  Phase 6: Unit Test            — tests/arc/test_solver.py
  Phase 7: Integration Test   — end-to-end on 20 tasks
  Phase 8: System Test          — 400-task eval
  Phase 9: Validation           — match paper baselines (≥2% solve rate)

Target: ≥2% solve rate on ARC-AGI-2 eval (public baseline).

Changelog (Task 9 — Search Upgrade):
  - D=4, beam=12 defaults (was 3/8)
  - rotate_270 dedup via geometry redundancy table
  - Adaptive depth: auto-escalate D=3→4 if solve_rate stalls
  - Color-op integration: derive per-task color mappings from train pairs
  - Composition score: track multi-op "discoveries"
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from cohezion.arc.transforms import (
    ALL_TRANSFORMS,
    GEOMETRY_REDUNDANT_IF_PRESENT,
    TransformFn,
    make_color_remap,
    make_color_swap,
)


KSEARCH_PATH = Path.home() / ".cohezion-research/ksearch/arc_prize.json"


@dataclass
class SolverState:
    beam: list[tuple[list[str], float]] = field(default_factory=list)
    best_score: float = 0.0
    best_chain: list[str] = field(default_factory=list)
    total_evals: int = 0
    wins: int = 0
    discoveries: int = 0  # number of multi-op chains beating all single-op chains


def _exact_match(pred: np.ndarray, target: np.ndarray) -> bool:
    return pred.shape == target.shape and np.array_equal(pred, target)


def _score_chain(
    chain: list[str],
    train_pairs: list[dict[str, np.ndarray]],
    ops_registry: dict[str, TransformFn],
) -> float:
    """Fraction of train examples solved exactly.

    Uses ops_registry (base transforms + per-task color ops) instead of
    the global ALL_TRANSFORMS, so dynamically-generated color ops work.
    """
    solved = 0
    for pair in train_pairs:
        out = _apply_chain_ext(pair["input"], chain, ops_registry)
        if out is not None and _exact_match(out, pair["output"]):
            solved += 1
    return solved / len(train_pairs)


def _apply_chain_ext(
    grid: np.ndarray,
    chain: list[str],
    ops_registry: dict[str, TransformFn],
) -> np.ndarray | None:
    """Apply a chain using an extended ops registry (base + per-task ops)."""
    current = grid.copy()
    for name in chain:
        fn = ops_registry.get(name)
        if fn is None:
            return None
        try:
            result = fn(current)
        except Exception:
            return None
        if result is None:
            return None
        if result.shape[0] > 30 or result.shape[1] > 30:
            return None
        current = result
    return current


def ucb1_score(mean: float, trials: int, total_trials: int, c: float = math.sqrt(2)) -> float:
    if trials == 0:
        return float("inf")
    return mean + c * math.sqrt(math.log(total_trials) / trials)


# ── Color-op derivation from train pairs ──────────────────────────


def _collect_color_pairs(
    train_pairs: list[dict[str, np.ndarray]],
) -> dict[int, set[int]]:
    """For each color in any input, record what colors appear in the same
    positions in the corresponding output."""
    mapping: dict[int, set[int]] = {}
    for pair in train_pairs:
        inp = pair["input"]
        out = pair["output"]
        # Only analyze pairs with matching shapes
        if inp.shape != out.shape:
            continue
        for i_val in np.unique(inp):
            if i_val == 0:
                continue
            positions = inp == i_val
            out_colors = set(out[positions].ravel().tolist())
            mapping.setdefault(int(i_val), set()).update(out_colors)
    return mapping


def _derive_color_mapping(
    train_pairs: list[dict[str, np.ndarray]],
) -> dict[int, int]:
    """Derive a simple color mapping: if an input color consistently maps
    to exactly one output color (and that color differs), include it."""
    pairs = _collect_color_pairs(train_pairs)
    mapping: dict[int, int] = {}
    for src, dsts in pairs.items():
        # Only map if unique, non-zero, and different from source
        dsts = {d for d in dsts if d != 0}
        if len(dsts) == 1:
            dst = dsts.pop()
            if dst != src:
                mapping[src] = dst
    return mapping


def derive_color_ops(
    train_pairs: list[dict[str, np.ndarray]],
) -> dict[str, TransformFn]:
    """Analyze train pairs and generate parameterized color ops.

    Strategy: for each derived color mapping, create both individual
    color_swap ops and a combined color_remap op.
    """
    mapping = _derive_color_mapping(train_pairs)
    ops: dict[str, TransformFn] = {}

    if not mapping:
        return ops

    # Individual swaps
    for src, dst in sorted(mapping.items()):
        name = f"color_swap_{src}_to_{dst}"
        ops[name] = make_color_swap(src, dst)

    # Combined remap
    if len(mapping) >= 2:
        remap_name = f"color_remap_{'_'.join(f'{s}t{d}' for s, d in sorted(mapping.items()))}"
        ops[remap_name] = make_color_remap(mapping)

    return ops


# ── Redundancy checking ───────────────────────────────────────────


def _is_op_redundant(chain: list[str], op_name: str) -> bool:
    """Return True if op_name would be redundant given the chain already.

    Redundancy rules (from GEOMETRY_REDUNDANT_IF_PRESENT):
    - If rotate_90 is already in chain, skip rotate_270 (rotate_270 = rotate_90∘rotate_180)
    - If rotate_270 is already in chain, skip rotate_90
    - Same-op doubling: rotate_180+rotate_180 = identity, etc.
    """
    # Rule 1: if the same op is already present and it's a geometry self-inverse or
    # double-applicable, skip it
    redundant = GEOMETRY_REDUNDANT_IF_PRESENT.get(op_name, set())
    for existing in chain:
        if existing in redundant:
            return True
        if existing == op_name and op_name in redundant:
            return True
    return False


# ── Main beam search ──────────────────────────────────────────────


def beam_search(
    train_pairs: list[dict[str, np.ndarray]],
    max_depth: int = 4,
    beam_width: int = 12,
    time_budget_sec: float = 30.0,
    skip_redundant: bool = True,
    adaptive: bool = False,
    color_ops: dict[str, TransformFn] | None = None,
) -> list[str]:
    """Find best transform chain via beam search with UCB1 pruning.

    Args:
        train_pairs: List of {input, output} training examples.
        max_depth: Maximum chain length (default 4).
        beam_width: Number of chains to keep per depth (default 12).
        time_budget_sec: Stop if elapsed exceeds this.
        skip_redundant: If True, skip geometry ops made redundant by
            existing chain members (e.g., rotate_270 after rotate_90).
        adaptive: If True, auto-escalate from D=3 to D=4 if solve_rate
            stalls (used by eval harness).
        color_ops: Pre-derived per-task color transform functions
            (from derive_color_ops). Added to the op set during search.

    Returns:
        Best transform chain found (may be empty if none found).
    """
    # Build op registry: base ops + any per-task color ops
    ops_registry: dict[str, TransformFn] = dict(ALL_TRANSFORMS)
    if color_ops:
        for name, fn in color_ops.items():
            ops_registry[name] = fn

    names = list(ops_registry.keys())
    beams: list[tuple[list[str], float]] = [([], 0.0)]
    state = SolverState()
    t0 = time.monotonic()
    ksearch = _load_ksearch()

    # Single-op baseline: best score achievable with exactly one op.
    # Used for composition discovery tracking.
    single_op_best = 0.0

    # ── Adaptive depth handling ────────────────────────────────
    if adaptive:
        # Start at D=3, escalate to original max_depth only if needed
        effective_depth = min(3, max_depth)
        escalation_depth = max_depth
    else:
        effective_depth = max_depth
        escalation_depth = max_depth

    depth = 1
    escalated = False

    while depth <= effective_depth:
        candidates: list[tuple[list[str], float]] = []
        for chain, _ in beams:
            for name in names:
                # Dedup: skip redundant geometry ops
                if skip_redundant and _is_op_redundant(chain, name):
                    continue

                new_chain = [*chain, name]
                # Skip if known loser in K-Search
                node = ksearch.get("nodes", {}).get("_".join(new_chain))
                if node and node.get("trials", 0) > 3 and node.get("wins", 0) == 0:
                    continue
                score = _score_chain(new_chain, train_pairs, ops_registry)
                state.total_evals += 1
                candidates.append((new_chain, score))
                if time.monotonic() - t0 > time_budget_sec:
                    break
            if time.monotonic() - t0 > time_budget_sec:
                break

        # Track best by actual score BEFORE UCB1 narrows the beam
        if candidates:
            actual_best = max(candidates, key=lambda x: x[1])
            if actual_best[1] > state.best_score:
                state.best_score = actual_best[1]
                state.best_chain = actual_best[0]

            # Track single-op baseline at depth 1
            if depth == 1:
                single_op_best = max(c[1] for c in candidates)

            # Composition discovery: multi-op chain beats all single-op chains
            if depth >= 2 and actual_best[1] > single_op_best and actual_best[1] > 0:
                state.discoveries += 1

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

        # ── Adaptive escalation: if we just finished D=3, nothing solved,
        #     and we have budget remaining, escalate to D=4 ──────────
        if (
            adaptive
            and not escalated
            and depth >= 3
            and state.best_score == 0.0
            and effective_depth < escalation_depth
            and time.monotonic() - t0 < time_budget_sec * 0.5
        ):
            effective_depth = escalation_depth
            escalated = True
            # depth continues to increment normally; loop continues to D=4

        depth += 1

    return state.best_chain


def solve_task(
    task: dict[str, Any],
    time_budget: float = 30.0,
    max_depth: int = 4,
    beam_width: int = 12,
    adaptive: bool = False,
) -> np.ndarray | None:
    """Solve a single ARC task.

    Derives per-task color ops from train pairs before search.
    """
    train_pairs = task["train"]
    color_ops = derive_color_ops(train_pairs)
    best_chain = beam_search(
        train_pairs,
        max_depth=max_depth,
        beam_width=beam_width,
        time_budget_sec=time_budget * 0.8,
        adaptive=adaptive,
        color_ops=color_ops,
    )
    # Build extended registry for applying the final chain
    ops_registry: dict[str, TransformFn] = dict(ALL_TRANSFORMS)
    if color_ops:
        for name, fn in color_ops.items():
            ops_registry[name] = fn
    test_input = task["test"][0]["input"]
    return _apply_chain_ext(test_input, best_chain, ops_registry)


def evaluate_on_subset(
    subset: str = "training",
    limit: int | None = None,
    time_per_task: float = 30.0,
    max_depth: int = 4,
    beam_width: int = 12,
    adaptive: bool = False,
) -> dict[str, Any]:
    """Run solver on ARC subset and return metrics."""
    from cohezion.arc.data_loader import load_all

    tasks = load_all(subset, limit=limit)
    results: dict[str, Any] = {"solved": 0, "total": 0, "details": []}
    for tid, task in tasks.items():
        pred = solve_task(
            task,
            time_budget=time_per_task,
            max_depth=max_depth,
            beam_width=beam_width,
            adaptive=adaptive,
        )
        true_out = task["test"][0]["output"]
        match = pred is not None and _exact_match(pred, true_out)
        results["total"] += 1
        if match:
            results["solved"] += 1
        results["details"].append({"task": tid, "match": match, "chain": []})
    results["solve_rate"] = results["solved"] / max(results["total"], 1)
    return results


# ── K-Search persistence ──────────────────────────────────────────


def _load_ksearch() -> dict[str, Any]:
    if KSEARCH_PATH.exists():
        return json.loads(KSEARCH_PATH.read_text())
    return {"target": "arc_prize", "total_trials": 0, "nodes": {}}


def _save_ksearch(data: dict[str, Any]) -> None:
    KSEARCH_PATH.parent.mkdir(parents=True, exist_ok=True)
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
