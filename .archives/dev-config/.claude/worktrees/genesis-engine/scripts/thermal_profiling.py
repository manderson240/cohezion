#!/usr/bin/env python3
"""Thermal profiling for Phase 5A.5 - Find optimal batch size and concurrency limit.

Measures token/sec and GPU utilization across different configurations:
- Batch sizes: 1, 2, 4, 8, 16
- Concurrency limits: 1, 2, 4, 6, 8
- Models: phi3:mini (lightweight), qwen3-coder:30b (heavy)

Expected curve:
- 1 core: 30-40 tok/sec (underutilized)
- 4 parallel: 80-100 tok/sec (optimal)
- 8 parallel: 120-140 tok/sec (approaching thermal)
- 16 parallel: 130-140 tok/sec (thermal throttle)

Usage::

    python scripts/thermal_profiling.py --batch-sizes 1,2,4,8,16 --concurrency 1,2,4,6,8
    python scripts/thermal_profiling.py --lightweight  # Fast profiling (phi3:mini)
    python scripts/thermal_profiling.py --full         # Full profiling (all configs)
"""

import argparse
import asyncio
import json
import logging
import time
from pathlib import Path

import numpy as np

from cohezion.concurrency.ollama_gate import get_gate, reset_gate
from cohezion.core.config import CohezionConfig
from cohezion.observability.gpu_monitor import GPUMonitor
from cohezion.swarm.batch_processor import BatchItem
from cohezion.swarm.token_client import TokenEfficientClient


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class ThermalProfiler:
    """Profile token efficiency across batch sizes and concurrency limits."""

    def __init__(self, output_dir: str = "research/thermal_profiling"):
        """Initialize profiler.

        Args:
            output_dir: Directory for results (JSON + plots)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = []
        self.config = CohezionConfig()

    async def profile_configuration(
        self,
        batch_size: int,
        concurrency_limit: int,
        model: str = "phi3:mini",
        num_iterations: int = 3,
    ) -> dict:
        """Profile a single batch size / concurrency configuration.

        Args:
            batch_size: Items per batch
            concurrency_limit: Max concurrent Ollama calls
            model: Model to use (phi3:mini or qwen3-coder:30b)
            num_iterations: Number of iterations to average

        Returns:
            Dict with profiling results
        """
        logger.info(f"Profiling: batch_size={batch_size}, concurrency={concurrency_limit}, model={model}")

        # Reset gate with new concurrency limit
        reset_gate()
        get_gate(max_concurrent=concurrency_limit)

        # Initialize client
        client = TokenEfficientClient(config=self.config)

        iteration_results = []

        for iteration in range(num_iterations):
            logger.debug(f"  Iteration {iteration + 1}/{num_iterations}")

            # Clear caches between iterations
            client.clear_cache()

            # Create batch items
            items = [
                BatchItem(
                    id=f"item_{i}",
                    prompt=f"Explain quantum computing in {10 + i} words",
                    system="You are a helpful assistant.",
                    model=model,
                )
                for i in range(batch_size)
            ]

            # Collect metrics
            monitor = GPUMonitor()
            monitor.start_measurement()
            start_time = time.time()

            # Execute batch
            try:
                await client.batch_generate(items)
            except Exception as e:
                logger.error(f"Batch execution failed: {e}")
                monitor.stop_measurement()
                continue

            elapsed = time.time() - start_time
            monitor.stop_measurement()

            gpu_stats = monitor.get_statistics()
            client_metrics = client.get_metrics()

            # Compute throughput
            total_tokens = client_metrics.get("total_tokens", 0)
            tokens_per_sec = total_tokens / elapsed if elapsed > 0 else 0

            result = {
                "iteration": iteration + 1,
                "elapsed_seconds": round(elapsed, 2),
                "total_tokens": total_tokens,
                "tokens_per_second": round(tokens_per_sec, 2),
                "avg_gpu_load": round(gpu_stats["avg_gpu_load"], 1),
                "peak_gpu_load": round(gpu_stats["peak_gpu_load"], 1),
                "avg_temperature": round(gpu_stats["avg_temperature"], 1),
                "peak_temperature": round(gpu_stats["peak_temperature"], 1),
                "thermal_throttled": gpu_stats["thermal_throttled"],
                "cache_hit_rate": round(client_metrics.get("combined_hit_rate", 0), 3),
            }
            iteration_results.append(result)
            logger.debug(
                f"    {tokens_per_sec:.1f} tok/sec, "
                f"{gpu_stats['avg_gpu_load']:.1f}% GPU, "
                f"{gpu_stats['avg_temperature']:.1f}°C"
            )

        # Aggregate results
        if iteration_results:
            tokens_per_sec_list = [r["tokens_per_second"] for r in iteration_results]
            gpu_load_list = [r["avg_gpu_load"] for r in iteration_results]
            temp_list = [r["avg_temperature"] for r in iteration_results]

            aggregate = {
                "batch_size": batch_size,
                "concurrency_limit": concurrency_limit,
                "model": model,
                "num_iterations": num_iterations,
                "avg_tokens_per_second": round(np.mean(tokens_per_sec_list), 2),
                "std_tokens_per_second": round(np.std(tokens_per_sec_list), 2),
                "min_tokens_per_second": round(np.min(tokens_per_sec_list), 2),
                "max_tokens_per_second": round(np.max(tokens_per_sec_list), 2),
                "avg_gpu_load": round(np.mean(gpu_load_list), 1),
                "peak_gpu_load": round(np.max([r["peak_gpu_load"] for r in iteration_results]), 1),
                "avg_temperature": round(np.mean(temp_list), 1),
                "peak_temperature": round(np.max([r["peak_temperature"] for r in iteration_results]), 1),
                "thermal_throttled": any(r["thermal_throttled"] for r in iteration_results),
                "iterations": iteration_results,
            }
        else:
            aggregate = {
                "batch_size": batch_size,
                "concurrency_limit": concurrency_limit,
                "model": model,
                "error": "No successful iterations",
                "iterations": [],
            }

        return aggregate

    async def run_profiling(
        self,
        batch_sizes: list[int],
        concurrency_limits: list[int],
        models: list[str],
    ) -> None:
        """Run full profiling across all configurations.

        Args:
            batch_sizes: List of batch sizes to test
            concurrency_limits: List of concurrency limits to test
            models: List of models to test
        """
        logger.info("=" * 60)
        logger.info("THERMAL PROFILING - Phase 5A.5")
        logger.info("=" * 60)

        total_configs = len(batch_sizes) * len(concurrency_limits) * len(models)
        config_num = 0

        for model in models:
            logger.info(f"\nTesting model: {model}")
            logger.info("-" * 60)

            for concurrency in concurrency_limits:
                for batch_size in batch_sizes:
                    config_num += 1
                    logger.info(f"[{config_num}/{total_configs}] Batch {batch_size}, Concurrency {concurrency}")

                    result = await self.profile_configuration(
                        batch_size=batch_size,
                        concurrency_limit=concurrency,
                        model=model,
                        num_iterations=3,
                    )
                    self.results.append(result)

        # Save results
        self._save_results()
        self._print_summary()

    def _save_results(self) -> None:
        """Save results to JSON file."""
        output_file = self.output_dir / "thermal_profiling_results.json"
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"\nResults saved to: {output_file}")

    def _print_summary(self) -> None:
        """Print summary of profiling results."""
        logger.info("\n" + "=" * 60)
        logger.info("PROFILING SUMMARY")
        logger.info("=" * 60)

        # Group by model
        models = {r["model"] for r in self.results if "model" in r}

        for model in sorted(models):
            logger.info(f"\n{model}:")
            logger.info("-" * 60)
            logger.info(
                f"{'Batch':<8} {'Concurrency':<12} {'Tok/Sec':<12} {'GPU Load':<12} {'Temp°C':<10} {'Throttle':<10}"
            )
            logger.info("-" * 60)

            results_for_model = [r for r in self.results if r.get("model") == model]

            for result in sorted(
                results_for_model,
                key=lambda x: (x.get("batch_size", 0), x.get("concurrency_limit", 0)),
            ):
                if "error" in result:
                    logger.info(f"{result['batch_size']:<8} {result['concurrency_limit']:<12} ERROR: {result['error']}")
                    continue

                batch = result.get("batch_size", 0)
                concurrency = result.get("concurrency_limit", 0)
                throughput = result.get("avg_tokens_per_second", 0)
                gpu_load = result.get("avg_gpu_load", 0)
                temp = result.get("avg_temperature", 0)
                throttled = "YES" if result.get("thermal_throttled") else "NO"

                logger.info(
                    f"{batch:<8} {concurrency:<12} {throughput:<12.1f} {gpu_load:<12.1f}% {temp:<10.1f} {throttled:<10}"
                )

        # Recommendations
        logger.info("\n" + "=" * 60)
        logger.info("RECOMMENDATIONS")
        logger.info("=" * 60)

        # Find optimal configuration (max throughput without throttle)
        non_throttled = [
            r for r in self.results if not r.get("thermal_throttled", False) and "avg_tokens_per_second" in r
        ]

        if non_throttled:
            best = max(non_throttled, key=lambda x: x["avg_tokens_per_second"])
            logger.info(
                f"\n✓ Optimal configuration (max throughput without throttle):"
                f"\n  Batch: {best['batch_size']}, "
                f"Concurrency: {best['concurrency_limit']}"
                f"\n  Throughput: {best['avg_tokens_per_second']} tok/sec"
                f"\n  GPU Load: {best['avg_gpu_load']}%"
                f"\n  Temperature: {best['avg_temperature']}°C"
            )

        # Find max throughput (may throttle)
        all_results = [r for r in self.results if "avg_tokens_per_second" in r]
        if all_results:
            peak = max(all_results, key=lambda x: x["avg_tokens_per_second"])
            logger.info(
                f"\n✓ Peak throughput configuration (may throttle):"
                f"\n  Batch: {peak['batch_size']}, "
                f"Concurrency: {peak['concurrency_limit']}"
                f"\n  Throughput: {peak['avg_tokens_per_second']} tok/sec"
                f"\n  Temperature: {peak['avg_temperature']}°C"
                f"\n  Throttled: {'YES' if peak.get('thermal_throttled') else 'NO'}"
            )

        logger.info("\n" + "=" * 60)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Thermal profiling for Phase 5A.5")
    parser.add_argument(
        "--batch-sizes",
        type=str,
        default="1,2,4,8,16",
        help="Comma-separated batch sizes",
    )
    parser.add_argument(
        "--concurrency",
        type=str,
        default="1,2,4,6,8",
        help="Comma-separated concurrency limits",
    )
    parser.add_argument(
        "--models",
        type=str,
        default="phi3:mini",
        help="Comma-separated model names",
    )
    parser.add_argument(
        "--lightweight",
        action="store_true",
        help="Fast profiling: batch_sizes=1,2,4, concurrency=1,4, model=phi3:mini",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full profiling: all batch sizes, all concurrency levels, both models",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="research/thermal_profiling",
        help="Output directory for results",
    )

    args = parser.parse_args()

    # Parse arguments
    if args.lightweight:
        batch_sizes = [1, 2, 4]
        concurrency_limits = [1, 4]
        models = ["phi3:mini"]
        logger.info("Running lightweight profiling (fast)")
    elif args.full:
        batch_sizes = [int(x) for x in args.batch_sizes.split(",")]
        concurrency_limits = [int(x) for x in args.concurrency.split(",")]
        models = args.models.split(",")
        logger.info("Running full profiling (slow)")
    else:
        batch_sizes = [int(x) for x in args.batch_sizes.split(",")]
        concurrency_limits = [int(x) for x in args.concurrency.split(",")]
        models = args.models.split(",")

    logger.info(f"Batch sizes: {batch_sizes}")
    logger.info(f"Concurrency limits: {concurrency_limits}")
    logger.info(f"Models: {models}")

    profiler = ThermalProfiler(output_dir=args.output_dir)
    await profiler.run_profiling(batch_sizes, concurrency_limits, models)


if __name__ == "__main__":
    asyncio.run(main())
