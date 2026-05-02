import gc
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
_vram_clear_interval = 10  # Clear VRAM every 10 problems
_safety_threshold = 30.0  # 30s Safety Trigger per arXiv:2603.27844v1


def reset_vram_state():
    """Hard reset to prevent vLLM memory leak."""
    print("Executing Hard VRAM Reset (GC & CUDA Cache)...")
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def predict(id_df: pl.DataFrame, problem_df: pl.DataFrame) -> pl.DataFrame:
    """
    The core prediction function required by AIMO3InferenceServer.
    Implements Pure Equal Division budget per AIMO-3 paper.
    """
    global _coordinator, _auditor, _start_time, _problems_solved

    if _coordinator is None:
        _coordinator = SwarmCoordinator()
        _auditor = KnowerAuditor()
        _start_time = time.time()

    # Periodic VRAM reset to combat vLLM memory leak
    if _problems_solved > 0 and _problems_solved % _vram_clear_interval == 0:
        reset_vram_state()

    problem_id = id_df["id"].to_list()[0]
    problem_text = problem_df["problem"].to_list()[0]

    # 1. Pure Equal Division Time Budgeting (arXiv:2603.27844v1)
    elapsed = time.time() - _start_time
    remaining_time = _total_time_limit - elapsed
    remaining_problems = 50 - (_problems_solved % 50)  # 50 problems per test set

    # Per-problem budget calculation
    budget_per_problem = remaining_time / max(1, remaining_problems)

    print(
        f"\n[Problem {_problems_solved + 1}] Remaining Time: {remaining_time:.1f}s | Budget: {budget_per_problem:.1f}s"
    )

    # 2. 30s Safety Trigger
    if budget_per_problem < _safety_threshold:
        print(f"⚠️ Budget ({budget_per_problem:.1f}s) below safety threshold. Returning default 0.")
        _problems_solved += 1
        return pl.DataFrame({"id": [problem_id], "answer": [0]})

    # 3. Diverse Prompt Mixer (Decorrelation)
    # Rotating through strategies to decorrelate errors
    strategies = ["Algebraist", "InductiveReasoning", "GoalOriented", "NumberTheorist"]
    primary_strategy = strategies[_problems_solved % len(strategies)]
    secondary_strategy = strategies[(_problems_solved + 1) % len(strategies)]

    run_results = []
    reasoning_chains = []

    # Target model for Kaggle (FP8 quantized)
    model_choice = (
        "deepseek-r1-distill-qwen-32b-fp8"
        if os.getenv("KAGGLE_IS_COMPETITION_RERUN")
        else "qwen3.5:cloud"
    )

    # Run 1: Primary specialist
    print(f"Executing Run 1 using {primary_strategy} strategy...")
    specialist1 = BaseSpecialist(primary_strategy, model_name=model_choice)
    response1 = specialist1.solve(problem_text)
    answer1 = specialist1.extract_answer(response1)
    run_results.append(answer1)
    reasoning_chains.append(response1)

    # Run 2: Secondary specialist
    print(f"Executing Run 2 using {secondary_strategy} strategy...")
    specialist2 = BaseSpecialist(secondary_strategy, model_name=model_choice)
    response2 = specialist2.solve(problem_text)
    answer2 = specialist2.extract_answer(response2)
    run_results.append(answer2)
    reasoning_chains.append(response2)

    # 4. Knower Audit & Weighted Voting
    audit = _auditor.audit_runs(run_results, reasoning_chains)

    if audit.get("action") == "TIE_BREAKER":
        # Check if we have budget for Run 3
        # Assuming Run 3 takes roughly same as Run 1 (~budget/2)
        if budget_per_problem > 165.0:
            print("Divergence detected. Triggering Weighted Tie-Breaker (Run 3)...")
            spec3_strategy = strategies[(_problems_solved + 2) % len(strategies)]
            tie_specialist = BaseSpecialist(spec3_strategy, model_name=model_choice)
            res3_text = tie_specialist.solve(problem_text)
            ans3 = tie_specialist.extract_answer(res3_text)
            run_results.append(ans3)
            reasoning_chains.append(res3_text)
            final_answer = _auditor.resolve_tie(answer1, answer2, ans3, reasoning_chains)
        else:
            print(
                "Divergence detected, but budget is too low for Tie-Breaker. Using highest-weight run."
            )
            final_answer = answer1 if answer1 is not None else 0
    else:
        final_answer = audit["final_answer"]

    _problems_solved += 1
    # Ensure answer is in 0-99999 range
    final_answer = int(final_answer or 0) % 100000
    return pl.DataFrame({"id": [problem_id], "answer": [final_answer]})


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
