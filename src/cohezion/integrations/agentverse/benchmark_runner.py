"""AgentVerseBenchmarkRunner - Run AgentVerse benchmarks with Cohezion metrics.

Runs AgentVerse task-solving benchmarks and captures Cohezion coherence
metrics for skill enhancement and refinement triggering.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.core.mcp_client import MCPClient

logger = logging.getLogger(__name__)

REFINEMENT_THRESHOLD = 0.5


@dataclass
class BenchmarkResult:
    """Result from a single benchmark task execution."""

    task: str
    skill: str
    success: bool
    metrics: dict[str, Any]
    duration_seconds: float = 0.0


@dataclass
class AgentVerseBenchmarkRunner:
    """Runner for AgentVerse benchmarks with Cohezion coherence tracking.

    Enables running AgentVerse task-solving benchmarks (HumanEval, tool use,
    etc.) while capturing Cohezion-specific metrics like coherence,
    alignment, and skill refinement triggers.

    Parameters
    ----------
    executor : Any
        CompoundExecutor instance for task execution
    mcp_client : MCPClient
        MCP client for vault persistence
    cohezion_skills : list[str], optional
        List of Cohezion skill names to benchmark

    Attributes
    ----------
    results : list[BenchmarkResult]
        Results from benchmark executions
    """

    executor: Any
    mcp_client: MCPClient
    cohezion_skills: list[str] = field(default_factory=list)
    results: list[BenchmarkResult] = field(default_factory=list)

    def run_single_task(
        self,
        task_description: str,
        skill_name: str,
    ) -> BenchmarkResult:
        """Run a single benchmark task.

        Parameters
        ----------
        task_description : str
            Description of the task to execute
        skill_name : str
            Cohezion skill to use

        Returns
        -------
        BenchmarkResult
            Result of the benchmark execution
        """
        logger.info(
            "Running benchmark task: %s with skill %s",
            task_description[:50],
            skill_name,
        )

        result = self.executor.execute_task(
            task_description=task_description,
            skill_name=skill_name,
            operation_type="generate",
        )

        benchmark_result = BenchmarkResult(
            task=task_description,
            skill=skill_name,
            success=result.success,
            metrics=result.metrics,
            duration_seconds=result.duration_seconds,
        )

        self.results.append(benchmark_result)
        return benchmark_result

    def run_batch_benchmark(
        self,
        tasks: list[dict[str, str]],
    ) -> list[BenchmarkResult]:
        """Run a batch of benchmark tasks.

        Parameters
        ----------
        tasks : list[dict[str, str]]
            List of dicts with 'task' and 'skill' keys

        Returns
        -------
        list[BenchmarkResult]
            Results from all task executions
        """
        logger.info("Running batch benchmark with %d tasks", len(tasks))

        for task_def in tasks:
            self.run_single_task(
                task_description=task_def["task"],
                skill_name=task_def["skill"],
            )

        return self.results

    def should_trigger_refinement(self, result: BenchmarkResult) -> bool:
        """Check if a result should trigger skill refinement.

        Parameters
        ----------
        result : BenchmarkResult
            Benchmark result to evaluate

        Returns
        -------
        bool
            True if refinement should be triggered
        """
        coherence = result.metrics.get("coherence", 0.5)
        return coherence < REFINEMENT_THRESHOLD or not result.success

    def get_skill_coherence_summary(self) -> dict[str, dict[str, Any]]:
        """Compute per-skill coherence summary.

        Returns
        -------
        dict[str, dict[str, Any]]
            Summary per skill with avg_coherence, count, success_rate
        """
        summary: dict[str, dict[str, Any]] = {}

        for result in self.results:
            if result.skill not in summary:
                summary[result.skill] = {
                    "coherences": [],
                    "count": 0,
                    "successes": 0,
                }

            summary[result.skill]["coherences"].append(result.metrics.get("coherence", 0.5))
            summary[result.skill]["count"] += 1
            if result.success:
                summary[result.skill]["successes"] += 1

        for _skill, data in summary.items():
            coherences = data["coherences"]
            data["avg_coherence"] = sum(coherences) / len(coherences) if coherences else 0.0
            data["success_rate"] = data["successes"] / data["count"] if data["count"] > 0 else 0.0
            del data["coherences"]

        return summary

    def identify_weak_skills(self, threshold: float = 0.5) -> list[str]:
        """Identify skills with below-threshold coherence.

        Parameters
        ----------
        threshold : float
            Coherence threshold (default 0.5)

        Returns
        -------
        list[str]
            List of skill names that need improvement
        """
        summary = self.get_skill_coherence_summary()
        weak = []

        for skill, data in summary.items():
            if data["avg_coherence"] < threshold:
                weak.append(skill)

        return weak

    def get_refinement_candidates(self) -> list[str]:
        """Get skills that are candidates for refinement.

        Returns
        -------
        list[str]
            Skills that failed or had low coherence
        """
        candidates = []

        for result in self.results:
            if self.should_trigger_refinement(result) and result.skill not in candidates:
                candidates.append(result.skill)

        return candidates

    def get_average_coherence(self) -> float:
        """Compute average coherence across all results.

        Returns
        -------
        float
            Average coherence score
        """
        if not self.results:
            return 0.0

        coherences = [r.metrics.get("coherence", 0.5) for r in self.results]
        return sum(coherences) / len(coherences) if coherences else 0.0

    def persist_results(self) -> str:
        """Persist benchmark results to vault.

        Returns
        -------
        str
            Path to persisted results
        """
        logger.info("Persisting %d benchmark results to vault", len(self.results))

        summary = self.get_skill_coherence_summary()
        refinement_candidates = self.get_refinement_candidates()

        data = {
            "n_results": len(self.results),
            "skill_summary": summary,
            "refinement_candidates": refinement_candidates,
            "results": [
                {
                    "task": r.task,
                    "skill": r.skill,
                    "success": r.success,
                    "coherence": r.metrics.get("coherence", 0.0),
                }
                for r in self.results
            ],
        }

        unique_id = uuid.uuid4().hex[:8]
        vault_path = f"/vault/benchmarks/agentverse_benchmark_{unique_id}.json"
        try:
            self.mcp_client.vault_write(vault_path, json.dumps(data, indent=2))
        except Exception as e:
            logger.warning("Failed to persist to vault: %s", e)
        return vault_path

    def load_historical_results(self) -> list[dict[str, Any]]:
        """Load historical benchmark results from vault.

        Returns
        -------
        list[dict[str, Any]]
            Historical benchmark results
        """
        results = []
        try:
            paths = self.mcp_client.vault_list(directory="/vault/benchmarks/", recursive=False)
            for vault_path in paths:
                if not vault_path.endswith(".json"):
                    continue
                try:
                    content = self.mcp_client.vault_read(vault_path)
                    results.append(json.loads(content))
                except Exception as e:
                    logger.debug("Failed to read vault file %s: %s", vault_path, e)
        except Exception as e:
            logger.debug("Failed to list vault benchmarks: %s", e)
        return results
