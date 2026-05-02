import json
import os
import time

import numpy as np
from arc_cosmogony_synthesizer import CosmogonySynthesizer

from cohezion.compound.tdd_adversarial.tdd_integration import TDDIntegration


class CosmogonyEvaluator:
    """Evaluates the CosmogonySynthesizer against the ARC-AGI-2 dataset."""

    def __init__(self, data_dir="data/arc-agi-2-repo/data/training"):
        self.data_dir = data_dir
        self.synthesizer = CosmogonySynthesizer(pop_size=50, max_generations=100)

    def load_task(self, task_id):
        path = os.path.join(self.data_dir, f"{task_id}.json")
        with open(path) as f:
            return json.load(f)

    def solve_task(self, task_id):
        task = self.load_task(task_id)
        print("\n==========================================")
        print(f"Solving Task: {task_id}")
        print("==========================================")

        # 1. Synthesize rule using training pairs
        train_pairs = task["train"]
        print(f"Training on {len(train_pairs)} pairs...")

        # Start timer
        start_time = time.time()

        # Extract masks for testing (in a real scenario, the synthesizer
        # would handle test masks dynamically)
        best_program = self.synthesizer.synthesize_rule(task_id, train_pairs)

        duration = time.time() - start_time
        print(f"\nSynthesis Duration: {duration:.2f}s")

        # 2. Evaluate on test set
        test_pairs = task["test"]
        print(f"Evaluating on {len(test_pairs)} test pairs...")

        correct = 0
        for i, pair in enumerate(test_pairs):
            test_in = np.array(pair["input"])
            test_out = np.array(pair["output"])

            # Use the coupler to find organs on the test input
            test_mask, _ = self.synthesizer.coupler.find_organs(test_in)

            # Execute precipitated program
            predicted_out = self.synthesizer.execute_program(best_program, test_in, test_mask)

            if predicted_out.shape == test_out.shape and np.all(predicted_out == test_out):
                print(f"  Test {i}: PASSED")
                correct += 1
            else:
                print(f"  Test {i}: FAILED")

        return correct == len(test_pairs)

    def run_benchmark(self, limit=5):
        """Runs the evaluator on a subset of the training set."""
        print(f"Running Cosmogony Benchmark on {limit} tasks...")

        # Initialize TDD Integration just to verify we have access to it
        # as requested in Step 1.3
        print("Verifying TDDIntegration availability...")
        from pathlib import Path

        tdd = TDDIntegration(Path.cwd())
        print(f"TDD Root: {tdd.project_root}")

        task_files = sorted(os.listdir(self.data_dir))[:limit]

        passed = 0
        for filename in task_files:
            task_id = filename.split(".")[0]
            try:
                if self.solve_task(task_id):
                    passed += 1
            except Exception as e:
                print(f"Error on task {task_id}: {e}")

        print("\n--- Final Results ---")
        print(f"Total Tasks: {limit}")
        print(f"Tasks Passed: {passed}")
        print(f"Accuracy: {(passed / limit) * 100:.2f}%")


if __name__ == "__main__":
    evaluator = CosmogonyEvaluator()
    evaluator.run_benchmark(limit=3)
