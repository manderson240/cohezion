import os
import sys
import time

import polars as pl


# Add official classes to path
sys.path.insert(0, os.path.join(os.getcwd(), "input"))
from base_specialist import BaseSpecialist
from kaggle_evaluation.aimo_3_inference_server import AIMO3InferenceServer
from knower_auditor import KnowerAuditor

# Import our local components
from swarm_coordinator import SwarmCoordinator


# Global state for production swarm
_coordinator = None
_auditor = None
_start_time = None
_problems_solved = 0
_total_time_limit = 5 * 3600  # 5 hours


def predict(id_df: pl.DataFrame, problem_df: pl.DataFrame) -> pl.DataFrame:
    """
    The core prediction function required by AIMO3InferenceServer.
    """
    global _coordinator, _auditor, _start_time, _problems_solved

    if _coordinator is None:
        _coordinator = SwarmCoordinator()
        _auditor = KnowerAuditor()
        _start_time = time.time()

    problem_id = id_df["id"].to_list()[0]
    problem_text = problem_df["problem"].to_list()[0]

    # 1. Telemetry & Time Budgeting
    elapsed = time.time() - _start_time
    remaining_time = _total_time_limit - elapsed
    remaining_problems = 110 - _problems_solved
    time_per_problem = remaining_time / max(1, remaining_problems)

    print(f"\n[Problem {_problems_solved + 1}/110] Time Budget: {time_per_problem:.1f}s")

    # 2. Plan the Journey
    task = _coordinator.plan_journey(problem_id, problem_text)

    # 3. Dual-Run Execution (Adversarial TDD)
    # We'll use Cloud Specialists during development for speed
    run_results = []
    reasoning_chains = []

    # Run 1: Primary specialist with cloud model
    specialist1 = BaseSpecialist(task.assigned_specialists[0], model_name="deepseek-r1:7b")
    response1 = specialist1.solve(problem_text)
    answer1 = specialist1.extract_answer(response1)
    run_results.append(answer1)
    reasoning_chains.append(response1)

    # Run 2: Secondary specialist with cloud model
    spec2 = (
        task.assigned_specialists[1]
        if len(task.assigned_specialists) > 1
        else task.assigned_specialists[0]
    )
    specialist2 = BaseSpecialist(spec2, model_name="deepseek-r1:7b")
    response2 = specialist2.solve(problem_text)
    answer2 = specialist2.extract_answer(response2)
    run_results.append(answer2)
    reasoning_chains.append(response2)

    # 4. Knower Audit
    audit = _auditor.audit_runs(run_results, reasoning_chains)
    final_answer = audit["final_answer"]

    _problems_solved += 1
    return pl.DataFrame({"id": [problem_id], "answer": [int(final_answer)]})


def main():
    server = AIMO3InferenceServer(predict)

    # Check if we are in rerun mode
    if os.getenv("KAGGLE_IS_COMPETITION_RERUN"):
        server.serve()
    else:
        # Run local gateway against downloaded test.csv
        test_csv = os.path.abspath("input/test.csv")
        print(f"Running local gateway against: {test_csv}")
        server.run_local_gateway((test_csv,))


if __name__ == "__main__":
    main()
