#!/usr/bin/env python3
"""
Quick Submission Generator - MVP Baseline

Generates submission.parquet from test.csv using fastest available model.
Target: Get submission file ready within 1 hour.
"""

import argparse
import time
from pathlib import Path

import polars as pl
from base_specialist import BaseSpecialist


def main():
    parser = argparse.ArgumentParser(description="Quick Submission Generator")
    parser.add_argument(
        "--test-csv",
        type=str,
        default="input/test.csv",
        help="Input test CSV path",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output/submission_quick.parquet",
        help="Output parquet path",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="qwen2-math:1.5b",
        help="Model to use",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout per problem (seconds)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("QUICK SUBMISSION GENERATOR")
    print("=" * 60)
    print(f"Input: {args.test_csv}")
    print(f"Output: {args.output}")
    print(f"Model: {args.model}")
    print(f"Timeout: {args.timeout}s")
    print("=" * 60)

    # Load test data
    test_df = pl.read_csv(args.test_csv)
    print(f"\nLoaded {len(test_df)} problems")

    # Initialize specialist
    specialist = BaseSpecialist("Algebraist", model_name=args.model, timeout=args.timeout)

    # Process each problem
    results = []
    for idx in range(len(test_df)):
        problem_id = test_df[idx, "id"]
        problem_text = test_df[idx, "problem"]

        print(f"\n[{idx + 1}/{len(test_df)}] {problem_id}: {problem_text[:50]}...")

        t0 = time.time()
        response = specialist.solve(problem_text)
        answer = specialist.extract_answer(response)
        elapsed = time.time() - t0

        print(f"  Answer: {answer}, Time: {elapsed:.1f}s")

        results.append({"id": problem_id, "answer": answer})

    # Create submission DataFrame
    submission_df = pl.DataFrame(results)
    print(f"\nSubmission DataFrame:")
    print(submission_df)

    # Save to parquet
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    submission_df.write_parquet(args.output)
    print(f"\n✅ Submission saved to: {args.output}")

    # Validate
    print("\nValidation:")
    print(f"  Rows: {len(submission_df)}")
    print(f"  Columns: {submission_df.columns}")
    print(f"  Answer range: {submission_df['answer'].min()} - {submission_df['answer'].max()}")

    print("\n" + "=" * 60)
    print("✅ SUBMISSION READY")
    print("=" * 60)


if __name__ == "__main__":
    main()
