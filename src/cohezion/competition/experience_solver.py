"""Experience-driven ARC solver: learn from training tasks, apply to eval tasks."""

from __future__ import annotations

import json
import time
from typing import Any

from arc_solver import (
    Grid,
    Program,
    apply_program,
    deepcopy_grid,
    grids_equal,
    search_program,
)
from experience_vault import ExperienceVault, extract_signature


def try_program_on_train(program: list[Program], train: list[dict[str, Grid]]) -> bool:
    if not program:
        return False
    try:
        return all(
            grids_equal(apply_program(deepcopy_grid(ex["input"]), program), ex["output"])
            for ex in train
        )
    except Exception:
        return False


def build_prediction(task: dict[str, Any], program: list[Program] | None) -> dict[str, Any]:
    predictions = []
    for test_example in task.get("test", []):
        pred1 = apply_program(deepcopy_grid(test_example["input"]), program or [])
        if pred1 is None:
            pred1 = deepcopy_grid(test_example["input"])
        pred2 = deepcopy_grid(pred1)
        predictions.append({"attempt_1": [pred1], "attempt_2": [pred2]})
    return {task["id"]: predictions}


def solve_with_experience(
    task: dict[str, Any],
    vault: ExperienceVault,
    train_challenges: dict[str, Any],
    train_solutions: dict[str, Any] | None = None,
    max_depth: int = 3,
    budget: int = 5000,
) -> dict[str, Any]:
    """Solve task using warm-start from similar solved training tasks."""
    sig = extract_signature(task["train"])
    similar = vault.find_similar(sig, top_k=10)

    # Phase 1: Re-derive programs from similar solved tasks and try them
    for dist, entry in similar:
        if not entry.solved:
            continue
        # Re-run search on the similar training task to recover its program
        ref_task = train_challenges[entry.task_id]
        ref_task["id"] = entry.task_id
        prog = search_program(ref_task["train"], max_depth=max_depth, budget=budget // 5)
        if prog and try_program_on_train(prog, task["train"]):
            return build_prediction(task, prog)

    # Phase 2: Full DSL search
    program = search_program(task["train"], max_depth=max_depth, budget=budget)
    return build_prediction(task, program)


def run_evaluation(
    train_challenges_path: str,
    train_solutions_path: str,
    test_challenges_path: str,
    test_solutions_path: str,
) -> dict[str, Any]:
    with open(train_challenges_path) as f:
        train_challenges = json.load(f)
    with open(train_solutions_path) as f:
        train_solutions = json.load(f)
    with open(test_challenges_path) as f:
        test_challenges = json.load(f)
    with open(test_solutions_path) as f:
        test_solutions = json.load(f)

    vault_path = ".pi/experience_arc_train.json"
    import os

    if os.path.exists(vault_path) and os.path.getsize(vault_path) > 100:
        vault = ExperienceVault(vault_path)
        print(f"Loaded vault: {vault.stats()}")
    else:
        vault = ExperienceVault(vault_path)
        print("Building experience vault from training data...")
        for task_id in sorted(train_challenges):
            task = train_challenges[task_id]
            task["id"] = task_id
            sols = train_solutions[task_id]

            sig = extract_signature(task["train"])
            start = time.monotonic()
            program = search_program(task["train"], max_depth=3, budget=5000)
            elapsed = (time.monotonic() - start) * 1000

            solved = False
            if program and sols and task.get("test"):
                pred = apply_program(deepcopy_grid(task["test"][0]["input"]), program)
                solved = pred is not None and grids_equal(pred, sols[0])

            from experience_vault import ExperienceEntry

            entry = ExperienceEntry(
                task_id=task_id,
                signature=sig,
                program_names=["dsl"],
                solved=solved,
                solve_time_ms=elapsed,
            )
            vault.add(entry)

        vault.save()
        print(f"Built vault: {vault.stats()}")

    total = len(test_challenges)
    correct = 0
    times = []

    for idx, task_id in enumerate(sorted(test_challenges)):
        task = test_challenges[task_id]
        task["id"] = task_id
        task_sols = test_solutions[task_id]

        start = time.monotonic()
        result = solve_with_experience(
            task, vault, train_challenges, train_solutions, max_depth=3, budget=5000
        )
        elapsed = time.monotonic() - start
        times.append(elapsed)

        pred_grid = result[task_id][0]["attempt_1"][0]
        if task_sols and grids_equal(pred_grid, task_sols[0]):
            correct += 1

        if idx % 30 == 29:
            rate = correct / (idx + 1) * 100
            print(f"  {idx + 1}/{total}: {rate:.2f}% correct")

    rate = correct / total * 100 if total else 0
    return {
        "tasks": total,
        "correct": correct,
        "solve_rate": round(rate, 2),
        "avg_time": round(sum(times) / len(times), 3),
        "vault_stats": vault.stats(),
    }


if __name__ == "__main__":
    root = "/home/mike-anderson/dev/cohezion/data/arc-agi-2"

    print("=== EVAL SET (generalization) ===")
    result = run_evaluation(
        f"{root}/arc-agi_training_challenges.json",
        f"{root}/arc-agi_training_solutions.json",
        f"{root}/arc-agi_evaluation_challenges.json",
        f"{root}/arc-agi_evaluation_solutions.json",
    )
    for k, v in result.items():
        print(f"  {k}: {v}")

    print("\n=== TRAIN SET (sanity check, reusing vault) ===")
    result2 = run_evaluation(
        f"{root}/arc-agi_training_challenges.json",
        f"{root}/arc-agi_training_solutions.json",
        f"{root}/arc-agi_training_challenges.json",
        f"{root}/arc-agi_training_solutions.json",
    )
    for k, v in result2.items():
        print(f"  {k}: {v}")
