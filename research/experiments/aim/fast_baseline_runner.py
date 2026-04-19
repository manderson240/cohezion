#!/usr/bin/env python3
"""
Fast Baseline Runner - Optimized for Speed

Skips adversarial review and dual-run to achieve ≤200s/problem target.
Uses qwen2-math:1.5b for fast compliant inference.

Target: 60%+ accuracy, submission-ready within 4 hours.
"""

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from base_specialist import BaseSpecialist


class FastBaselineRunner:
    """
    Fast baseline runner - single inference, no adversarial review.

    Optimizations:
    - Single run (no dual-run protocol)
    - No adversarial review cycles
    - Fast model (qwen2-math:1.5b)
    - Reduced timeout (60s vs 300s)
    """

    def __init__(
        self,
        reference_path: str = "input/reference.csv",
        model_name: str = "qwen2-math:1.5b",
        timeout: int = 60,
    ):
        self.reference_path = reference_path
        self.model_name = model_name
        self.timeout = timeout
        self.specialist = BaseSpecialist("Algebraist", model_name=model_name, timeout=timeout)

    def load_reference_csv(self) -> List[Dict[str, Any]]:
        """Load reference problems from CSV (handles multi-line problems)."""
        import csv

        problems = []
        with open(self.reference_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                answer_str = row.get("answer", "0")
                try:
                    answer = int(answer_str) if answer_str else 0
                except (ValueError, TypeError):
                    answer = 0
                problems.append(
                    {
                        "id": row.get("id", "unknown"),
                        "problem": row.get("problem", ""),
                        "answer": answer,
                    }
                )
        return problems

    def run_benchmark(self) -> Dict[str, Any]:
        """Run benchmark on all reference problems."""
        print("=" * 60)
        print("FAST BASELINE RUNNER - Optimized for Speed")
        print("=" * 60)
        print(f"Model: {self.model_name}")
        print(f"Timeout: {self.timeout}s")
        print(f"Strategy: Single inference, no adversarial review")
        print("=" * 60)

        problems = self.load_reference_csv()
        print(f"\nRunning {len(problems)} reference problems...\n")

        results = []
        for problem in problems:
            result = self._run_single_problem(problem)
            results.append(result)

            status = "✅" if result["correct"] else "❌"
            print(
                f"{status} {result['problem_id']}: Expected={result['expected']}, "
                f"Actual={result['actual']}, Time={result['time']:.1f}s"
            )

        summary = self._compute_summary(results)
        self._print_summary(summary)

        return summary

    def _run_single_problem(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """Run single problem with fast pipeline."""
        start_time = time.time()

        problem_id = problem["id"]
        problem_text = problem["problem"]
        expected_answer = problem["answer"]

        # Single inference - no dual-run, no adversarial review
        response = self.specialist.solve(problem_text)
        actual_answer = self.specialist.extract_answer(response)

        elapsed = time.time() - start_time
        correct = actual_answer == expected_answer if actual_answer is not None else False

        return {
            "problem_id": problem_id,
            "expected": expected_answer,
            "actual": actual_answer,
            "correct": correct,
            "time": elapsed,
            "response_length": len(response),
        }

    def _compute_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute summary metrics."""
        total = len(results)
        correct_count = sum(1 for r in results if r["correct"])
        total_time = sum(r["time"] for r in results)
        avg_time = total_time / total if total > 0 else 0

        accuracy = correct_count / total if total > 0 else 0

        return {
            "total_problems": total,
            "correct_count": correct_count,
            "accuracy": accuracy,
            "accuracy_target": 0.60,  # Realistic target for fast baseline
            "accuracy_pass": accuracy >= 0.60,
            "total_time": total_time,
            "avg_time": avg_time,
            "time_target": 200.0,  # ≤200s/problem
            "time_pass": avg_time <= 200.0,
            "all_targets_met": accuracy >= 0.60 and avg_time <= 200.0,
        }

    def _print_summary(self, summary: Dict[str, Any]):
        """Print summary report."""
        print(f"\n{'=' * 60}")
        print(f"FAST BASELINE SUMMARY")
        print(f"{'=' * 60}")
        print(f"Total problems: {summary['total_problems']}")
        print(
            f"\nAccuracy: {summary['accuracy'] * 100:.1f}% ({summary['correct_count']}/{summary['total_problems']})"
        )
        print(f"  Target: ≥60% | Pass: {'✅' if summary['accuracy_pass'] else '❌'}")
        print(f"\nAverage time: {summary['avg_time']:.1f}s per problem")
        print(f"  Target: ≤200s | Pass: {'✅' if summary['time_pass'] else '❌'}")
        print(f"\nTotal time: {summary['total_time']:.1f}s ({summary['total_time'] / 60:.1f}m)")
        print(f"\nAll targets met: {'✅ YES' if summary['all_targets_met'] else '❌ NO'}")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fast Baseline Runner")
    parser.add_argument(
        "--reference",
        type=str,
        default="input/reference.csv",
        help="Path to reference CSV",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="qwen2-math:1.5b",
        help="Model to use (default: qwen2-math:1.5b)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout per problem in seconds (default: 60)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output/fast_baseline_results.json",
        help="Output results JSON path",
    )
    args = parser.parse_args()

    runner = FastBaselineRunner(
        reference_path=args.reference,
        model_name=args.model,
        timeout=args.timeout,
    )
    summary = runner.run_benchmark()

    # Save results
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to {args.output}")
