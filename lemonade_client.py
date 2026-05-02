#!/usr/bin/env python3
"""Production Lemonade Client - Optimized for maximum throughput.

Implements the empirically-determined optimal configuration:
- Optimal concurrency: 4 requests (from experiments #200-206)
- Batching strategy: explicit batches of 4 for >4 requests
- Connection pooling: keep-alive with 300s timeout
- Raw asyncio.gather() - no queue/worker overhead

Usage:
    client = LemonadeClient()

    # Single request (≤4 concurrent optimal)
    result = await client.generate("prompt")

    # Multiple requests (auto-batched)
    results = await client.generate_batch(["p1", "p2", "p3", "p4", "p5"])
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import aiohttp


@dataclass
class GenerationResult:
    """Result from a generation request."""

    content: str
    tokens: int
    latency_ms: float
    success: bool
    error: str | None = None


class LemonadeClient:
    """Production-optimized client for Lemonade inference server.

    Optimized for AMD Ryzen AI MAX+ 395 with Lemonade Vulkan backend.
    Throughput: 125-139 TPS burst, ~107 TPS sustained.
    """

    # Empirically-determined optimal settings (experiments #200-206)
    OPTIMAL_CONCURRENCY = 4  # Sweet spot from scaling curve
    KEEPALIVE_TIMEOUT = 300  # seconds

    def __init__(
        self,
        base_url: str = "http://localhost:13307",
        timeout: float = 120.0,
        optimal_concurrency: int = 4,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.optimal_concurrency = optimal_concurrency

        # Persistent connection pool
        self._connector = aiohttp.TCPConnector(
            limit=optimal_concurrency * 3,
            limit_per_host=optimal_concurrency * 3,
            keepalive_timeout=self.KEEPALIVE_TIMEOUT,
        )
        self._session: aiohttp.ClientSession | None = None
        self._model: str | None = None

    async def __aenter__(self) -> LemonadeClient:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args) -> None:
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """Establish connection pool and detect model."""
        if self._session is None:
            self._session = aiohttp.ClientSession(connector=self._connector)
            await self._detect_model()

    async def close(self) -> None:
        """Close connection pool."""
        if self._session:
            await self._session.close()
            self._session = None

    async def _detect_model(self) -> None:
        """Auto-detect available model from server."""
        if not self._session:
            return

        try:
            async with self._session.get(
                f"{self.base_url}/v1/models", timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = [m.get("id", m.get("name")) for m in data.get("data", [])]
                    self._model = models[0] if models else "gemma-4-26B-A4B"
        except Exception:
            self._model = "gemma-4-26B-A4B"

    async def generate(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        model: str | None = None,
        max_tokens: int = 128,
        temperature: float = 0.7,
    ) -> GenerationResult:
        """Execute a single generation request."""
        await self.connect()

        model = model or self._model or "gemma-4-26B-A4B"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        start = time.monotonic()
        try:
            async with self._session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                elapsed_ms = (time.monotonic() - start) * 1000

                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                tokens = usage.get("completion_tokens", len(content.split()))

                return GenerationResult(
                    content=content,
                    tokens=tokens,
                    latency_ms=elapsed_ms,
                    success=True,
                )
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            return GenerationResult(
                content="",
                tokens=0,
                latency_ms=elapsed_ms,
                success=False,
                error=str(e),
            )

    async def generate_batch(
        self,
        prompts: list[str],
        system: str = "You are a helpful assistant.",
        model: str | None = None,
        max_tokens: int = 128,
        temperature: float = 0.7,
        show_progress: bool = False,
    ) -> list[GenerationResult]:
        """Execute multiple requests with optimal batching.

        For ≤4 requests: single concurrent batch
        For >4 requests: explicit batching with gather() per batch

        Args:
            prompts: List of prompts to process
            system: System prompt for all requests
            model: Model to use (auto-detected if None)
            max_tokens: Max tokens per generation
            temperature: Sampling temperature
            show_progress: Print progress to stderr

        Returns:
            List of GenerationResult (same order as prompts)
        """
        if not prompts:
            return []

        await self.connect()
        model = model or self._model or "gemma-4-26B-A4B"

        # Small batches (≤optimal): single gather
        if len(prompts) <= self.optimal_concurrency:
            tasks = [self.generate(p, system, model, max_tokens, temperature) for p in prompts]
            return await asyncio.gather(*tasks)

        # Large batches: explicit batching
        results: list[GenerationResult] = []

        for i in range(0, len(prompts), self.optimal_concurrency):
            batch = prompts[i : i + self.optimal_concurrency]

            if show_progress:
                print(
                    f"Processing batch {i // self.optimal_concurrency + 1}/"
                    f"{(len(prompts) + self.optimal_concurrency - 1) // self.optimal_concurrency}...",
                    file=__import__("sys").stderr,
                )

            tasks = [self.generate(p, system, model, max_tokens, temperature) for p in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

        return results

    async def benchmark(
        self,
        num_requests: int = 4,
        max_tokens: int = 40,
    ) -> dict[str, Any]:
        """Run quick throughput benchmark.

        Returns:
            Dict with tokens_per_sec, total_time_ms, total_tokens, etc.
        """
        prompts = [f"Write a haiku about machine learning topic {i}." for i in range(num_requests)]

        start = time.monotonic()
        results = await self.generate_batch(prompts, max_tokens=max_tokens)
        total_ms = (time.monotonic() - start) * 1000

        total_tokens = sum(r.tokens for r in results if r.success)
        successful = sum(1 for r in results if r.success)

        tps = total_tokens / (total_ms / 1000) if total_ms > 0 else 0

        return {
            "tokens_per_sec": tps,
            "total_time_ms": total_ms,
            "total_tokens": total_tokens,
            "successful": successful,
            "num_requests": num_requests,
            "avg_latency_ms": sum(r.latency_ms for r in results) / len(results) if results else 0,
        }


# Simple CLI for testing
async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Lemonade Client")
    parser.add_argument("--benchmark", "-b", action="store_true", help="Run benchmark")
    parser.add_argument("--requests", "-n", type=int, default=4)
    parser.add_argument("prompt", nargs="?", help="Single prompt to process")
    args = parser.parse_args()

    async with LemonadeClient() as client:
        if args.benchmark:
            print(f"Running benchmark with {args.requests} requests...")
            result = await client.benchmark(args.requests)
            print("\nResults:")
            print(f"  Throughput:   {result['tokens_per_sec']:.1f} TPS")
            print(f"  Total time:   {result['total_time_ms']:.1f} ms")
            print(f"  Total tokens: {result['total_tokens']}")
            print(f"  Successful:   {result['successful']}/{result['num_requests']}")
        elif args.prompt:
            result = await client.generate(args.prompt)
            if result.success:
                print(result.content)
            else:
                print(f"Error: {result.error}", file=__import__("sys").stderr)
                return 1
        else:
            print("Usage: lemonade_client.py --benchmark [-n N] | <prompt>")
            return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
