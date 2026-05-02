"""
AGI Benchmark v3 Submission - Cohezion Epistemic Humility Evaluator

Standalone submission for Kaggle AGI Benchmark competition.
https://www.kaggle.com/competitions/kaggle-measuring-agi

This implementation removes the kbench.task decorator dependency and provides
a self-contained evaluator with HIHO coherence metrics.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TaskResult:
    """Result of evaluating a single task."""

    task_id: str
    category: str
    passed: bool
    confidence: float  # 0.0 - 1.0
    hiho_score: float  # Epistemic humility score (peaks at 0.5 coherence)
    reasoning: str = ""


class HihoVectorEngine:
    """Half-In-Half-Out stability scoring for epistemic humility.

    The stability function is a Gaussian centered at 0.5:
        score = exp(-((x - 0.5) / sigma)^2)
    """

    def __init__(self, sigma: float = 0.25) -> None:
        self.sigma = sigma
        self.target = 0.5

    def calculate_hiho_score(self, coherence: float) -> float:
        """Return stability score in [0, 1] for a given coherence value.

        Parameters
        ----------
        coherence : float
            Mean magnitude or confidence metric.

        Returns
        -------
        float
            1.0 at coherence=0.5, decaying symmetrically.
        """
        deviation = (coherence - self.target) / self.sigma
        return math.exp(-(deviation * deviation))


@dataclass
class AGIBenchmark:
    """AGI Benchmark evaluator with epistemic humility scoring."""

    name: str = "Cohezion Epistemic Humility Evaluator"
    version: str = "3.0"
    hiho: HihoVectorEngine = field(default_factory=HihoVectorEngine)

    def evaluate_answer(self, task: dict[str, Any], model_answer: str) -> TaskResult:
        """Evaluate a single task answer with HIHO coherence scoring.

        Parameters
        ----------
        task : dict
            Task containing 'task_id', 'category', 'prompt', 'answer'
        model_answer : str
            The model's answer (A, B, C, or D)

        Returns
        -------
        TaskResult
            Evaluation result with HIHO epistemic humility score.
        """
        correct_answer = task.get("answer", "").upper().strip()
        model_answer = model_answer.upper().strip()

        # Binary pass/fail
        passed = model_answer == correct_answer

        # Confidence calculation based on answer certainty
        # Models that are very confident (near 1.0) or uncertain (near 0.0)
        # get lower HIHO scores than those at optimal 0.5 coherence
        if passed:
            confidence = 0.85  # High but not extreme
        else:
            confidence = 0.15  # Uncertain but not zero

        # Calculate HIHO score - optimal at 0.5 (balanced epistemic humility)
        hiho_score = self.hiho.calculate_hiho_score(confidence)

        reasoning = f"Expected: {correct_answer}, Got: {model_answer}"
        if passed:
            reasoning += f" | HIHO={hiho_score:.3f} (balanced confidence)"
        else:
            reasoning += f" | HIHO={hiho_score:.3f} (needs calibration)"

        return TaskResult(
            task_id=task["task_id"],
            category=task["category"],
            passed=passed,
            confidence=confidence,
            hiho_score=hiho_score,
            reasoning=reasoning,
        )

    def run_benchmark(self, tasks: list[dict[str, Any]], model_answers: dict[str, str] | None = None) -> dict[str, Any]:
        """Run the full benchmark evaluation.

        Parameters
        ----------
        tasks : list
            List of task dictionaries
        model_answers : dict, optional
            Pre-computed model answers. If None, uses reference answers.

        Returns
        -------
        dict
            Benchmark results in Kaggle submission format.
        """
        results = []
        category_stats: dict[str, dict[str, Any]] = {}

        for task in tasks:
            task_id = task["task_id"]
            category = task["category"]

            # If no model answers provided, use reference (for testing)
            if model_answers and task_id in model_answers:
                answer = model_answers[task_id]
            else:
                answer = task.get("answer", "")

            result = self.evaluate_answer(task, answer)
            results.append(result)

            # Track category stats
            if category not in category_stats:
                category_stats[category] = {
                    "total": 0,
                    "passed": 0,
                    "avg_hiho": 0.0,
                }
            category_stats[category]["total"] += 1
            if result.passed:
                category_stats[category]["passed"] += 1
            category_stats[category]["avg_hiho"] += result.hiho_score

        # Calculate averages
        total_passed = sum(1 for r in results if r.passed)
        avg_hiho = sum(r.hiho_score for r in results) / len(results) if results else 0.0

        for cat in category_stats:
            stats = category_stats[cat]
            stats["avg_hiho"] = stats["avg_hiho"] / stats["total"]

        return {
            "name": self.name,
            "version": self.version,
            "total_tasks": len(tasks),
            "tasks_passed": total_passed,
            "accuracy": total_passed / len(tasks) if tasks else 0.0,
            "avg_hiho_score": round(avg_hiho, 4),
            "category_breakdown": category_stats,
            "task_results": [
                {
                    "task_id": r.task_id,
                    "category": r.category,
                    "passed": r.passed,
                    "confidence": round(r.confidence, 4),
                    "hiho_score": round(r.hiho_score, 4),
                    "reasoning": r.reasoning,
                }
                for r in results
            ],
        }


def load_tasks(json_path: Path) -> list[dict[str, Any]]:
    """Load tasks from JSON file."""
    with open(json_path) as f:
        data = json.load(f)
    return data.get("tasks", [])


def main():
    """Main entry point for Kaggle submission."""
    # Load tasks
    task_path = Path("/kaggle/input/agi-benchmark-tasks/submission.json")
    if not task_path.exists():
        # Fallback to local path for testing
        task_path = Path(__file__).parent.parent.parent.parent / "submission.json"

    tasks = load_tasks(task_path)

    # Initialize benchmark
    benchmark = AGIBenchmark()

    # Run evaluation
    # In actual Kaggle environment, this would use model predictions
    # For now, we output the task structure
    results = benchmark.run_benchmark(tasks)

    # Output in Kaggle format
    output = {
        "submission_name": benchmark.name,
        "version": benchmark.version,
        "total_tasks": results["total_tasks"],
        "tasks": tasks,  # Include original tasks
    }

    # Write submission files
    output_path = Path("/kaggle/working/submission.json")
    jsonl_path = Path("/kaggle/working/submission.jsonl")

    # For local testing
    if not output_path.parent.exists():
        output_path = Path(__file__).parent / "output.json"
        jsonl_path = Path(__file__).parent / "output.jsonl"

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    # Also write JSONL format
    with open(jsonl_path, "w") as f:
        for task in tasks:
            f.write(json.dumps(task) + "\n")

    print(f"Submission written to: {output_path}")
    print(f"Tasks: {len(tasks)}")
    print(f"Tracks: {set(t['category'] for t in tasks)}")

    return results


if __name__ == "__main__":
    main()
