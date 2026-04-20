"""
Epic 6 Benchmark Runner - Testing & Validation

Runs the complete swarm pipeline on reference problems and measures:
- Accuracy (correct / total) - Target: 100% (10/10)
- Stability (consistent / total) - Target: ≥0.90
- Performance (time per problem) - Target: ≤165s
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from base_specialist import BaseSpecialist
from flume_navigator import FLUMEProfilerNavigator
from knower_auditor import KnowerAuditor
from performance_profiler import PerformanceProfiler
from swarm_coordinator import SwarmCoordinator


@dataclass
class BenchmarkResult:
    problem_id: str
    expected_answer: int
    actual_answer: int
    correct: bool
    stable: bool
    run1_answer: int
    run2_answer: int
    tie_breaker_used: bool
    time_seconds: float
    reasoning_chain: str


class Epic6BenchmarkRunner:
    """
    Runs Epic 6 validation tests on reference problems.

    Targets:
    - Accuracy: 100% (10/10 reference problems)
    - Stability: ≥0.90 dual-run consistency
    - Performance: ≤165s per problem
    """

    def __init__(self, reference_problems_path: str = "reference_problems.json"):
        self.reference_problems = self._load_problems(reference_problems_path)
        self.coordinator = SwarmCoordinator()
        self.auditor = KnowerAuditor()
        self.profiler = PerformanceProfiler()
        self.flume = FLUMEProfilerNavigator()

        self.results: List[BenchmarkResult] = []
        self.start_time = time.time()

    def _load_problems(self, path: str) -> List[Dict[str, Any]]:
        """Load reference problems from JSON."""
        with open(path, "r") as f:
            return json.load(f)

    def run_benchmark(self, problem_ids: List[str] = None) -> Dict[str, Any]:
        """
        Run benchmark on specified problems (or all if None).

        Returns summary metrics.
        """
        if problem_ids is None:
            problems = self.reference_problems
        else:
            problems = [p for p in self.reference_problems if p["id"] in problem_ids]

        print(f"=== Epic 6 Benchmark Runner ===")
        print(f"Running {len(problems)} reference problems...")
        print()

        for problem in problems:
            result = self._run_single_problem(problem)
            self.results.append(result)

            print(
                f"[{result.problem_id}] "
                f"Expected: {result.expected_answer}, "
                f"Actual: {result.actual_answer}, "
                f"Correct: {result.correct}, "
                f"Time: {result.time_seconds:.1f}s"
            )

        print()
        summary = self._compute_summary()
        self._print_summary(summary)

        return summary

    def _run_single_problem(self, problem: Dict[str, Any]) -> BenchmarkResult:
        """Run single problem through complete pipeline."""
        problem_start = time.time()

        problem_id = problem["id"]
        problem_text = problem["problem"]
        expected_answer = problem["answer"]

        # 1. Plan journey
        routing_start = time.time()
        task = self.coordinator.plan_journey(problem_id, problem_text)
        routing_end = time.time()

        # 2. Dual-run execution
        run1_start = time.time()
        specialist1 = BaseSpecialist(task.assigned_specialists[0])
        response1 = specialist1.solve(problem_text, keep_alive="1m")
        ans1 = specialist1.extract_answer(response1)
        run1_end = time.time()

        run2_start = time.time()
        spec2_name = (
            task.assigned_specialists[1]
            if len(task.assigned_specialists) > 1
            else task.assigned_specialists[0]
        )
        specialist2 = BaseSpecialist(spec2_name)
        response2 = specialist2.solve(problem_text, keep_alive="1m")
        ans2 = specialist2.extract_answer(response2)
        run2_end = time.time()

        # 3. Knower audit
        audit_start = time.time()
        audit = self.auditor.audit_runs([ans1, ans2], [response1, response2])
        audit_end = time.time()

        # 4. Tie-breaker if needed
        tie_breaker_used = False
        if audit["action"] == "TIE_BREAKER":
            tie_breaker_start = time.time()
            tie_specialist = BaseSpecialist(task.assigned_specialists[0], "phi4:latest")
            res3_text = tie_specialist.solve(problem_text, keep_alive="1m")
            res3 = tie_specialist.extract_answer(res3_text)
            final_answer = self.auditor.resolve_tie(ans1, ans2, res3)
            tie_breaker_end = time.time()
            tie_breaker_used = True

            # Record tie-breaker timing
            timings = {
                "problem_start": problem_start,
                "routing_start": routing_start,
                "routing_end": routing_end,
                "run1_start": run1_start,
                "run1_end": run1_end,
                "run2_start": run2_start,
                "run2_end": run2_end,
                "audit_start": audit_start,
                "audit_end": audit_end,
                "tie_breaker_start": tie_breaker_start,
                "tie_breaker_end": tie_breaker_end,
                "problem_end": tie_breaker_end,
            }
        else:
            final_answer = audit["final_answer"]
            timings = {
                "problem_start": problem_start,
                "routing_start": routing_start,
                "routing_end": routing_end,
                "run1_start": run1_start,
                "run1_end": run1_end,
                "run2_start": run2_start,
                "run2_end": run2_end,
                "audit_start": audit_start,
                "audit_end": audit_end,
                "problem_end": audit_end,
            }

        # Record metrics
        self.profiler.record_metrics(problem_id, timings, tie_breaker=tie_breaker_used)

        # Check correctness
        correct = final_answer == expected_answer
        stable = audit["consistent"]

        total_time = time.time() - problem_start

        # FLUME stability check
        chain1 = self.flume.encode_reasoning_chain(response1)
        chain2 = self.flume.encode_reasoning_chain(response2)
        flume_stable = self.flume.check_stability(chain1, chain2)

        return BenchmarkResult(
            problem_id=problem_id,
            expected_answer=expected_answer,
            actual_answer=final_answer,
            correct=correct,
            stable=stable and flume_stable,
            run1_answer=ans1,
            run2_answer=ans2,
            tie_breaker_used=tie_breaker_used,
            time_seconds=total_time,
            reasoning_chain=response1[:200] + "..." if len(response1) > 200 else response1,
        )

    def _compute_summary(self) -> Dict[str, Any]:
        """Compute summary metrics."""
        if not self.results:
            return {"error": "No results"}

        total = len(self.results)
        correct_count = sum(1 for r in self.results if r.correct)
        stable_count = sum(1 for r in self.results if r.stable)
        tie_breaker_count = sum(1 for r in self.results if r.tie_breaker_used)
        total_time = sum(r.time_seconds for r in self.results)
        avg_time = total_time / total

        accuracy = correct_count / total
        stability_ratio = stable_count / total

        return {
            "total_problems": total,
            "correct_count": correct_count,
            "accuracy": accuracy,
            "accuracy_target": 1.0,
            "accuracy_pass": accuracy >= 1.0,  # 100% target
            "stable_count": stable_count,
            "stability_ratio": stability_ratio,
            "stability_target": 0.90,
            "stability_pass": stability_ratio >= 0.90,
            "tie_breaker_count": tie_breaker_count,
            "tie_breaker_ratio": tie_breaker_count / total,
            "total_time": total_time,
            "avg_time": avg_time,
            "time_target": 165.0,
            "time_pass": avg_time <= 165.0,
            "all_targets_met": accuracy >= 1.0 and stability_ratio >= 0.90 and avg_time <= 165.0,
        }

    def _print_summary(self, summary: Dict[str, Any]):
        """Print summary report."""
        print("=== Epic 6 Benchmark Summary ===")
        print(f"Total problems: {summary['total_problems']}")
        print()
        print(
            f"Accuracy: {summary['accuracy'] * 100:.1f}% ({summary['correct_count']}/{summary['total_problems']})"
        )
        print(f"  Target: 100% | Pass: {'✅' if summary['accuracy_pass'] else '❌'}")
        print()
        print(
            f"Stability: {summary['stability_ratio'] * 100:.1f}% ({summary['stable_count']}/{summary['total_problems']})"
        )
        print(f"  Target: ≥90% | Pass: {'✅' if summary['stability_pass'] else '❌'}")
        print()
        print(f"Performance: {summary['avg_time']:.1f}s per problem")
        print(f"  Target: ≤165s | Pass: {'✅' if summary['time_pass'] else '❌'}")
        print()
        print(
            f"Tie-breakers: {summary['tie_breaker_count']} ({summary['tie_breaker_ratio'] * 100:.1f}%)"
        )
        print()
        print(f"All targets met: {'✅ YES' if summary['all_targets_met'] else '❌ NO'}")
        print()

        # Per-problem breakdown
        print("=== Per-Problem Results ===")
        for result in self.results:
            status = "✅" if result.correct else "❌"
            stable = "S" if result.stable else "U"
            tb = "TB" if result.tie_breaker_used else ""
            print(
                f"{status} {result.problem_id}: {result.actual_answer} (expected {result.expected_answer}) | {stable} | {tb} | {result.time_seconds:.1f}s"
            )

    def save_results(self, filepath: str = "sandbox/aimo/epic6_benchmark_results.json"):
        """Save benchmark results to JSON."""
        data = {
            "results": [
                {
                    "problem_id": r.problem_id,
                    "expected_answer": r.expected_answer,
                    "actual_answer": r.actual_answer,
                    "correct": r.correct,
                    "stable": r.stable,
                    "run1_answer": r.run1_answer,
                    "run2_answer": r.run2_answer,
                    "tie_breaker_used": r.tie_breaker_used,
                    "time_seconds": r.time_seconds,
                }
                for r in self.results
            ],
            "summary": self._compute_summary(),
        }

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Results saved to {filepath}")


if __name__ == "__main__":
    from dataclasses import dataclass

    runner = Epic6BenchmarkRunner()
    summary = runner.run_benchmark()
    runner.save_results()
