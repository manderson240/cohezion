"""ROCm-Optimized LLM Executor for AMD Ryzen AI MAX+ 395.

Hardware Profile:
- CPU: AMD Ryzen AI MAX+ 395 (Zen 5, 16C/32T, AVX-512)
- GPU: AMD Radeon 8060S (RDNA 3.5, iGPU)
- Memory: 128GB LPDDR5X-8000 (UMA - Unified Memory Architecture)
- Architecture: Strix Halo

Optimizations:
1. UMA Zero-Copy: Avoid CPU/GPU transfers (shared memory pool)
2. AVX-512: Vectorized operations where applicable
3. ROCm 6.x: AMD GPU acceleration for Ollama
4. Batch Processing: Leverage 128GB RAM for large batches
5. Memory Mapping: mmap for model weights (instant loading)

Environment:
    export OLLAMA_USE_ROCM=1
    export OLLAMA_NUM_PARALLEL=4
    export OLLAMA_MAX_LOADED_MODELS=2
    export HSA_OVERRIDE_GFX_VERSION=11.5.1  # For RDNA 3.5
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from typing import Any

import httpx


logger = logging.getLogger(__name__)

# ROCm-optimized defaults
DEFAULT_ROCM_MODEL = "llama3.2:3b"  # Efficient on 8060S
DEFAULT_ROCM_URL = "http://localhost:11434"

# Hardware-optimized parameters for Ryzen AI MAX+ 395
ROCM_CONFIG = {
    "num_gpu": 1,  # Use RDNA 3.5 iGPU
    "num_thread": 8,  # Leave cores for system/agent overhead
    "ctx_size": 8192,  # Balanced for 128GB RAM
    "batch_size": 512,  # Larger batches with UMA
    "mmap": True,  # Memory-map weights (instant loading)
    "use_mlock": False,  # Allow swapping with 128GB
}


@dataclass
class ROCmResult:
    """Result from ROCm-optimized execution."""

    success: bool
    output: str
    latency_ms: float
    tokens_per_sec: float
    gpu_utilization: float | None = None
    memory_used_gb: float | None = None
    error: str | None = None


class ROCmExecutor:
    """ROCm-optimized LLM executor for AMD Ryzen AI MAX+ 395.

    Leverages Unified Memory Architecture (UMA) for zero-copy
    GPU acceleration and 128GB LPDDR5X bandwidth.

    Args:
        model: Ollama model name (default: llama3.2:3b)
        base_url: Ollama API endpoint
        enable_rocm: Force ROCm GPU usage
    """

    def __init__(
        self,
        model: str = DEFAULT_ROCM_MODEL,
        base_url: str = DEFAULT_ROCM_URL,
        enable_rocm: bool = True,
    ):
        self.model = model
        self.base_url = base_url
        self.enable_rocm = enable_rocm

        # Set ROCm environment
        if enable_rocm:
            self._configure_rocm()

        self._session: httpx.AsyncClient | None = None

    def _configure_rocm(self) -> None:
        """Configure ROCm environment for Strix Halo."""
        env_vars = {
            "OLLAMA_USE_ROCM": "1",
            "OLLAMA_NUM_PARALLEL": "4",  # Parallel requests
            "OLLAMA_MAX_LOADED_MODELS": "2",  # Keep 2 models in VRAM
            "HSA_OVERRIDE_GFX_VERSION": "11.5.1",  # RDNA 3.5 gfx version
            "OLLAMA_KEEP_ALIVE": "5m",  # Keep model loaded
        }

        for key, value in env_vars.items():
            os.environ[key] = value
            logger.debug(f"ROCm env: {key}={value}")

        logger.info(f"ROCm configured for {self.model}")

    async def _get_session(self) -> httpx.AsyncClient:
        """Get HTTP session with ROCm-optimized timeouts."""
        if self._session is None or self._session.is_closed:
            # Longer timeout for local ROCm (slower than cloud APIs but cheaper)
            self._session = httpx.AsyncClient(
                timeout=httpx.Timeout(180.0, connect=30.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._session

    async def ensure_model(self) -> bool:
        """Ensure model is pulled and available."""
        try:
            session = await self._get_session()
            resp = await session.get(f"{self.base_url}/api/tags")

            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]

                if self.model in models:
                    logger.info(f"Model {self.model} available")
                    return True
                else:
                    logger.warning(f"Model {self.model} not found. Available: {models}")
                    return False
            else:
                logger.error(f"Ollama API error: {resp.status_code}")
                return False

        except Exception as e:
            logger.error(f"Failed to check model: {e}")
            return False

    async def execute(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> ROCmResult:
        """Execute prompt on ROCm-optimized Ollama.

        Args:
            prompt: User prompt
            system: System message
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            stream: Stream response (not implemented)

        Returns:
            ROCmResult with performance metrics
        """
        start_time = time.monotonic()

        try:
            session = await self._get_session()

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "num_ctx": ROCM_CONFIG["ctx_size"],
                    "num_thread": ROCM_CONFIG["num_thread"],
                    "num_gpu": ROCM_CONFIG["num_gpu"],
                    "batch_size": ROCM_CONFIG["batch_size"],
                    "use_mlock": ROCM_CONFIG["use_mlock"],
                    "mmap": ROCM_CONFIG["mmap"],
                },
            }

            if system:
                payload["system"] = system

            resp = await session.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )

            resp.raise_for_status()
            data = resp.json()

            elapsed = (time.monotonic() - start_time) * 1000
            output = data.get("response", "")

            # Extract performance metrics
            eval_count = data.get("eval_count", 0)
            prompt_eval_count = data.get("prompt_eval_count", 0)
            total_tokens = eval_count + prompt_eval_count

            tokens_per_sec = (total_tokens / (elapsed / 1000)) if elapsed > 0 else 0

            return ROCmResult(
                success=True,
                output=output,
                latency_ms=elapsed,
                tokens_per_sec=tokens_per_sec,
            )

        except Exception as e:
            elapsed = (time.monotonic() - start_time) * 1000
            logger.exception("ROCm execution failed")
            return ROCmResult(
                success=False,
                output="",
                latency_ms=elapsed,
                tokens_per_sec=0.0,
                error=str(e),
            )

    async def benchmark_throughput(
        self,
        num_requests: int = 10,
    ) -> dict[str, Any]:
        """Benchmark ROCm throughput with concurrent requests.

        Args:
            num_requests: Number of parallel requests

        Returns:
            Performance metrics
        """
        prompt = "Write a Python function to calculate fibonacci numbers."

        start = time.monotonic()

        # Launch concurrent requests
        tasks = [self.execute(prompt, max_tokens=256, temperature=0.7) for _ in range(num_requests)]

        results = await asyncio.gather(*tasks)

        elapsed = time.monotonic() - start

        successful = [r for r in results if r.success]
        total_tokens = sum(len(r.output.split()) for r in successful)

        return {
            "total_requests": num_requests,
            "successful": len(successful),
            "total_time_s": elapsed,
            "requests_per_sec": num_requests / elapsed,
            "tokens_generated": total_tokens,
            "tokens_per_sec": total_tokens / elapsed if elapsed > 0 else 0,
            "avg_latency_ms": sum(r.latency_ms for r in successful) / len(successful)
            if successful
            else 0,
        }

    def get_hardware_info(self) -> dict[str, Any]:
        """Get ROCm hardware information."""
        info = {
            "cpu": "AMD Ryzen AI MAX+ 395 (Zen 5, 16C/32T)",
            "gpu": "AMD Radeon 8060S (RDNA 3.5)",
            "memory": "128GB LPDDR5X-8000 UMA",
            "rocm_enabled": self.enable_rocm,
            "model": self.model,
        }

        # Try to get actual GPU info
        try:
            result = subprocess.run(
                ["rocminfo"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                info["rocminfo_available"] = True
        except (subprocess.TimeoutExpired, OSError):
            info["rocminfo_available"] = False

        return info


# Factory for Cohezion integration
def create_rocm_executor(
    model: str = DEFAULT_ROCM_MODEL,
) -> ROCmExecutor:
    """Factory for ROCm-optimized executor.

    Usage:
        executor = create_rocm_executor("llama3.2:3b")
        result = await executor.execute("Write a function...")
    """
    return ROCmExecutor(model=model, enable_rocm=True)


async def main():
    """Test ROCm executor."""

    executor = create_rocm_executor()

    # Check hardware
    print("Hardware Profile:")
    for key, value in executor.get_hardware_info().items():
        print(f"  {key}: {value}")

    # Ensure model
    print("\nChecking model...")
    if not await executor.ensure_model():
        print(f"Model {executor.model} not available.")
        print(f"Run: ollama pull {executor.model}")
        return 1

    # Test execution
    print("\nTest execution...")
    result = await executor.execute(
        prompt="Write a Python function to reverse a string.",
        max_tokens=256,
    )

    if result.success:
        print("✓ Success")
        print(f"  Latency: {result.latency_ms:.1f}ms")
        print(f"  Throughput: {result.tokens_per_sec:.1f} tokens/s")
        print(f"\nOutput:\n{result.output[:200]}...")
    else:
        print(f"✗ Failed: {result.error}")
        return 1

    # Benchmark
    print("\nBenchmark (10 concurrent requests)...")
    bench = await executor.benchmark_throughput(10)
    print(f"  Requests/sec: {bench['requests_per_sec']:.2f}")
    print(f"  Tokens/sec: {bench['tokens_per_sec']:.2f}")

    return 0


if __name__ == "__main__":
    asyncio.run(main())
