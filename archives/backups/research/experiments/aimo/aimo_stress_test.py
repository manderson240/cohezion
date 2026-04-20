import os
import sys
import time
from unittest.mock import patch
import polars as pl


# Mock the BaseSpecialist to simulate time passage and returns
class MockBaseSpecialist:
    def __init__(self, role, model_name="qwen3.5:cloud"):
        self.role = role
        self.model_name = model_name

    def solve(self, text, keep_alive=None):
        # Simulate 60 seconds of compute time per run
        time.sleep(0.01)  # Sleep to allow print flushes, simulate time via monkeypatch
        return f"Simulated response for {self.role}. Boxed answer: \\boxed{{42}}"

    def extract_answer(self, response):
        return 42


def run_stress_test():
    print("=== AIMO 'Hard-Resource' Stress Test ===")
    print("Simulating 5-Hour Limit, 110 Problems, Monte Carlo Tie-Breakers, and VRAM Resets")

    # Import the driver components
    sys.path.insert(0, os.path.abspath("input"))
    import aimo_v2_driver

    # We will mock time.time() to simulate time passing exactly how we want.
    # We start at t=0
    simulated_time = 0.0

    def mock_time():
        nonlocal simulated_time
        return simulated_time

    # Each solver call takes roughly 65 simulated seconds.
    # So 2 runs = 130s. This leaves about ~30s per problem.
    class StressTestSpecialist(MockBaseSpecialist):
        def solve(self, text, keep_alive=None):
            nonlocal simulated_time
            # Simulate 75 seconds per LLM generation to force time budget crunch
            simulated_time += 75.0
            return super().solve(text, keep_alive)

        def extract_answer(self, response):
            nonlocal simulated_time
            simulated_time += 0.5
            # We randomly cause a divergence on problem 5, 25, 45, etc. to test tie_breaker
            import random

            global divergence_problem
            if aimo_v2_driver._problems_solved % 5 == 0:
                return random.choice([42, 13])
            return 42

    with (
        patch("aimo_v2_driver.time.time", side_effect=mock_time),
        patch("aimo_v2_driver.BaseSpecialist", StressTestSpecialist),
    ):
        # Reset globals
        aimo_v2_driver._coordinator = None
        aimo_v2_driver._auditor = None
        aimo_v2_driver._start_time = None
        aimo_v2_driver._problems_solved = 0

        total_problems = 110
        for i in range(total_problems):
            # Create mock dataframes
            id_df = pl.DataFrame({"id": [f"prob_{i}"]})
            problem_df = pl.DataFrame({"problem": ["Solve for X: 2x = 84"]})

            # Predict
            result = aimo_v2_driver.predict(id_df, problem_df)

            # Output progress every 10 problems
            if (i + 1) % 10 == 0:
                print(
                    f"✅ Completed {i + 1}/110 - Simulated Time Elapsed: {simulated_time:.1f}s / {5 * 3600}s"
                )

    print("\\n=== Stress Test Complete ===")
    print(f"Total Simulated Time: {simulated_time:.1f}s")
    if simulated_time <= 5 * 3600:
        print("✅ SUCCESS: Swarm completed 110 problems within 5 hours.")
    else:
        print("❌ FAIL: Swarm exceeded 5-hour budget.")


if __name__ == "__main__":
    run_stress_test()
