"""
Live E2E Test - Single Reference Problem

Runs the complete swarm pipeline on ONE reference problem with real Ollama calls.
Validates:
- Specialist routing
- Dual-run execution
- Knower audit
- Answer extraction
- Full integration
"""

import json
import time

from base_specialist import BaseSpecialist
from flume_navigator import FLUMEProfilerNavigator
from knower_auditor import KnowerAuditor
from swarm_coordinator import SwarmCoordinator


def run_single_problem(problem: dict, timeout_per_call: int = 60) -> dict:
    """Run single problem through complete pipeline."""
    print(f"\n{'=' * 60}")
    print(f"Problem: {problem['id']}")
    print(f"Text: {problem['problem'][:100]}...")
    print(f"Expected Answer: {problem['answer']}")
    print(f"{'=' * 60}")

    start_time = time.time()

    # 1. Plan journey
    print("\n[1/5] Planning journey...")
    coordinator = SwarmCoordinator()
    task = coordinator.plan_journey(problem["id"], problem["problem"])
    print(f"Assigned specialists: {task.assigned_specialists}")
    print(
        f"Domain scores: algebra={task.state.algebra:.2f}, geometry={task.state.geometry:.2f}, "
        f"number_theory={task.state.number_theory:.2f}, combinatorics={task.state.combinatorics:.2f}"
    )

    # 2. Run 1 - Primary specialist
    print(f"\n[2/5] Run 1: {task.assigned_specialists[0]}...")
    specialist1 = BaseSpecialist(task.assigned_specialists[0])
    try:
        response1 = specialist1.solve(problem["problem"], keep_alive="1m")
        ans1 = specialist1.extract_answer(response1)
        print(f"Response: {response1[:200]}...")
        print(f"Extracted answer: {ans1}")
    except Exception as e:
        print(f"Error in Run 1: {e}")
        response1 = "Error"
        ans1 = None

    # 3. Run 2 - Secondary specialist
    print(
        f"\n[3/5] Run 2: {task.assigned_specialists[1] if len(task.assigned_specialists) > 1 else task.assigned_specialists[0]}..."
    )
    spec2 = (
        task.assigned_specialists[1]
        if len(task.assigned_specialists) > 1
        else task.assigned_specialists[0]
    )
    specialist2 = BaseSpecialist(spec2)
    try:
        response2 = specialist2.solve(problem["problem"], keep_alive="1m")
        ans2 = specialist2.extract_answer(response2)
        print(f"Response: {response2[:200]}...")
        print(f"Extracted answer: {ans2}")
    except Exception as e:
        print(f"Error in Run 2: {e}")
        response2 = "Error"
        ans2 = None

    # 4. Knower audit
    print("\n[4/5] Knower audit...")
    auditor = KnowerAuditor()
    answers = [ans1, ans2] if ans1 is not None and ans2 is not None else [0, 0]
    responses = [response1, response2]
    audit = auditor.audit_runs(answers, responses)
    print(f"Audit result: {audit}")

    # 5. Tie-breaker if needed
    final_answer = audit["final_answer"]
    if audit["action"] == "TIE_BREAKER":
        print("\n[5/5] Tie-breaker (Run 3)...")
        tie_specialist = BaseSpecialist(task.assigned_specialists[0], "phi4:latest")
        try:
            res3_text = tie_specialist.solve(problem["problem"], keep_alive="1m")
            res3 = tie_specialist.extract_answer(res3_text)
            print(f"Tie-breaker answer: {res3}")
            final_answer = auditor.resolve_tie(ans1, ans2, res3)
            print(f"Final answer (majority vote): {final_answer}")
        except Exception as e:
            print(f"Error in tie-breaker: {e}")

    # FLUME stability check
    print("\n[FLUME] Checking stability...")
    flume = FLUMEProfilerNavigator()
    chain1 = flume.encode_reasoning_chain(response1 if response1 else "Error")
    chain2 = flume.encode_reasoning_chain(response2 if response2 else "Error")
    flume_stable = flume.check_stability(chain1, chain2)

    # Summary
    elapsed = time.time() - start_time
    correct = final_answer == problem["answer"]

    print(f"\n{'=' * 60}")
    print(f"RESULTS")
    print(f"{'=' * 60}")
    print(f"Expected: {problem['answer']}")
    print(f"Actual: {final_answer}")
    print(f"Correct: {'✅ YES' if correct else '❌ NO'}")
    print(f"Stable (Knower): {'✅' if audit['consistent'] else '❌'}")
    print(f"Stable (FLUME): {'✅' if flume_stable else '❌'}")
    print(f"Time: {elapsed:.1f}s")
    print(f"{'=' * 60}")

    return {
        "problem_id": problem["id"],
        "expected": problem["answer"],
        "actual": final_answer,
        "correct": correct,
        "stable": audit["consistent"] and flume_stable,
        "time": elapsed,
        "run1_answer": ans1,
        "run2_answer": ans2,
        "tie_breaker_used": audit["action"] == "TIE_BREAKER",
    }


if __name__ == "__main__":
    # Load reference problems
    with open("reference_problems.json", "r") as f:
        problems = json.load(f)

    print(f"Loaded {len(problems)} reference problems")
    print(f"Running E2E test on FIRST problem only (to validate pipeline)...")

    # Run first problem
    result = run_single_problem(problems[0])

    # Save result
    with open("e2e_test_result.json", "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nResult saved to e2e_test_result.json")

    # Summary
    if result["correct"]:
        print("\n✅ E2E TEST PASSED - Pipeline working correctly!")
    else:
        print("\n❌ E2E TEST FAILED - Answer mismatch")
        print(f"   Expected: {result['expected']}, Got: {result['actual']}")
