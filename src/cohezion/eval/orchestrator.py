"""BenchmarkOrchestrator for coordinating multi-benchmark evaluations.

Orchestrates runs across HumanEval, SWE-bench, and AgentBench with support
for parallel execution, result aggregation, and model comparison.
"""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

from cohezion.eval.agentbench.harness import AgentBenchHarness
from cohezion.eval.humaneval.harness import HumanEvalHarness
from cohezion.eval.results.tracker import BenchmarkTracker
from cohezion.eval.swebench.harness import SWEBenchHarness


logger = logging.getLogger(__name__)


class BenchmarkConfig:
    """Configuration for a single benchmark run."""

    def __init__(
        self,
        benchmark: str,
        dataset: str | None = None,
        limit: int | None = None,
        num_samples: int = 1,
        temperature: float = 0.2,
        timeout: int = 1800,
        max_workers: int = 8,
        environments: list[str] | None = None,
    ):
        """Initialize benchmark configuration.

        Args:
            benchmark: Benchmark name (humaneval, swebench, agentbench)
            dataset: Dataset variant (e.g., 'lite' for SWE-bench)
            limit: Limit number of instances for testing
            num_samples: Number of samples per problem (HumanEval)
            temperature: Sampling temperature (HumanEval)
            timeout: Timeout per instance in seconds (SWE-bench)
            max_workers: Parallel workers (SWE-bench)
            environments: Environments to test (AgentBench)
        """
        self.benchmark = benchmark
        self.dataset = dataset
        self.limit = limit
        self.num_samples = num_samples
        self.temperature = temperature
        self.timeout = timeout
        self.max_workers = max_workers
        self.environments = environments


class BenchmarkResult:
    """Result from a single benchmark run."""

    def __init__(
        self,
        benchmark: str,
        model_name: str,
        success: bool,
        metrics: dict[str, Any],
        error: str | None = None,
        duration_seconds: float | None = None,
    ):
        """Initialize benchmark result.

        Args:
            benchmark: Benchmark name
            model_name: Model identifier
            success: Whether run completed successfully
            metrics: Result metrics
            error: Error message if failed
            duration_seconds: Run duration
        """
        self.benchmark = benchmark
        self.model_name = model_name
        self.success = success
        self.metrics = metrics
        self.error = error
        self.duration_seconds = duration_seconds
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "benchmark": self.benchmark,
            "model_name": self.model_name,
            "success": self.success,
            "metrics": self.metrics,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp,
        }


class BenchmarkOrchestrator:
    """Orchestrates multi-benchmark evaluations.

    Coordinates runs across HumanEval, SWE-bench, and AgentBench with support
    for parallel execution, result aggregation, and model comparison.

    Example:
        >>> orchestrator = BenchmarkOrchestrator(results_dir="data/eval")
        >>> config = BenchmarkConfig("humaneval", limit=10)
        >>> result = await orchestrator.run_single("gpt-4", config)
        >>> results = orchestrator.compare_models(["gpt-4", "claude-3"])
    """

    BENCHMARKS: ClassVar[set[str]] = {"humaneval", "swebench", "agentbench"}

    def __init__(
        self,
        results_dir: str = "data/eval",
        tracker: BenchmarkTracker | None = None,
    ):
        """Initialize orchestrator.

        Args:
            results_dir: Base directory for all benchmark results
            tracker: Optional BenchmarkTracker instance
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.tracker = tracker or BenchmarkTracker()

        self._harnesses: dict[str, Any] = {}

    def _get_harness(
        self,
        benchmark: str,
        config: BenchmarkConfig,
    ) -> Any:
        """Get or create harness for benchmark.

        Args:
            benchmark: Benchmark name
            config: Benchmark configuration

        Returns:
            Harness instance

        Raises:
            ValueError: If benchmark not supported
        """
        if benchmark == "humaneval":
            return HumanEvalHarness(
                results_dir=str(self.results_dir / "humaneval"),
            )
        elif benchmark == "swebench":
            return SWEBenchHarness(
                dataset_name=config.dataset or "lite",
                max_workers=config.max_workers,
                results_dir=str(self.results_dir / "swebench"),
            )
        elif benchmark == "agentbench":
            return AgentBenchHarness(
                environments=config.environments,
                results_dir=str(self.results_dir / "agentbench"),
            )
        else:
            raise ValueError(f"Unsupported benchmark: {benchmark}")

    async def run_single(
        self,
        model_name: str,
        config: BenchmarkConfig,
        agent_factory: Any,
    ) -> BenchmarkResult:
        """Run a single benchmark.

        Args:
            model_name: Model identifier
            config: Benchmark configuration
            agent_factory: Factory to create agent instances

        Returns:
            Benchmark result
        """
        start_time = datetime.now()
        benchmark = config.benchmark

        logger.info(f"Running {benchmark} for model: {model_name}")

        try:
            harness = self._get_harness(benchmark, config)
            metrics = await self._run_benchmark(
                harness, benchmark, model_name, config, agent_factory
            )

            duration = (datetime.now() - start_time).total_seconds()
            result = BenchmarkResult(
                benchmark=benchmark,
                model_name=model_name,
                success=True,
                metrics=metrics,
                duration_seconds=duration,
            )

            self._record_result(result)
            logger.info(f"Completed {benchmark}: {model_name} in {duration:.1f}s")

            return result

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Failed {benchmark} for {model_name}: {e}")

            return BenchmarkResult(
                benchmark=benchmark,
                model_name=model_name,
                success=False,
                metrics={},
                error=str(e),
                duration_seconds=duration,
            )

    async def _run_benchmark(
        self,
        harness: Any,
        benchmark: str,
        model_name: str,
        config: BenchmarkConfig,
        agent_factory: Any,
    ) -> dict[str, Any]:
        """Execute benchmark with given harness.

        Args:
            harness: Benchmark harness instance
            benchmark: Benchmark name
            model_name: Model identifier
            config: Benchmark configuration
            agent_factory: Agent factory

        Returns:
            Metrics dictionary
        """
        if benchmark == "humaneval":
            solutions_path = harness.generate_solutions(
                model_name=model_name,
                agent_factory=agent_factory,
                num_samples=config.num_samples,
                temperature=config.temperature,
            )
            return harness.evaluate(solutions_path)

        elif benchmark == "swebench":
            predictions_path = harness.generate_predictions(
                model_name=model_name,
                agent_factory=agent_factory,
                limit=config.limit,
            )
            return harness.evaluate(
                predictions_path=predictions_path,
                timeout=config.timeout,
            )

        elif benchmark == "agentbench":
            return harness.run_evaluation(
                model_name=model_name,
                agent_factory=agent_factory,
                limit_per_env=config.limit,
            )

        raise ValueError(f"Unknown benchmark: {benchmark}")

    async def run_parallel(
        self,
        model_name: str,
        configs: list[BenchmarkConfig],
        agent_factory: Any,
        max_parallel: int = 3,
    ) -> list[BenchmarkResult]:
        """Run multiple benchmarks in parallel.

        Args:
            model_name: Model identifier
            configs: List of benchmark configurations
            agent_factory: Factory to create agent instances
            max_parallel: Maximum concurrent benchmark runs

        Returns:
            List of benchmark results
        """
        logger.info(f"Running {len(configs)} benchmarks in parallel for {model_name}")

        results: list[BenchmarkResult] = []

        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            futures = {
                executor.submit(
                    self.run_single, model_name, config, agent_factory
                ): config
                for config in configs
            }

            for future in as_completed(futures):
                config = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Benchmark {config.benchmark} failed: {e}")
                    results.append(
                        BenchmarkResult(
                            benchmark=config.benchmark,
                            model_name=model_name,
                            success=False,
                            metrics={},
                            error=str(e),
                        )
                    )

        return results

    async def compare_models(
        self,
        model_names: list[str],
        benchmark_configs: dict[str, BenchmarkConfig],
        agent_factory_fn: Callable[[str], Any],
    ) -> dict[str, dict[str, BenchmarkResult]]:
        """Compare multiple models across benchmarks.

        Args:
            model_names: List of model identifiers
            benchmark_configs: Dict mapping benchmark name to config
            agent_factory_fn: Function that takes model_name and returns agent

        Returns:
            Dict mapping model_name to benchmark_name to result
        """
        logger.info(f"Comparing models: {model_names}")

        comparison: dict[str, dict[str, BenchmarkResult]] = {}

        for model_name in model_names:
            comparison[model_name] = {}
            agent_factory = agent_factory_fn(model_name)

            for benchmark_name, _config in benchmark_configs.items():
                logger.info(f"Running {benchmark_name} for {model_name}")

                result = await self.run_single(model_name, _config, agent_factory)
                comparison[model_name][benchmark_name] = result

        return comparison

    def aggregate_results(
        self,
        results: list[BenchmarkResult],
    ) -> dict[str, Any]:
        """Aggregate results across benchmarks.

        Args:
            results: List of benchmark results

        Returns:
            Aggregated metrics
        """
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        by_benchmark: dict[str, list[BenchmarkResult]] = {}
        for result in results:
            if result.benchmark not in by_benchmark:
                by_benchmark[result.benchmark] = []
            by_benchmark[result.benchmark].append(result)

        summary: dict[str, Any] = {
            "total_runs": len(results),
            "successful_runs": len(successful),
            "failed_runs": len(failed),
            "success_rate": len(successful) / len(results) if results else 0,
            "by_benchmark": {},
            "total_duration_seconds": sum(r.duration_seconds or 0 for r in results),
        }

        for benchmark, bench_results in by_benchmark.items():
            bench_successful = [r for r in bench_results if r.success]

            summary["by_benchmark"][benchmark] = {
                "runs": len(bench_results),
                "successful": len(bench_successful),
                "success_rate": (
                    len(bench_successful) / len(bench_results) if bench_results else 0
                ),
                "metrics": [r.metrics for r in bench_successful if r.metrics],
            }

        return summary

    def generate_comparison_report(
        self,
        comparison: dict[str, dict[str, BenchmarkResult]],
    ) -> str:
        """Generate comparison report markdown.

        Args:
            comparison: Model comparison results

        Returns:
            Markdown report
        """
        report = "# Model Comparison Report\n\n"
        report += f"Generated: {datetime.now().isoformat()}\n\n"

        benchmarks = set()
        for bench_results in comparison.values():
            benchmarks.update(bench_results.keys())

        report += "## Summary\n\n"
        report += "| Model | " + " | ".join(benchmarks) + " | Status |\n"
        report += "|-------|" + "|".join(["---"] * len(benchmarks)) + "|-------|\n"

        for model_name, bench_results in comparison.items():
            statuses = []
            for benchmark in benchmarks:
                result = bench_results.get(benchmark)
                if result and result.success:
                    statuses.append("✓")
                elif result:
                    statuses.append("✗")
                else:
                    statuses.append("-")

            report += f"| {model_name} | " + " | ".join(statuses) + " | |\n"

        report += "\n## Detailed Metrics\n\n"

        for model_name, bench_results in comparison.items():
            report += f"### {model_name}\n\n"

            for benchmark, result in bench_results.items():
                report += f"#### {benchmark}\n\n"

                if result.success:
                    report += f"Status: Success ({result.duration_seconds:.1f}s)\n\n"

                    if benchmark == "humaneval" and "pass_at_k" in result.metrics:
                        pak = result.metrics["pass_at_k"]
                        report += f"- pass@1: {pak.get('pass@1', 0):.1%}\n"
                        report += f"- pass@10: {pak.get('pass@10', 0):.1%}\n"
                        report += f"- pass@100: {pak.get('pass@100', 0):.1%}\n"

                    elif (
                        benchmark == "swebench" and "resolution_rate" in result.metrics
                    ):
                        rr = result.metrics["resolution_rate"]
                        report += f"- Resolution Rate: {rr:.1%}\n"

                    elif benchmark == "agentbench" and "summary" in result.metrics:
                        summary = result.metrics["summary"]
                        report += (
                            f"- Overall: {summary.get('overall_success_rate', 0):.1%}\n"
                        )

                        for env, rate in summary.get("per_environment", {}).items():
                            report += f"  - {env}: {rate:.1%}\n"
                else:
                    report += f"Status: Failed - {result.error}\n"

                report += "\n"

        output_path = self.results_dir / "comparison_report.md"
        with open(output_path, "w") as f:
            f.write(report)

        logger.info(f"Comparison report saved to {output_path}")

        return report

    def _record_result(self, result: BenchmarkResult) -> None:
        """Record result to tracker.

        Args:
            result: Benchmark result
        """
        if not result.success:
            return

        try:
            if result.benchmark == "humaneval":
                pass_at_k = result.metrics.get("pass_at_k", {})
                self.tracker.record_humaneval(
                    model_name=result.model_name,
                    pass_at_k=pass_at_k,
                    details=result.metrics,
                )

            elif result.benchmark == "swebench":
                self.tracker.record_swebench(
                    model_name=result.model_name,
                    resolution_rate=result.metrics.get("resolution_rate", 0),
                    dataset=result.metrics.get("dataset", "unknown"),
                    details=result.metrics,
                )

            elif result.benchmark == "agentbench":
                summary = result.metrics.get("summary", {})
                self.tracker.record_agentbench(
                    model_name=result.model_name,
                    overall_rate=summary.get("overall_success_rate", 0),
                    per_environment=summary.get("per_environment", {}),
                    details=result.metrics,
                )
        except Exception as e:
            logger.warning(f"Failed to record result: {e}")

    def get_available_benchmarks(self) -> dict[str, Any]:
        """Get information about available benchmarks.

        Returns:
            Benchmark information
        """
        return {
            "humaneval": {
                "name": "HumanEval",
                "description": "Code generation benchmark (164 problems)",
                "primary_metric": "pass@1",
            },
            "swebench": {
                "name": "SWE-bench",
                "description": "Software engineering benchmark (real GitHub issues)",
                "primary_metric": "resolution_rate",
                "datasets": list(SWEBenchHarness.DATASETS.keys()),
            },
            "agentbench": {
                "name": "AgentBench",
                "description": "Multi-environment agent evaluation (8 environments)",
                "primary_metric": "overall_success_rate",
                "environments": list(AgentBenchHarness.ENVIRONMENTS.keys()),
            },
        }
