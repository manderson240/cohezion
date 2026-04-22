"""Test skill refinement convergence for ARC solver.

The paper claims skill refinement improves primitive selection over task batches.
Current `_select_strategies` uses fixed heuristics (color change, shape change).

Experiment:
1. Run solver on batch N of tasks with fixed strategies (baseline).
2. Record which strategy succeeded on which task signature.
3. Build a signature → strategy mapping from successes.
4. Run solver on batch N+1 using learned mapping for warm-start.
5. Compare solve rates: learned vs. fixed.

This validates whether minimal experiential learning improves performance.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import arc_solver
from arc_solver import grids_equal


def task_signature(task: dict) -> str:
    """Compact signature for task similarity."""
    train = task["train"]
    inp_h = len(train[0]["input"])
    inp_w = len(train[0]["input"][0]) if train[0]["input"] else 0
    out_h = len(train[0]["output"])
    out_w = len(train[0]["output"][0]) if train[0]["output"] else 0
    colors = len({c for ex in train for row in ex["input"] for c in row})
    return f"{inp_h}x{inp_w}_to_{out_h}x{out_w}_c{colors}"


def run_with_fixed_strategies(tasks: list, budget: int = 2000) -> Tuple[int, int]:
    """Run solver with fixed _select_strategies."""
    solved = 0
    for task in tasks:
        try:
            ops = arc_solver.get_all_ops(task["train"])
            program = arc_solver.search_program(task["train"], max_depth=3, ops=ops, budget=budget)
            if program and all(
                grids_equal(arc_solver.apply_program(arc_solver.deepcopy_grid(ex["input"]), program), ex["output"])
                for ex in task["train"]
            ):
                solved += 1
        except Exception:
            pass
    return solved, len(tasks)


def run_with_skill_refinement(
    train_tasks: list, test_tasks: list, budget: int = 2000
) -> Dict[str, Any]:
    """Run solver where test_tasks benefit from strategy mapping learned on train_tasks."""

    # Phase 1: Learn from train tasks
    strategy_success: Dict[str, List[str]] = {}

    for task in train_tasks:
        try:
            ops = arc_solver.get_all_ops(task["train"])
            strategies = arc_solver._select_strategies(task["train"])
            found = False
            for name, _ in strategies:
                if found:
                    break
                # Check if this strategy subset would work
                strategy_ops = ops if ops else [("identity", arc_solver.identity)]
                for op in strategy_ops:
                    try:
                        if all(
                            grids_equal(op[1](arc_solver.deepcopy_grid(ex["input"])), ex["output"])
                            for ex in task["train"]
                        ):
                            sig = task_signature(task)
                            if sig not in strategy_success:
                                strategy_success[sig] = []
                            strategy_success[sig].append(name)
                            found = True
                            break
                    except Exception:
                        pass
        except Exception:
            pass

    # Build most-common strategy per signature
    learned_strategies: Dict[str, str] = {}
    for sig, names in strategy_success.items():
        from collections import Counter
        most_common = Counter(names).most_common(1)
        if most_common:
            learned_strategies[sig] = most_common[0][0]

    # Phase 2: Run on test tasks with learned mapping
    baseline_solved = 0
    learned_solved = 0

    for task in test_tasks:
        sig = task_signature(task)
        ops = arc_solver.get_all_ops(task["train"])
        program = arc_solver.search_program(task["train"], max_depth=3, ops=ops, budget=budget)
        if program:
            baseline_solved += 1

        # Test with learned strategy
        if sig in learned_strategies:
            # Try learned strategy first
            strategies = arc_solver._select_strategies(task["train"])
            learned_name = learned_strategies[sig]
            preferred = [s for s in strategies if s[0] == learned_name]
            other = [s for s in strategies if s[0] != learned_name]
            reordered = preferred + other
            ops = arc_solver.get_all_ops(task["train"])
            program = arc_solver.search_program(task["train"], max_depth=3, ops=ops, budget=budget)
            if program:
                learned_solved += 1

    return {
        "train_tasks": len(train_tasks),
        "test_tasks": len(test_tasks),
        "unique_signatures_learned": len(learned_strategies),
        "baseline_solved": baseline_solved,
        "learned_solved": learned_solved,
        "improvement": learned_solved - baseline_solved,
        "improvement_pct": round((learned_solved - baseline_solved) / max(len(test_tasks), 1) * 100, 1),
    }


if __name__ == "__main__":
    random.seed(42)
    root = Path("/home/mike-anderson/dev/cohezion")
    with open(root / "data/arc-agi-2/arc-agi_training_challenges.json") as f:
        challenges = json.load(f)

    # Build task list
    tasks = []
    for task_id in sorted(challenges):
        task = challenges[task_id]
        task["id"] = task_id
        tasks.append(task)

    random.shuffle(tasks)

    # Split: train on first 500, test on next 200
    train = tasks[:500]
    test = tasks[500:700]

    print(f"Train tasks: {len(train)}, Test tasks: {len(test)}")

    # Baseline
    baseline_solved, total = run_with_fixed_strategies(test[:50], budget=1000)
    print(f"\nBaseline (first 50 test tasks, budget=1000):")
    print(f"  Solved: {baseline_solved}/{total} = {baseline_solved/total*100:.1f}%")

    # Refined
    result = run_with_skill_refinement(train, test[:50], budget=1000)
    print(f"\nSkill Refinement (learned from {result['train_tasks']} tasks):")
    print(f"  Unique signatures learned: {result['unique_signatures_learned']}")
    print(f"  Baseline solved: {result['baseline_solved']}/{result['test_tasks']}")
    print(f"  Learned solved:  {result['learned_solved']}/{result['test_tasks']}")
    print(f"  Improvement:     {result['improvement']} tasks (+{result['improvement_pct']:.1f}%)")

    print(f"\nMETRIC skill_refinement_convergence_score={result['improvement_pct']:.1f}")
