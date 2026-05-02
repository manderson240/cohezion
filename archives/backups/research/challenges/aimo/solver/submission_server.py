#!/usr/bin/env python3
"""Inference server for AIMO3 competition submission.

This file is the entry point for the Kaggle evaluation system.
"""

import sys
from pathlib import Path


# Add solver to path
sys.path.insert(0, str(Path(__file__).parent))

import aimo_3_gateway
from solver import AIMO3SimpleSolver


class SubmissionInferenceServer(AIMO3SimpleSolver):
    """
    Inference server for Kaggle submission.

    Inherits from the solver and implements the required interface.
    """

    pass


if __name__ == "__main__":
    # Standard Kaggle evaluation entry point
    if __import__("os").getenv("KAGGLE_IS_COMPETITION_RERUN"):
        gateway = aimo_3_gateway.AIMO3Gateway()
        gateway.run()
    else:
        # Local testing mode
        print("AIMO3 Simple Solver - Local Test Mode")
        print("=" * 50)

        # Test on reference problems
        import polars as pl

        ref_df = pl.read_csv("../aimo3_data/reference.csv")

        solver = SubmissionInferenceServer()
        print(f"\nTesting on {len(ref_df)} reference problems...")
        print("=" * 50)

        # Run solver
        results = solver.predict(ref_df)

        # Compare with expected
        correct = 0
        for ref_row, result_row in zip(ref_df.iter_rows(named=True), results.iter_rows(named=True)):
            expected = ref_row["answer"]
            predicted = result_row["answer"]
            status = "✓" if predicted == expected else "✗"
            print(f"{status} {ref_row['id']}: {predicted} (expected {expected})")
            if predicted == expected:
                correct += 1

        print(f"\nScore: {correct}/{len(ref_df)} ({100 * correct / len(ref_df):.1f}%)")
