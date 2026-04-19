"""
Performance Profiler - Optimize for 5-Hour Limit (Story 4.1)

Profiles execution time per problem and enforces time budgeting.
Target: ≤165s per problem for 110 problems within 5 hours.
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class PerformanceMetrics:
    """Performance metrics for a single problem."""

    problem_id: str
    total_time: float
    routing_time: float
    run1_time: float
    run2_time: float
    audit_time: float
    tie_breaker_time: float = 0.0
    memory_mb: float = 0.0
    success: bool = True


class PerformanceProfiler:
    """
    Profiles swarm execution to ensure 5-hour time budget compliance.

    Target: 110 problems × 165s = 18,150s (5.04 hours with safety margin)
    """

    def __init__(self, total_time_limit: float = 5 * 3600, problem_count: int = 110):
        self.total_time_limit = total_time_limit
        self.problem_count = problem_count
        self.time_per_problem = total_time_limit / problem_count  # ~163.6s
        self.metrics_log: List[PerformanceMetrics] = []
        self.start_time = time.time()
        self.problems_solved = 0

    def start_problem(self, problem_id: str) -> Dict[str, float]:
        """Start timing for a problem."""
        return {
            "problem_start": time.time(),
            "routing_start": time.time(),
        }

    def end_routing(self, timings: Dict[str, float]) -> Dict[str, float]:
        """End routing timing."""
        timings["routing_end"] = time.time()
        timings["run1_start"] = time.time()
        return timings

    def end_run1(self, timings: Dict[str, float]) -> Dict[str, float]:
        """End Run 1 timing."""
        timings["run1_end"] = time.time()
        timings["run2_start"] = time.time()
        return timings

    def end_run2(self, timings: Dict[str, float]) -> Dict[str, float]:
        """End Run 2 timing."""
        timings["run2_end"] = time.time()
        timings["audit_start"] = time.time()
        return timings

    def end_audit(self, timings: Dict[str, float]) -> Dict[str, float]:
        """End audit timing."""
        timings["audit_end"] = time.time()
        timings["problem_end"] = time.time()
        return timings

    def record_metrics(
        self,
        problem_id: str,
        timings: Dict[str, float],
        tie_breaker: bool = False,
        success: bool = True,
    ) -> PerformanceMetrics:
        """Record performance metrics for a problem."""
        total_time = timings["problem_end"] - timings["problem_start"]
        routing_time = timings["routing_end"] - timings["routing_start"]
        run1_time = timings["run1_end"] - timings["run1_start"]
        run2_time = timings["run2_end"] - timings["run2_start"]
        audit_time = timings["audit_end"] - timings["audit_start"]

        if tie_breaker:
            tie_breaker_time = timings.get("tie_breaker_end", 0) - timings.get(
                "tie_breaker_start", 0
            )
        else:
            tie_breaker_time = 0.0

        metrics = PerformanceMetrics(
            problem_id=problem_id,
            total_time=total_time,
            routing_time=routing_time,
            run1_time=run1_time,
            run2_time=run2_time,
            audit_time=audit_time,
            tie_breaker_time=tie_breaker_time,
            success=success,
        )

        self.metrics_log.append(metrics)
        self.problems_solved += 1

        return metrics

    def check_time_budget(self) -> Dict[str, Any]:
        """Check if we're within time budget."""
        elapsed = time.time() - self.start_time
        remaining_time = self.total_time_limit - elapsed
        remaining_problems = self.problem_count - self.problems_solved

        if remaining_problems > 0:
            required_pace = remaining_time / remaining_problems
        else:
            required_pace = float("inf")

        avg_time = sum(m.total_time for m in self.metrics_log) / max(1, len(self.metrics_log))

        return {
            "elapsed": elapsed,
            "remaining_time": remaining_time,
            "problems_solved": self.problems_solved,
            "remaining_problems": remaining_problems,
            "required_pace": required_pace,
            "avg_time": avg_time,
            "on_track": avg_time <= self.time_per_problem,
            "time_per_problem_target": self.time_per_problem,
        }

    def generate_report(self) -> str:
        """Generate performance report."""
        if not self.metrics_log:
            return "No metrics recorded"

        total_time = sum(m.total_time for m in self.metrics_log)
        avg_time = total_time / len(self.metrics_log)
        max_time = max(m.total_time for m in self.metrics_log)
        min_time = min(m.total_time for m in self.metrics_log)

        tie_breaker_count = sum(1 for m in self.metrics_log if m.tie_breaker_time > 0)

        report = f"""
=== Performance Report ===
Problems solved: {self.problems_solved}/{self.problem_count}
Total time: {total_time:.1f}s ({total_time / 3600:.2f} hours)
Average time: {avg_time:.1f}s (target: {self.time_per_problem:.1f}s)
Max time: {max_time:.1f}s
Min time: {min_time:.1f}s
Tie-breakers: {tie_breaker_count}/{self.problems_solved}

Time Budget Status:
- Total budget: {self.total_time_limit / 3600:.1f} hours
- Elapsed: {time.time() - self.start_time:.1f}s
- Remaining: {self.total_time_limit - (time.time() - self.start_time):.1f}s
- On track: {"YES" if avg_time <= self.time_per_problem else "NO"}

Per-Component Breakdown:
- Routing: {sum(m.routing_time for m in self.metrics_log):.1f}s total
- Run 1: {sum(m.run1_time for m in self.metrics_log):.1f}s total
- Run 2: {sum(m.run2_time for m in self.metrics_log):.1f}s total
- Audit: {sum(m.audit_time for m in self.metrics_log):.1f}s total
- Tie-breaker: {sum(m.tie_breaker_time for m in self.metrics_log):.1f}s total
"""
        return report

    def save_metrics(self, filepath: str = "sandbox/aimo/performance_metrics.json"):
        """Save metrics to JSON file."""
        data = {
            "metrics": [
                {
                    "problem_id": m.problem_id,
                    "total_time": m.total_time,
                    "routing_time": m.routing_time,
                    "run1_time": m.run1_time,
                    "run2_time": m.run2_time,
                    "audit_time": m.audit_time,
                    "tie_breaker_time": m.tie_breaker_time,
                    "success": m.success,
                }
                for m in self.metrics_log
            ],
            "summary": self.check_time_budget(),
        }

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Metrics saved to {filepath}")


if __name__ == "__main__":
    # Test profiler
    profiler = PerformanceProfiler()

    # Simulate problem execution
    timings = profiler.start_problem("test1")
    time.sleep(0.1)
    timings = profiler.end_routing(timings)
    time.sleep(0.5)
    timings = profiler.end_run1(timings)
    time.sleep(0.5)
    timings = profiler.end_run2(timings)
    time.sleep(0.1)
    timings = profiler.end_audit(timings)

    profiler.record_metrics("test1", timings)

    print(profiler.generate_report())
    print(f"Time budget check: {profiler.check_time_budget()}")
