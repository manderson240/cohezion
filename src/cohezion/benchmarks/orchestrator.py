"""Cohezion Unified Benchmark Orchestrator.

Runs comprehensive benchmark suite matching Mythos Preview evaluation scope.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from cohezion.benchmarks.agentic_benchmark import AgenticBenchmark
from cohezion.benchmarks.coding_benchmark import CohezionCodeBenchmark
from cohezion.benchmarks.cyber_benchmark import CyberBenchmark


logger = logging.getLogger(__name__)


@dataclass
class BenchmarkSuiteResults:
    """Complete benchmark suite results."""

    timestamp: str
    overall_score: float
    coding: dict[str, Any]
    cyber: dict[str, Any]
    agentic: dict[str, Any]


class UnifiedBenchmarkOrchestrator:
    """Main benchmark orchestrator."""

    MYTHOS_TARGETS = {
        "coding_pass@1": 93.9,
        "cyber_solve": 100.0,
        "agentic_success": 79.6,
        "terminal_bench": 82.0,
        "usamo": 97.6,
    }

    def __init__(self, output_dir: Path | None = None):
        """Initialize orchestrator."""
        self.output_dir = output_dir or Path("benchmark_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.coding = CohezionCodeBenchmark()
        self.cyber = CyberBenchmark()
        self.agentic = AgenticBenchmark()

    async def run_full_suite(
        self, executor: Any, agent: Any | None = None, quick: bool = False
    ) -> BenchmarkSuiteResults:
        """Run complete benchmark suite."""

        logger.info("=" * 60)
        logger.info("COHEZION UNIFIED BENCHMARK SUITE")
        logger.info("=" * 60)

        # Coding benchmark
        logger.info("\n[1/3] Running Coding Benchmark...")
        coding_results = await self._run_coding(executor, quick)

        # Cyber benchmark
        logger.info("\n[2/3] Running Cyber Benchmark...")
        cyber_results = await self._run_cyber(executor, quick)

        # Agentic benchmark
        logger.info("\n[3/3] Running Agentic Benchmark...")
        if agent:
            agentic_results = await self._run_agentic(agent, quick)
        else:
            logger.warning("No agent provided - agentic benchmark skipped")
            agentic_results = {"status": "skipped", "reason": "no_agent"}

        # Compute composite score
        composite = self._compute_composite(coding_results, cyber_results, agentic_results)

        results = BenchmarkSuiteResults(
            timestamp=datetime.now().isoformat(),
            overall_score=composite,
            coding=coding_results,
            cyber=cyber_results,
            agentic=agentic_results,
        )

        # Save results
        await self._save_results(results)
        self._print_summary(results)

        return results

    async def _run_coding(self, executor: Any, quick: bool) -> dict[str, Any]:
        """Run coding benchmark."""
        n_tasks = 10 if quick else 50
        try:
            results = await self.coding.run_full_benchmark(executor=executor, n_tasks=n_tasks, parallel=True)
            return results
        except Exception as e:
            logger.error(f"Coding benchmark failed: {e}")
            return {"error": str(e), "status": "failed"}

    async def _run_cyber(self, executor: Any, quick: bool) -> dict[str, Any]:
        """Run cyber benchmark."""
        n_challenges = 5 if quick else 20
        try:
            results = await self.cyber.run_benchmark(executor=executor, n_challenges=n_challenges)
            return results
        except Exception as e:
            logger.error(f"Cyber benchmark failed: {e}")
            return {"error": str(e), "status": "failed"}

    async def _run_agentic(self, agent: Any, quick: bool) -> dict[str, Any]:
        """Run agentic benchmark."""
        n_tasks = 3 if quick else 10
        try:
            results = await self.agentic.run_benchmark(agent=agent, n_tasks=n_tasks)
            return results
        except Exception as e:
            logger.error(f"Agentic benchmark failed: {e}")
            return {"error": str(e), "status": "failed"}

    def _compute_composite(self, coding, cyber, agentic) -> float:
        """Compute weighted composite score."""
        scores = []

        if "overall" in coding:
            pass_at_1 = coding["overall"].get("pass_at_1", 0)
            scores.append(pass_at_1 / 0.939)  # vs Mythos

        if "overall" in cyber:
            solve_rate = cyber["overall"].get("solve_rate", 0)
            scores.append(solve_rate / 1.0)

        if "overall" in agentic:
            success = agentic["overall"].get("success_rate", 0)
            scores.append(success / 0.796)

        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    async def _save_results(self, results: BenchmarkSuiteResults) -> None:
        """Save results to disk."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"benchmark_{ts}.json"

        with open(output_file, "w") as f:
            json.dump(asdict(results), f, indent=2)

        logger.info(f"Results saved: {output_file}")

    def _print_summary(self, results: BenchmarkSuiteResults) -> None:
        """Print results summary."""
        print("\n" + "=" * 60)
        print("BENCHMARK RESULTS SUMMARY")
        print("=" * 60)
        score = results.overall_score
        pct = score * 100
        print(f"Overall Score: {pct:.1f}%")

        if "overall" in results.coding:
            c = results.coding["overall"]
            print("\nCoding:")
            c_pct = c.get("pass_at_1_percentage", 0)
            print(f"  Pass at 1: {c_pct:.1f}% (target: 93.9%)")
            c_tasks = c.get("total_tasks", 0)
            print(f"  Tasks: {c_tasks}")

        if "overall" in results.cyber:
            cy = results.cyber["overall"]
            print("\nCyber:")
            cy_pct = cy.get("solve_percentage", 0)
            print(f"  Solve Rate: {cy_pct:.1f}% (target: 100%)")
            cy_chal = cy.get("total_challenges", 0)
            print(f"  Challenges: {cy_chal}")

        if "overall" in results.agentic:
            a = results.agentic["overall"]
            print("\nAgentic:")
            a_pct = a.get("success_percentage", 0)
            print(f"  Success: {a_pct:.1f}% (target: 79.6%)")
            step_c = a.get("step_completion", 0)
            print(f"  Step Completion: {step_c:.1%}")

        print("\n" + "=" * 60)

    async def run_continuous(self, executor: Any, agent: Any, interval_hours: float = 1.0) -> None:
        """Run continuous benchmark loop."""
        while True:
            logger.info("Starting benchmark cycle...")
            await self.run_full_suite(executor, agent, quick=True)
            logger.info(f"Sleeping for {interval_hours} hours...")
            await asyncio.sleep(interval_hours * 3600)


orchestrator = UnifiedBenchmarkOrchestrator()
