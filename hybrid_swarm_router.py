#!/usr/bin/env python3
"""Hybrid NPU/GPU/Cloud Swarm Router for Lemonade."""

from __future__ import annotations

import asyncio
import json
import subprocess
from dataclasses import dataclass
from typing import Literal

import aiohttp


@dataclass
class HybridConfig:
    """Configuration for hybrid inference."""

    npu_endpoint: str = "http://localhost:13306"  # FLM NPU
    gpu_endpoint: str = "http://localhost:13307"  # ROCm (when fixed)
    cloud_endpoint: str = "http://localhost:11434"  # Ollama cloud
    npu_models: set[str] = None
    gpu_models: set[str] = None

    def __post_init__(self):
        self.npu_models = {
            "qwen3.5-4b-FLM",
            "qwen3.5-2b-FLM",
            "qwen3-4b-FLM",
            "gemma3-4b-FLM",
            "phi4-mini-4b-FLM",
            "llama3.1-8b-FLM",
        }
        self.gpu_models = {
            "Gemma-4-E2B-it-GGUF",
            "Gemma-4-E4B-it-GGUF",
            "Gemma-4-26B-A4B-it-GGUF",
            "Gemma-4-31B-it-GGUF",
        }


class HybridSwarmRouter:
    """Routes requests between NPU, GPU, and Cloud backends."""

    def __init__(self):
        self.config = HybridConfig()
        self.metrics = {"npu_requests": 0, "gpu_requests": 0, "cloud_requests": 0}

    async def route(self, prompt: str, model_hint: str | None = None) -> dict:
        """Intelligently route to best backend."""

        # 1. Check if user specified model
        if model_hint:
            if "-FLM" in model_hint:
                return await self._npu_infer(prompt, model_hint)
            elif "Gemma-4" in model_hint:
                return await self._gpu_infer(prompt, model_hint)

        # 2. Auto-route based on prompt characteristics
        tokens = len(prompt.split())

        if tokens < 100 and "code" not in prompt.lower():
            # Fast NPU for simple queries
            return await self._npu_infer(prompt, "qwen3.5-4b-FLM")

        elif any(kw in prompt.lower() for kw in ["reason", "analyze", "complex"]):
            # GPU for reasoning (once fixed)
            return await self._gpu_infer(prompt, "Gemma-4-E4B-it-GGUF")

        else:
            # Cloud fallback
            return await self._cloud_infer(prompt, "gemma4:e4b")

    async def _npu_infer(self, prompt: str, model: str) -> dict:
        """NPU via FLM (FastFlowLM)."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.npu_endpoint}/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                    },
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    result = await resp.json()
                    self.metrics["npu_requests"] += 1
                    return {
                        "backend": "npu",
                        "model": model,
                        "response": result["choices"][0]["message"]["content"],
                        "metrics": self.metrics,
                    }
        except Exception as e:
            # Fallback to cloud on NPU failure
            print(f"NPU failed ({e}), falling back to cloud...")
            return await self._cloud_infer(prompt, "gemma4:e4b")

    async def _gpu_infer(self, prompt: str, model: str) -> dict:
        """GPU via ROCm (when fixed)."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.gpu_endpoint}/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "options": {"temperature": 0.7},
                    },
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        self.metrics["gpu_requests"] += 1
                        return {
                            "backend": "gpu",
                            "model": model,
                            "response": result["choices"][0]["message"]["content"],
                            "metrics": self.metrics,
                        }
                    else:
                        # GPU not ready, use cloud
                        return await self._cloud_infer(prompt, "gemma4:e4b")
        except Exception:
            return await self._cloud_infer(prompt, "gemma4:e4b")

    async def _cloud_infer(self, prompt: str, model: str) -> dict:
        """Cloud via Ollama."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.cloud_endpoint}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False},
                    timeout=aiohttp.ClientTimeout(total=180),
                ) as resp:
                    result = await resp.json()
                    self.metrics["cloud_requests"] += 1
                    return {
                        "backend": "cloud",
                        "model": model,
                        "response": result["response"],
                        "metrics": self.metrics,
                    }
        except Exception as e:
            return {"error": str(e), "backend": "failed"}

    def load_model(self, backend: Literal["npu", "gpu", "cloud"], model: str):
        """Pre-load a model on specified backend."""
        if backend == "npu":
            cmd = f"lemonade load {model}"
        elif backend == "gpu":
            cmd = f"lemonade load {model} --llamacpp rocm"
        else:
            cmd = f"ollama pull {model}"

        subprocess.Popen(cmd, shell=True)
        return {"status": "loading", "backend": backend, "model": model}

    async def benchmark(self, prompt: str = "Explain quantum computing") -> dict:
        """Benchmark all available backends."""
        results = {}

        # Test NPU
        print("Testing NPU (qwen3.5-4b-FLM)...")
        results["npu"] = await self._npu_infer(prompt, "qwen3.5-4b-FLM")

        # Test GPU (may fail if not fixed)
        print("Testing GPU (Gemma-4-E2B)...")
        results["gpu"] = await self._gpu_infer(prompt, "Gemma-4-E2B-it-GGUF")

        # Test Cloud
        print("Testing Cloud (gemma4:e4b)...")
        results["cloud"] = await self._cloud_infer(prompt, "gemma4:e4b")

        return results


# Usage example
async def main():
    router = HybridSwarmRouter()

    # Simple query - routes to NPU
    result = await router.route("What is 21 + 34?")
    print(f"Routing: {result['backend']}")
    print(f"Response: {result['response'][:100]}...")
    print(f"Metrics: {result['metrics']}")

    # Complex query - routes to GPU (or cloud if GPU fails)
    result = await router.route(
        "Analyze the implications of 1-bit quantization on MoE architectures",
        model_hint="Gemma-4-26B-A4B-it-GGUF",
    )
    print(f"\nComplex routing: {result['backend']}")


if __name__ == "__main__":
    asyncio.run(main())
