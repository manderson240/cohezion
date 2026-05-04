"""Multi-Model Orchestrator for heterogeneous local inference (CPU/GPU/NPU).

Optimized for AMD Ryzen AI MAX+ 395 with triple compute:
- CPU: 16C/32T Zen 5 (best for small models < 3B)
- GPU: RDNA 3.5 iGPU (best for medium models 3B-14B)
- NPU: XDNA 2 50 TOPS (best for specialized quantized models)

Supports: Llama, Mistral, DeepSeek, Phi, Gemma, Qwen, and more
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import aiohttp

from cohezion.swarm.providers.model_provider import (
    GenerationResult,
    ModelProvider,
    register_model_provider,
)


logger = logging.getLogger(__name__)


class ComputeUnit(Enum):
    """Available compute units on Ryzen AI MAX+ 395."""

    CPU = "cpu"  # 16C/32T Zen 5 - small models, general compute
    GPU = "gpu"  # RDNA 3.5 iGPU - medium models, high throughput
    NPU = "npu"  # XDNA 2 - quantized models, power efficient
    HYBRID = "hybrid"  # Mixed execution (NPU prefill + GPU decode)


class ModelType(Enum):
    """Model architecture families."""

    LLAMA = "llama"  # Llama 2, 3, 3.1, 3.2
    GEMMA = "gemma"  # Gemma 2, 3, 4
    MISTRAL = "mistral"  # Mistral, Mixtral, MoE variants
    PHI = "phi"  # Phi-3, Phi-4
    DEEPSEEK = "deepseek"  # DeepSeek-V3, R1
    QWEN = "qwen"  # Qwen 2, 2.5
    GRANITE = "granite"  # IBM Granite
    OTHER = "other"


@dataclass
class ModelProfile:
    """Hardware-aware model profile."""

    model_family: ModelType
    size_b: float  # Size in billions
    preferred_unit: ComputeUnit
    fallback_unit: ComputeUnit
    quantization: str  # q4, q6, q8, fp16
    max_context: int
    recommended_batch: int
    memory_gb: float  # Estimated VRAM

    def __post_init__(self):
        if self.memory_gb == 0:
            # Estimate: 1B params ≈ 0.5GB (Q4), 1GB (FP16)
            mem_per_b = 0.5 if "q4" in self.quantization else 1.0
            self.memory_gb = self.size_b * mem_per_b


class MultiModelOrchestrator(ModelProvider):
    """Orchestrates heterogeneous model inference across CPU/GPU/NPU.

    Automatically selects optimal execution path based on:
    - Model size and architecture
    - Available compute resources
    - Current system load
    - Latency vs throughput requirements

    Example:
        orchestrator = MultiModelOrchestrator()

        # Automatic routing based on model
        result = await orchestrator.generate(
            model="llama3.2:3b",
            prompt="Write a function...",
        )

        # Force specific compute unit
        result = await orchestrator.generate(
            model="deepseek-r1:14b",
            prompt="Solve this...",
            force_unit=ComputeUnit.GPU,
        )
    """

    # Model profiles for known architectures
    MODEL_PROFILES: dict[str, ModelProfile] = {
        # Small models (< 3B) - CPU efficient
        "phi3:mini": ModelProfile(
            ModelType.PHI, 3.8, ComputeUnit.CPU, ComputeUnit.GPU, "q4", 128000, 16, 2.0
        ),
        "llama3.2:1b": ModelProfile(
            ModelType.LLAMA, 1.0, ComputeUnit.CPU, ComputeUnit.GPU, "q4", 128000, 32, 0.5
        ),
        "llama3.2:3b": ModelProfile(
            ModelType.LLAMA, 3.0, ComputeUnit.GPU, ComputeUnit.CPU, "q4", 128000, 16, 1.5
        ),
        "gemma2:2b": ModelProfile(
            ModelType.GEMMA, 2.0, ComputeUnit.CPU, ComputeUnit.GPU, "q4", 8192, 32, 1.0
        ),
        # Medium models (3B-8B) - GPU optimal
        "llama3.1:8b": ModelProfile(
            ModelType.LLAMA, 8.0, ComputeUnit.GPU, ComputeUnit.CPU, "q4", 128000, 8, 4.0
        ),
        "mistral:7b": ModelProfile(
            ModelType.MISTRAL, 7.0, ComputeUnit.GPU, ComputeUnit.NPU, "q4", 32768, 8, 3.5
        ),
        "deepseek-r1:7b": ModelProfile(
            ModelType.DEEPSEEK, 7.0, ComputeUnit.GPU, ComputeUnit.CPU, "q4", 32768, 8, 3.5
        ),
        "gemma3:4b": ModelProfile(
            ModelType.GEMMA, 4.0, ComputeUnit.GPU, ComputeUnit.NPU, "q4", 65536, 16, 2.0
        ),
        # Large models (8B-14B) - GPU with hybrid fallback
        "llama3.1:8b-instruct": ModelProfile(
            ModelType.LLAMA, 8.0, ComputeUnit.GPU, ComputeUnit.HYBRID, "q4", 128000, 4, 4.0
        ),
        "qwen2.5:14b": ModelProfile(
            ModelType.QWEN, 14.0, ComputeUnit.GPU, ComputeUnit.HYBRID, "q4", 65536, 4, 7.0
        ),
        "deepseek-coder:6.7b": ModelProfile(
            ModelType.DEEPSEEK, 6.7, ComputeUnit.GPU, ComputeUnit.CPU, "q4", 65536, 8, 3.5
        ),
        # Vision models - GPU required
        "granite3.2-vision:2b": ModelProfile(
            ModelType.GRANITE, 2.0, ComputeUnit.GPU, ComputeUnit.HYBRID, "q4", 65536, 8, 2.5
        ),
        "gemma3:12b": ModelProfile(
            ModelType.GEMMA, 12.0, ComputeUnit.GPU, ComputeUnit.HYBRID, "q4", 65536, 2, 6.0
        ),
        # NPU optimized (quantized ONNX)
        "phi3:npu": ModelProfile(
            ModelType.PHI, 3.8, ComputeUnit.NPU, ComputeUnit.GPU, "int4", 4096, 16, 1.0
        ),
    }

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize multi-model orchestrator.

        Args:
            config: Configuration dict with optional overrides
        """
        super().__init__(config)

        self.base_url = self.config.get("base_url", "http://localhost:11434")
        self.timeout = self.config.get("timeout", 180)
        self.default_unit = ComputeUnit(self.config.get("default_unit", "gpu"))

        # Hardware endpoints (can be extended)
        self.endpoints = {
            ComputeUnit.CPU: self.base_url,  # Default Ollama
            ComputeUnit.GPU: self.base_url,  # Ollama with ROCm
            ComputeUnit.NPU: self.config.get("npu_endpoint", "http://localhost:8001"),
            ComputeUnit.HYBRID: self.config.get("hybrid_endpoint", self.base_url),
        }

        # Resource monitoring
        self.active_models: dict[ComputeUnit, int] = dict.fromkeys(ComputeUnit, 0)
        self.latency_tracker: dict[str, list[float]] = {}

        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def get_model_profile(self, model: str) -> ModelProfile | None:
        """Get hardware profile for model."""
        # Direct match
        if model in self.MODEL_PROFILES:
            return self.MODEL_PROFILES[model]

        # Pattern matching for variants
        for pattern, profile in self.MODEL_PROFILES.items():
            if pattern.split(":")[0] in model.lower():
                return profile

        # Default profile for unknown models
        size_str = model.split(":")[-1] if ":" in model else "7b"
        try:
            size = float(size_str.replace("b", "").replace("m", ".001"))
        except ValueError:
            size = 7.0

        unit = ComputeUnit.CPU if size < 3.0 else ComputeUnit.GPU
        return ModelProfile(
            model_family=ModelType.OTHER,
            size_b=size,
            preferred_unit=unit,
            fallback_unit=ComputeUnit.CPU,
            quantization="q4",
            max_context=8192,
            recommended_batch=8,
            memory_gb=size * 0.5,
        )

    def select_compute_unit(
        self,
        model: str,
        latency_critical: bool = False,
        throughput_priority: bool = False,
        force_unit: ComputeUnit | None = None,
    ) -> ComputeUnit:
        """Select optimal compute unit for model.

        Args:
            model: Model name
            latency_critical: Prioritize TTFT over throughput
            throughput_priority: Prioritize tokens/sec
            force_unit: Override automatic selection

        Returns:
            Selected compute unit
        """
        if force_unit:
            return force_unit

        profile = self.get_model_profile(model)
        if not profile:
            return self.default_unit

        # Load balancing: check current utilization
        preferred_load = self.active_models.get(profile.preferred_unit, 0)

        # If preferred unit is overloaded, use fallback
        if preferred_load > 2:  # Threshold for queue depth
            logger.info(
                f"{profile.preferred_unit.value} overloaded ({preferred_load}), using fallback"
            )
            return profile.fallback_unit

        # Latency-critical small models → CPU (lowest TTFT)
        if latency_critical and profile.size_b < 3.0:
            return ComputeUnit.CPU

        # Throughput priority → GPU (highest bandwidth)
        if throughput_priority:
            return ComputeUnit.GPU if profile.size_b > 3.0 else ComputeUnit.CPU

        return profile.preferred_unit

    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> GenerationResult:
        """Generate response with automatic compute unit selection.

        Args:
            model: Ollama model name
            prompt: Input prompt
            max_tokens: Max tokens
            temperature: Temperature
            **kwargs: Additional options including:
                - force_unit: Override compute unit selection
                - latency_critical: Prioritize TTFT
                - throughput_priority: Prioritize tokens/sec
        """
        start_time = time.time()

        # Select compute unit
        unit = self.select_compute_unit(
            model,
            latency_critical=kwargs.get("latency_critical", False),
            throughput_priority=kwargs.get("throughput_priority", False),
            force_unit=kwargs.get("force_unit"),
        )

        profile = self.get_model_profile(model)
        endpoint = self.endpoints.get(unit, self.base_url)

        self.active_models[unit] += 1

        try:
            result = await self._generate_on_unit(
                model, prompt, unit, endpoint, max_tokens, temperature, profile, **kwargs
            )

            # Track latency
            self._track_latency(model, result.latency_ms)

            return result

        finally:
            self.active_models[unit] -= 1

    async def _generate_on_unit(
        self,
        model: str,
        prompt: str,
        unit: ComputeUnit,
        endpoint: str,
        max_tokens: int,
        temperature: float,
        profile: ModelProfile | None,
        **kwargs,
    ) -> GenerationResult:
        """Execute generation on specific compute unit."""
        session = await self._get_session()

        # Optimize options for compute unit
        options = self._optimize_for_unit(unit, profile, max_tokens, temperature)
        options.update(kwargs.get("options", {}))

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }

        # Add keep_alive for GPU models to avoid reloading
        if unit in (ComputeUnit.GPU, ComputeUnit.HYBRID):
            payload["keep_alive"] = "5m"

        try:
            async with session.post(
                f"{endpoint}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"API error {response.status}: {error_text}")

                data = await response.json()

                latency_ms = (time.time() - start_time) * 1000
                tokens_used = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)

                return GenerationResult(
                    response=data.get("response", ""),
                    model=model,
                    provider=f"multi_model/{unit.value}",
                    confidence=self._estimate_confidence(data, profile),
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    metadata={
                        "compute_unit": unit.value,
                        "model_size_b": profile.size_b if profile else 0,
                        "throughput_tps": data.get("eval_count", 0) / (latency_ms / 1000),
                    },
                )

        except Exception:
            logger.exception(f"Generation failed on {unit.value}")
            raise

    def _optimize_for_unit(
        self,
        unit: ComputeUnit,
        profile: ModelProfile | None,
        max_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        """Generate unit-specific optimizations."""
        opts = {
            "num_predict": max_tokens,
            "temperature": temperature,
        }

        if profile:
            opts["num_ctx"] = min(profile.max_context, 8192)

            if unit == ComputeUnit.CPU:
                # CPU: Use more threads, smaller batches
                opts["num_thread"] = 8
                opts["batch_size"] = profile.recommended_batch

            elif unit == ComputeUnit.GPU:
                # GPU: ROCm optimizations
                opts["num_gpu"] = 1
                opts["num_thread"] = 4
                opts["batch_size"] = profile.recommended_batch
                opts["mmap"] = True
                opts["use_mlock"] = False

            elif unit == ComputeUnit.NPU:
                # NPU: Quantized inference
                opts["num_thread"] = 4

        return opts

    def _estimate_confidence(
        self,
        data: dict,
        profile: ModelProfile | None,
    ) -> float:
        """Estimate confidence from response characteristics."""
        response = data.get("response", "")

        if not response:
            return 0.0

        # Base confidence on completion
        confidence = 0.85

        # Higher confidence for longer completions (indicates model engaged)
        if len(response) > 100:
            confidence = min(0.98, confidence + 0.05)

        # Lower confidence for very short responses
        if len(response) < 20:
            confidence = max(0.5, confidence - 0.1)

        return confidence

    def _track_latency(self, model: str, latency_ms: float) -> None:
        """Track latency for adaptive routing."""
        if model not in self.latency_tracker:
            self.latency_tracker[model] = []

        self.latency_tracker[model].append(latency_ms)

        # Keep only last 10 samples
        if len(self.latency_tracker[model]) > 10:
            self.latency_tracker[model].pop(0)

    def get_latency_stats(self, model: str) -> dict[str, float]:
        """Get latency statistics for model."""
        samples = self.latency_tracker.get(model, [])
        if not samples:
            return {}

        return {
            "mean_ms": sum(samples) / len(samples),
            "min_ms": min(samples),
            "max_ms": max(samples),
            "samples": len(samples),
        }

    async def batch_generate(
        self,
        requests: list[dict[str, Any]],
        max_concurrent: int = 4,
    ) -> list[GenerationResult]:
        """Generate multiple responses with controlled concurrency.

        Args:
            requests: List of request dicts with model, prompt, etc.
            max_concurrent: Max concurrent requests

        Returns:
            List of generation results
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_generate(req: dict) -> GenerationResult:
            async with semaphore:
                return await self.generate(
                    model=req["model"],
                    prompt=req["prompt"],
                    max_tokens=req.get("max_tokens", 1024),
                    temperature=req.get("temperature", 0.7),
                    **{
                        k: v
                        for k, v in req.items()
                        if k not in ["model", "prompt", "max_tokens", "temperature"]
                    },
                )

        tasks = [bounded_generate(req) for req in requests]
        return await asyncio.gather(*tasks, return_exceptions=True)


# Auto-register provider
register_model_provider("multi_model", MultiModelOrchestrator)


async def demo():
    """Demonstrate multi-model orchestration."""
    orchestrator = MultiModelOrchestrator()

    # Show model profiles
    print("Model Profiles:")
    for name, profile in MultiModelOrchestrator.MODEL_PROFILES.items():
        print(
            f"  {name}: {profile.size_b}B, {profile.preferred_unit.value}, "
            f"~{profile.memory_gb}GB VRAM"
        )

    # Test automatic routing
    test_models = ["phi3:mini", "llama3.2:3b", "mistral:7b"]

    for model in test_models:
        profile = orchestrator.get_model_profile(model)
        unit = orchestrator.select_compute_unit(model)
        print(f"\n{model}:")
        print(f"  Size: {profile.size_b}B")
        print(f"  Preferred: {profile.preferred_unit.value}")
        print(f"  Selected: {unit.value}")
        print(f"  Memory: ~{profile.memory_gb}GB")


if __name__ == "__main__":
    asyncio.run(demo())
