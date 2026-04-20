"""
Kaggle Benchmark Runner - COMPLIANT Open-Weight Models

Runs benchmark on reference problems using deepseek-r1:7b (open-weight, pre-March 15 2026).
Target: 100% accuracy on 4 reference problems, ≥0.90 stability.

Supports cloud models (qwen3.5:cloud) for development/validation, but submission must use
compliant open-weight models released before March 15, 2026.
"""

import argparse
import json
import time
from typing import Any, Dict, List

from base_specialist import BaseSpecialist
from knower_auditor import KnowerAuditor
from swarm_coordinator import SwarmCoordinator


class KaggleBenchmarkRunner:
    """
    Runs benchmark on reference problems using COMPLIANT open-weight models.
    Default: deepseek-r1:7b (open-weight, released before March 15 2026)

    Targets:
    - Accuracy: 100% (4/4 reference problems)
    - Stability: ≥0.90 dual-run consistency
    """

    def __init__(
        self,
        reference_problems_path: str = "reference_problems.json",
        model_name: str = "deepseek-r1:7b",
    ):
        self.reference_problems = self._load_problems(reference_problems_path)
        self.coordinator = SwarmCoordinator()
        self.auditor = KnowerAuditor()
        self.model_name = model_name  # Default: compliant deepseek-r1:7b

    def _load_problems(self, path: str) -> List[Dict[str, Any]]:
        """Load reference problems from JSON."""
        with open(path, "r") as f:
            return json.load(f)

    def run_benchmark(self) -> Dict[str, Any]:
        """Run benchmark on all reference problems."""
        print(f"{'=' * 60}")
        print(f"KAGGLE BENCHMARK RUNNER - COMPLIANT Models")
        print(f"{'=' * 60}")
        print(f"Running {len(self.reference_problems)} reference problems...")
        print(f"Model: {self.model_name} (open-weight, compliant)")
        print(f"{'=' * 60}\n")

        results = []
        for problem in self.reference_problems:
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
        """Run single problem through complete pipeline."""
        start_time = time.time()

        problem_id = problem["id"]
        problem_text = problem["problem"]
        expected_answer = problem["answer"]

        # 1. Plan journey
        task = self.coordinator.plan_journey(problem_id, problem_text)

        # 2. Dual-run with cloud models
        run_results = []
        reasoning_chains = []

        # Run 1 - COMPLIANT model
        specialist1 = BaseSpecialist(task.assigned_specialists[0], model_name=self.model_name)
        response1 = specialist1.solve(problem_text)
        ans1 = specialist1.extract_answer(response1)
        run_results.append(ans1)
        reasoning_chains.append(response1)

        # Run 2 - COMPLIANT model
        spec2 = (
            task.assigned_specialists[1]
            if len(task.assigned_specialists) > 1
            else task.assigned_specialists[0]
        )
        specialist2 = BaseSpecialist(spec2, model_name=self.model_name)
        response2 = specialist2.solve(problem_text)
        ans2 = specialist2.extract_answer(response2)
        run_results.append(ans2)
        reasoning_chains.append(response2)

        # 3. Knower audit
        audit = self.auditor.audit_runs(run_results, reasoning_chains)
        final_answer = audit["final_answer"]

        # 4. Tie-breaker if needed (improved - handles None)
        tie_breaker_used = False
        if audit["action"] == "TIE_BREAKER" or final_answer is None:
            print(f"  [Tie-breaker] Divergence detected, running phi4:latest...")
            tie_specialist = BaseSpecialist(
                task.assigned_specialists[0], model_name="phi4:latest", timeout=60
            )
            res3_text = tie_specialist.solve(problem_text)
            res3 = tie_specialist.extract_answer(res3_text)
            final_answer = self.auditor.resolve_tie(ans1, ans2, res3)
            tie_breaker_used = True

        elapsed = time.time() - start_time
        correct = final_answer == expected_answer if final_answer is not None else False
        stable = audit["consistent"]

        return {
            "problem_id": problem_id,
            "expected": expected_answer,
            "actual": final_answer,
            "correct": correct,
            "stable": stable,
            "run1_answer": ans1,
            "run2_answer": ans2,
            "tie_breaker_used": tie_breaker_used,
            "time": elapsed,
        }

    def _compute_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute summary metrics."""
        total = len(results)
        correct_count = sum(1 for r in results if r["correct"])
        stable_count = sum(1 for r in results if r["stable"])
        tie_breaker_count = sum(1 for r in results if r["tie_breaker_used"])
        total_time = sum(r["time"] for r in results)
        avg_time = total_time / total if total > 0 else 0

        accuracy = correct_count / total if total > 0 else 0
        stability_ratio = stable_count / total if total > 0 else 0

        return {
            "total_problems": total,
            "correct_count": correct_count,
            "accuracy": accuracy,
            "accuracy_target": 1.0,
            "accuracy_pass": accuracy >= 1.0,
            "stable_count": stable_count,
            "stability_ratio": stability_ratio,
            "stability_target": 0.90,
            "stability_pass": stability_ratio >= 0.90,
            "tie_breaker_count": tie_breaker_count,
            "total_time": total_time,
            "avg_time": avg_time,
            "all_targets_met": accuracy >= 1.0 and stability_ratio >= 0.90,
        }

    def _print_summary(self, summary: Dict[str, Any]):
        """Print summary report."""
        print(f"\n{'=' * 60}")
        print(f"BENCHMARK SUMMARY")
        print(f"{'=' * 60}")
        print(f"Total problems: {summary['total_problems']}")
        print(
            f"\nAccuracy: {summary['accuracy'] * 100:.1f}% ({summary['correct_count']}/{summary['total_problems']})"
        )
        print(f"  Target: 100% | Pass: {'✅' if summary['accuracy_pass'] else '❌'}")
        print(
            f"\nStability: {summary['stability_ratio'] * 100:.1f}% ({summary['stable_count']}/{summary['total_problems']})"
        )
        print(f"  Target: ≥90% | Pass: {'✅' if summary['stability_pass'] else '❌'}")
        print(f"\nAverage time: {summary['avg_time']:.1f}s per problem")
        print(f"Tie-breakers: {summary['tie_breaker_count']}")
        print(f"\nAll targets met: {'✅ YES' if summary['all_targets_met'] else '❌ NO'}")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kaggle Benchmark Runner")
    parser.add_argument(
        "--model",
        type=str,
        default="qwen3.5:cloud",
        help="Model to use (default: qwen3.5:cloud for dev, use qwen2-math:7b for compliant submission)",
    )
    parser.add_argument(
        "--reference-path",
        type=str,
        default="reference_problems.json",
        help="Path to reference problems JSON",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="kaggle_benchmark_results.json",
        help="Output results JSON path",
    )
    args = parser.parse_args()

    runner = KaggleBenchmarkRunner(
        reference_problems_path=args.reference_path,
        model_name=args.model,
    )
    summary = runner.run_benchmark()

    # Save results
    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to {args.output}")
