#!/usr/bin/env python3
"""Execute active goals' loops for real -- runs the goal's verification test(s),
computes test_pass_rate, persists the loop_trace result, and marks a converged
goal resolved.

TraceGoalRefactorPipeline.refactor() needs a caller-supplied step_fn per goal
(there is no way to derive "which test verifies this" from a goal's title
alone); refactor_traces_to_goals.py only synthesizes + persists the
GoalSpecification. This script supplies that missing half for the goals whose
verification target is known.

Usage:
    python scripts/ops/execute_goal_loops.py             # default: dry-run, show targets
    python scripts/ops/execute_goal_loops.py --execute    # actually run the tests
"""

from __future__ import annotations

import argparse
import asyncio
import re
import subprocess
import sys


sys.path.insert(0, "src")

from cohezion.flume.loop_goal_refactor_engine import (
    AutonomousGoalExecutor,
    DurableSurrealGoalPersistence,
    GoalSpecification,
)


# Maps a substring of a goal's title to the pytest target that verifies it.
# There is no way to derive this from the title alone -- it's the one piece of
# judgment a human/agent adds per goal when wiring execution. Extend as new
# actionable goals get synthesized by refactor_traces_to_goals.py.
_GOAL_TEST_TARGETS: dict[str, str] = {
    # 2026-08-30 health campaign: verify_code's dotted-call bypass (os.system
    # verified safe) was caught and fixed; proof6 is the exact regression test.
    "verify_code dotted-call bypass": (
        "tests/physics/test_rigorous_empirical_proofs.py::"
        "test_proof6_autoharness_ast_safety_and_latency"
    ),
    # Same campaign, the other 6 fixes (7xF821-Any, context_store-kwarg,
    # transports-syntax, EVIPriority-mutable, tier1_available-unbound,
    # skillmatrix-markers) span different modules with no single dedicated
    # regression test each -- "stay green" is verified against this project's
    # own established fast-tests gate (harness.md), which the retro's own
    # "1882 passed / 0 failed" claim was itself measured against.
    "Verify 7 fixes stay green": "tests/unit",
}


def _pytest_pass_rate(target: str) -> tuple[float, str]:
    """Run pytest against `target`; return (pass_rate, one-line summary)."""
    try:
        result = subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                target,
                "-q",
                "--tb=line",
                "-p",
                "no:warnings",
                "--import-mode=append",
            ],
            capture_output=True,
            text=True,
            timeout=280,
        )
    except subprocess.TimeoutExpired:
        return 0.0, f"TIMEOUT running {target}"
    output = result.stdout + result.stderr
    tail = " | ".join(output.strip().splitlines()[-3:])
    passed = sum(int(n) for n in re.findall(r"(\d+) passed", output))
    failed = sum(int(n) for n in re.findall(r"(\d+) failed", output))
    errored = sum(int(n) for n in re.findall(r"(\d+) error", output))
    total = passed + failed + errored
    if total == 0:
        return 0.0, f"NO TESTS RAN (collection error?) -- {tail}"
    return passed / total, tail


def _find_target(goal_title: str) -> str | None:
    for key, target in _GOAL_TEST_TARGETS.items():
        if key in goal_title:
            return target
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="actually run the tests")
    args = parser.parse_args()

    persistence = DurableSurrealGoalPersistence()
    open_goals = persistence.fetch_open_goals(limit=50)
    if not open_goals:
        print("No active goals.")
        return 0

    ran = 0
    for row in open_goals:
        title = row.get("title", "")
        target = _find_target(title)
        if target is None:
            print(f"SKIP (no known verification target): {title!r}")
            continue

        raw_id = row.get("id", "")
        goal_id = raw_id.split(":", 1)[1].strip("`") if ":" in raw_id else raw_id
        goal = GoalSpecification(
            goal_id=goal_id,
            title=title,
            target_metric=row.get("target_metric", "test_pass_rate"),
            target_threshold=row.get("target_threshold", 1.0),
            max_iterations=row.get("max_iterations", 3),
        )
        print(f"\n=== {title} ===\nverification target: {target}")
        if not args.execute:
            print("(dry-run: not running. Re-run with --execute.)")
            continue

        def step_fn(_it: int, state: dict, _target: str = target) -> tuple[dict, float, str]:
            rate, summary = _pytest_pass_rate(_target)
            return state, rate, summary

        executor = AutonomousGoalExecutor(goal)
        result = asyncio.run(executor.execute_loop(initial_state={}, step_fn=step_fn))
        print(
            f"converged={result.converged} final_metric={result.final_metric:.3f} "
            f"iterations={result.iterations_run} ({result.total_time_ms:.0f}ms)"
        )
        for step in result.history:
            print(f"  iter {step.iteration}: {step.action_taken}")

        persistence.persist_loop_result(result)
        if result.converged:
            persistence._sql(f"UPDATE goal:`{goal.goal_id}` SET status = 'resolved';")
            print(f"  goal:`{goal.goal_id}` marked resolved")
        ran += 1

    print(f"\nRan {ran} goal loop(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
