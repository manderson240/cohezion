#!/usr/bin/env python3
"""Safeguarded GPU Saturation Benchmark - With System Protection.

Tests concurrency levels 4-8 to find true GPU saturation point.
Includes: timeouts, abort thresholds, system responsiveness checks.

Guardrails:
- Max benchmark duration: 300s per concurrency level
- System responsiveness check between rounds
- GPU temp limit: 85°C (abort if exceeded)
- Auto-abort if TPS degrades >20% from previous successful run
- Pre-heat cooldown between tests
"""

import asyncio
import signal
import subprocess
import sys
import time
from dataclasses import dataclass

import aiohttp


@dataclass
class BenchmarkResult:
    concurrency: int
    tps: float
    total_tokens: int
    wall_time_ms: float
    success: bool
    aborted: bool = False
    reason: str = ""


class SafeguardedBenchmark:
    """Benchmark runner with safety guardrails."""

    def __init__(self):
        self.max_temp = 85.0  # Abort if GPU exceeds
        self.max_duration = 300.0  # Max 5 min per test
        self.min_responsiveness = 2.0  # Max 2s for system ping
        self.rollback_threshold = 0.8  # Abort if TPS < 80% of best
        self.best_result: float | None = None

    def check_temperature(self) -> tuple[bool, float]:
        """Check GPU temperature. Returns (safe, temp)."""
        try:
            result = subprocess.run(["rocm-smi", "-t"], capture_output=True, text=True, timeout=5)
            # Parse temperature from output
            for line in result.stdout.split("\n"):
                if "Temperature" in line:
                    # Extract number from line like "Temperature: 65.0°C"
                    temp_str = line.split(":")[1].strip().rstrip("°C").strip()
                    temp = float(temp_str)
                    return temp < self.max_temp, temp
            return True, 0.0
        except Exception:
            return True, 0.0  # Proceed if can't read temp

    def system_responsive(self) -> bool:
        """Check system responsiveness with quick ping."""
        try:
            result = subprocess.run(
                ["rocm-smi"], capture_output=True, timeout=self.min_responsiveness
            )
            return True
        except subprocess.TimeoutExpired:
            print("  ⚠️  WARNING: System responsiveness degraded", file=sys.stderr)
            return False
        return True

    def cooldown(self, seconds: int = 10):
        """Cooldown period between tests."""
        print(f"  Cooling down ({seconds}s)...")
        for i in range(seconds, 0, -1):
            print(f"    {i}s remaining...", end="\r", flush=True)
            time.sleep(1)
        print(" " * 30)  # Clear line

    async def benchmark_concurrency(
        self,
        concurrency: int,
        num_requests: int = 4,
    ) -> BenchmarkResult:
        """Benchmark specific concurrency level with safeguards."""

        print(f"\n{'=' * 60}")
        print(f"Testing concurrency={concurrency}")
        print(f"{'=' * 60}")

        # Pre-flight safety checks
        temp_safe, temp = self.check_temperature()
        if not temp_safe:
            return BenchmarkResult(
                concurrency=concurrency,
                tps=0,
                total_tokens=0,
                wall_time_ms=0,
                success=False,
                aborted=True,
                reason=f"GPU temperature too high ({temp:.1f}°C > {self.max_temp}°C)",
            )

        if not self.system_responsive():
            return BenchmarkResult(
                concurrency=concurrency,
                tps=0,
                total_tokens=0,
                wall_time_ms=0,
                success=False,
                aborted=True,
                reason="System not responsive before test",
            )

        print(f"  Pre-flight: Temp={temp:.1f}°C, System responsive ✓")

        # Run benchmark with timeout
        start_time = time.monotonic()
        try:
            result = await asyncio.wait_for(
                self._run_inference(concurrency, num_requests), timeout=self.max_duration
            )
        except TimeoutError:
            return BenchmarkResult(
                concurrency=concurrency,
                tps=0,
                total_tokens=0,
                wall_time_ms=0,
                success=False,
                aborted=True,
                reason=f"Timeout after {self.max_duration}s",
            )

        elapsed = time.monotonic() - start_time
        wall_time_ms = elapsed * 1000

        # Check results
        if not result["success"]:
            return BenchmarkResult(
                concurrency=concurrency,
                tps=0,
                total_tokens=0,
                wall_time_ms=wall_time_ms,
                success=False,
                aborted=True,
                reason="Inference failures",
            )

        tps = result["tps"]

        # Check against rollback threshold
        if self.best_result and tps < self.best_result * self.rollback_threshold:
            return BenchmarkResult(
                concurrency=concurrency,
                tps=tps,
                total_tokens=result["total_tokens"],
                wall_time_ms=wall_time_ms,
                success=True,
                aborted=True,
                reason=f"TPS degraded {tps / self.best_result * 100:.1f}% from best",
            )

        # Update best result
        if not self.best_result or tps > self.best_result:
            self.best_result = tps

        # Final temperature check
        temp_safe, final_temp = self.check_temperature()
        print(f"  Post-test: Temp={final_temp:.1f}°C")

        return BenchmarkResult(
            concurrency=concurrency,
            tps=tps,
            total_tokens=result["total_tokens"],
            wall_time_ms=wall_time_ms,
            success=True,
        )

    async def _run_inference(
        self,
        concurrency: int,
        num_requests: int,
    ) -> dict:
        """Run actual inference test."""

        base_url = "http://localhost:8002"

        # Detect model
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{base_url}/v1/models", timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m.get("id") for m in data.get("data", [])]
                        model = models[0] if models else "DeepSeek-Qwen3-8B-GGUF"
                    else:
                        model = "DeepSeek-Qwen3-8B-GGUF"
            except:
                model = "DeepSeek-Qwen3-8B-GGUF"

        prompts = [f"Write a haiku about ML topic {i % 100}." for i in range(num_requests)]

        connector = aiohttp.TCPConnector(limit=concurrency * 2)

        async with aiohttp.ClientSession(connector=connector) as session:
            # Warm-up (single request)
            try:
                await session.post(
                    f"{base_url}/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": "Say ready"}],
                        "max_tokens": 10,
                    },
                    timeout=aiohttp.ClientTimeout(total=30),
                )
            except Exception:
                pass

            # Run concurrent requests
            start = time.monotonic()
            tasks = []
            for prompt in prompts[:concurrency]:
                tasks.append(
                    session.post(
                        f"{base_url}/v1/chat/completions",
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": "You are helpful."},
                                {"role": "user", "content": prompt},
                            ],
                            "max_tokens": 40,
                            "temperature": 0.7,
                        },
                        timeout=aiohttp.ClientTimeout(total=120),
                    )
                )

            responses = await asyncio.gather(*tasks, return_exceptions=True)
            wall_time = (time.monotonic() - start) * 1000

            # Process results
            total_tokens = 0
            success_count = 0
            for resp in responses:
                if isinstance(resp, Exception):
                    continue
                if hasattr(resp, "json"):
                    try:
                        data = await resp.json()
                        usage = data.get("usage", {})
                        total_tokens += usage.get("completion_tokens", 0)
                        success_count += 1
                    except:
                        pass

            tps = total_tokens / (wall_time / 1000) if wall_time > 0 else 0

            return {
                "success": success_count == concurrency,
                "tps": tps,
                "total_tokens": total_tokens,
                "wall_time_ms": wall_time,
            }

    async def run_safeguarded_sweep(
        self,
        concurrency_levels: list[int] = [4, 5, 6, 7, 8],
    ):
        """Run full sweep with safeguards."""

        print("=" * 70)
        print("GUARDED GPU SATURATION ANALYSIS")
        print("=" * 70)
        print(f"Testing: {concurrency_levels}")
        print("Guardrails:")
        print(f"  - Max temp: {self.max_temp}°C")
        print(f"  - Max duration: {self.max_duration}s per test")
        print(f"  - Rollback threshold: {self.rollback_threshold * 100:.0f}% of best")
        print("  - Cooldown between tests: 10s")
        print("=" * 70)

        results = []

        for level in concurrency_levels:
            result = await self.benchmark_concurrency(level)
            results.append(result)

            # Report
            if result.aborted:
                print(f"\n  ⚠️  ABORTED: {result.reason}")
                break
            else:
                print(
                    f"\n  ✓ Complete: {result.tps:.1f} TPS, "
                    f"{result.total_tokens} tokens, "
                    f"{result.wall_time_ms / 1000:.2f}s"
                )

            # Cooldown before next level
            if level != concurrency_levels[-1]:
                self.cooldown(10)

        # Summary
        print("\n" + "=" * 70)
        print("RESULTS SUMMARY")
        print("=" * 70)
        print(f"{'N':>3} {'TPS':>10} {'Time':>10} {'Status':>20}")
        print("-" * 70)

        for r in results:
            status = "ABORTED" if r.aborted else "COMPLETE"
            print(f"{r.concurrency:>3} {r.tps:>10.1f} {r.wall_time_ms / 1000:>9.2f}s {status:>20}")

        # Find optimal
        complete = [r for r in results if not r.aborted]
        if complete:
            best = max(complete, key=lambda x: x.tps)
            print(f"\nOptimal: concurrency={best.concurrency} at {best.tps:.1f} TPS")
            print("Previously: concurrency=4 at 138.9 TPS")

        print("=" * 70)


async def main():
    benchmark = SafeguardedBenchmark()

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\n\nReceived interrupt - stopping gracefully...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    await benchmark.run_safeguarded_sweep([4, 5, 6, 7, 8])


if __name__ == "__main__":
    asyncio.run(main())
