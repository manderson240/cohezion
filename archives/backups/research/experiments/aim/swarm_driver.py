import time

from base_specialist import BaseSpecialist
from knower_auditor import KnowerAuditor
from mock_aimo_api import make_env
from swarm_coordinator import SwarmCoordinator


def run_simulation():
    # 1. Initialize Mock Environment
    env = make_env("reference_problems.json")
    iter_test = env.iter_test()

    # 2. Initialize Swarm Components
    coordinator = SwarmCoordinator()
    auditor = KnowerAuditor()

    print("--- Starting AIMO Swarm Simulation ---")

    total_stability = 0.0
    problems_processed = 0

    for test_df, sample_submission_df in iter_test:
        problem_id = test_df.iloc[0]["id"]
        problem_text = test_df.iloc[0]["problem"]
        print(f"\n[Problem: {problem_id}] Processing...")

        # A. Plan the Journey
        task = coordinator.plan_journey(problem_id, problem_text)
        print(f"Assigning Specialists: {task.assigned_specialists}")

        # B. Dual-Run Execution (Cross-Specialist Verification)
        run_results = []
        reasoning_chains = []

        # Run 1: Primary Specialist
        spec1_name = task.assigned_specialists[0]
        print(f"--- Run 1: {spec1_name} ---")
        specialist1 = BaseSpecialist(spec1_name)
        response1 = specialist1.solve(problem_text, keep_alive="1m")
        ans1 = specialist1.extract_answer(response1)
        run_results.append(ans1)
        reasoning_chains.append(response1)

        # Run 2: Secondary Specialist (or Primary again if only one)
        spec2_name = (
            task.assigned_specialists[1] if len(task.assigned_specialists) > 1 else spec1_name
        )
        print(f"--- Run 2: {spec2_name} ---")
        specialist2 = BaseSpecialist(spec2_name)
        response2 = specialist2.solve(problem_text, keep_alive="1m")
        ans2 = specialist2.extract_answer(response2)
        run_results.append(ans2)
        reasoning_chains.append(response2)

        time.sleep(2)

        # C. Knower Audit
        audit = auditor.audit_runs(run_results, reasoning_chains)
        print(f"Audit Results: {audit}")

        total_stability += audit["stability_score"]
        problems_processed += 1
        final_answer = audit["final_answer"]

        # D. Tie-Breaker (if needed)
        if audit["action"] == "TIE_BREAKER":
            print("--- Triggering Tie-Breaker (Run 3) ---")
            tie_specialist = BaseSpecialist(spec1_name, "phi4:latest")
            res3_text = tie_specialist.solve(problem_text, keep_alive="1m")
            res3 = tie_specialist.extract_answer(res3_text)
            print(f"Tie-Breaker Result: {res3}")
            final_answer = auditor.resolve_tie(run_results[0], run_results[1], res3)
            print(f"Resolved Answer via Voting: {final_answer}")

        # E. Predict and Update Environment
        print(f"Final Answer Submitted: {final_answer}")
        sample_submission_df.loc[0, "answer"] = final_answer
        env.predict(sample_submission_df)

    print("\n--- Simulation Complete ---")
    accuracy = env.competition.get_score()
    avg_stability = total_stability / problems_processed if problems_processed > 0 else 0.0
    print(f"Final Accuracy: {accuracy * 100:.2f}% | Avg Stability: {avg_stability:.3f}")
    return accuracy, avg_stability


if __name__ == "__main__":
    try:
        run_simulation()
    except Exception as e:
        print(f"Simulation Failed: {e!s}")
