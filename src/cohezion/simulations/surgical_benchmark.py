import asyncio
import time
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class SurgicalRegimeBenchmark:
    """Surgical benchmark that tests ONE regime at a time with shorter prompts."""

    def __init__(self):
        self.results: Dict[str, Any] = {}

    async def benchmark_regime_atomic(
        self, regime: str, model: str, prompt: str, timeout: float = 60.0
    ) -> Optional[Dict[str, Any]]:
        """Benchmark a single regime with timeout."""
        logger.info(f"🔬 Testing {regime} regime with {model}...")

        try:
            from cohezion.swarm.providers.gemma4_provider import Gemma4Provider

            provider = Gemma4Provider(config={})

            start_time = time.perf_counter()

            # Use asyncio.wait_for to enforce timeout
            res = await asyncio.wait_for(
                provider.generate(model=model, prompt=prompt, regime=regime), timeout=timeout
            )

            end_time = time.perf_counter()
            latency = end_time - start_time
            tokens = len(res.response) // 4

            result = {
                "regime": regime,
                "model": model,
                "latency": latency,
                "tokens": tokens,
                "tok_per_sec": tokens / latency if latency > 0 else 0,
                "success": True,
                "error": None,
            }

            logger.info(f"✅ {regime} completed: {latency:.3f}s, {tokens} tokens")
            return result

        except asyncio.TimeoutError:
            logger.error(f"❌ {regime} timed out after {timeout}s")
            return {
                "regime": regime,
                "model": model,
                "latency": timeout,
                "tokens": 0,
                "tok_per_sec": 0,
                "success": False,
                "error": f"timeout_{timeout}s",
            }
        except Exception as e:
            logger.error(f"❌ {regime} failed: {e}")
            return {
                "regime": regime,
                "model": model,
                "latency": 0,
                "tokens": 0,
                "tok_per_sec": 0,
                "success": False,
                "error": str(e),
            }

    async def run_single(self, regime: str, model: str, prompt: str) -> Dict[str, Any]:
        """Run a single regime benchmark."""
        logger.info(f"=== Testing {regime} Regime ===")

        # Baseline
        baseline = await self.benchmark_regime_atomic(regime, model, prompt, timeout=45.0)

        # SOTA (with optimizations)
        sota = await self.benchmark_regime_atomic(
            regime, model, prompt + " (optimized)", timeout=45.0
        )

        return {"regime": regime, "baseline": baseline, "sota": sota}

    async def run_all(self):
        """Run all regime benchmarks sequentially."""
        logger.info("=== Surgical Regime Benchmark Starting ===")

        # Define regimes with ultra-short prompts
        regimes = [
            ("SENSING", "gemma4:2b", "Analyze data."),
            ("CALCULATION", "gemma4:4b", "Calculate sum."),
            ("SYNTHESIS", "gemma4:4b", "Synthesize data."),
            ("STEERING", "gemma4:2b", "Optimize path."),
        ]

        results = {}

        for regime, model, prompt in regimes:
            result = await self.run_single(regime, model, prompt)
            results[regime] = result

            # Small delay between tests
            await asyncio.sleep(2)

        return results

    def save_results(self, results: Dict[str, Any], output_path: Path):
        """Save benchmark results to JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(results, f, indent=4)

        logger.info(f"✅ Results saved to {output_path}")

        # Print summary table
        print("\n" + "═" * 70)
        print(f"{'Regime':<15} | {'Status':<10} | {'Baseline (s)':<15} | {'SOTA (s)':<15}")
        print("═" * 70)
        for regime, data in results.items():
            baseline = data.get("baseline", {})
            sota = data.get("sota", {})
            b_latency = baseline.get("latency", 0) if baseline.get("success") else "FAILED"
            s_latency = sota.get("latency", 0) if sota.get("success") else "FAILED"
            status = "✅" if baseline.get("success") else "❌"
            print(f"{regime:<15} | {status:<10} | {str(b_latency):<15} | {str(s_latency):<15}")
        print("═" * 70)


async def main():
    benchmark = SurgicalRegimeBenchmark()
    results = await benchmark.run_all()

    output_path = Path("data/benchmarks/regime_baseline.json")
    benchmark.save_results(results, output_path)


if __name__ == "__main__":
    asyncio.run(main())
