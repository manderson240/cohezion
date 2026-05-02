#!/usr/bin/env python3
"""
COHEZION QUANTUM-AWARE DYNAMIC MODEL ROUTING ENGINE v1.1.48
Optimized for AMD Ryzen AI MAX+ 395 with 125GB DDR5 memory

This routing system compounds improvements recursively, enabling future solutions
through intelligent resource allocation and quantization-aware optimization.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import psutil  # type: ignore[import-untyped]

from cohezion.concurrency.safe_singleton import safe_singleton


# Configure logging for compound engineering insights
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class IDEPriority(Enum):
    """IDE priority weights based on user preference and system impact"""

    ANTIGRAVITY = 3  # Maximum priority for agentic development
    ZED = 2  # High priority for interactive development
    OPENCODE = 1  # Standard priority for CLI operations


class ModelTier(Enum):
    """Memory-bandwidth-aware model tiers optimized for DDR5 constraints"""

    MICRO = (0.5, 4, 12)  # 0.5-4GB, 12 concurrent, 15-20 t/s
    SMALL = (4, 8, 8)  # 4-8GB, 8 concurrent, 8-15 t/s
    MEDIUM = (8, 16, 4)  # 8-16GB, 4 concurrent, 4-8 t/s
    LARGE = (16, 32, 2)  # 16-32GB, 2 concurrent, 2-4 t/s
    ULTRA = (32, 128, 1)  # 32-128GB, 1 concurrent, 0.5-2 t/s


@dataclass
class ModelConfig:
    """Quantization-aware model configuration"""

    name: str
    size_gb: float
    quantization: str
    context_max: int
    expected_tps: float  # tokens per second
    cache_hit_rate: float  # L3 cache efficiency
    template_format: str
    optimal_for_ide: list[IDEPriority]
    is_cloud: bool = False


class MemoryBandwidthAnalyzer:
    """Real-time memory bandwidth analysis for optimal routing"""

    def __init__(self) -> None:
        self.total_memory_gb: float = float(psutil.virtual_memory().total) / (1024**3)
        self.available_memory_gb: float = float(psutil.virtual_memory().available) / (1024**3)
        self.l3_cache_mb: int = 64  # AMD Ryzen AI MAX+ 395 specific
        self.ddr5_bandwidth_gbps: int = 85  # Estimated DDR5-8000 performance

    def analyze_memory_pressure(self) -> float:
        """Calculate memory pressure ratio (0-1)"""
        return float(1.0 - (self.available_memory_gb / self.total_memory_gb))

    def calculate_optimal_concurrent_models(self, model_tier: ModelTier) -> int:
        """Calculate optimal concurrent models based on memory bandwidth"""
        memory_pressure = self.analyze_memory_pressure()

        if memory_pressure < 0.3:
            return int(model_tier.value[2])  # Full concurrent capacity
        elif memory_pressure < 0.7:
            return max(1, int(model_tier.value[2]) // 2)  # Reduced capacity
        else:
            return 1  # Conservative single model

    def estimate_tokens_per_second(self, model_config: ModelConfig) -> float:
        """Estimate tokens/second based on memory bandwidth and cache efficiency"""
        base_bandwidth_factor = self.ddr5_bandwidth_gbps / 100  # Normalize to 1.0
        cache_bonus = model_config.cache_hit_rate * 0.3  # L3 cache provides up to 30% boost
        quantization_factor = self.get_quantization_factor(model_config.quantization)

        estimated_tps = model_config.expected_tps * base_bandwidth_factor * (1 + cache_bonus) * quantization_factor

        # Apply memory pressure scaling
        memory_pressure = self.analyze_memory_pressure()
        if memory_pressure > 0.8:
            estimated_tps *= 0.7  # Degraded performance under pressure
        elif memory_pressure > 0.6:
            estimated_tps *= 0.85

        return estimated_tps

    def get_quantization_factor(self, quantization: str) -> float:
        """Get performance multiplier based on quantization level"""
        factors = {
            "Q8_0": 1.0,  # Baseline
            "Q6_K": 1.15,  # 15% speed improvement
            "Q4_K_M": 1.35,  # 35% improvement (optimal for CPU)
            "Q3_K_M": 1.5,  # 50% improvement but quality loss
        }
        return factors.get(quantization, 1.0)


class AdaptiveTemplateManager:
    """Dynamic template adaptation for cross-model family compatibility"""

    def __init__(self) -> None:
        self.templates: dict[str, dict[str, str]] = {
            "chatml": {
                "prefix": "<<|im_start|>>",
                "suffix": "<<|im_end|>>",
                "system": "system",
                "user": "user",
                "assistant": "assistant",
            },
            "microsoft": {
                "prefix": "<<|im_start|>>",
                "suffix": "<<|im_end|>>",
                "separator": "<<|im_sep|>>",
                "system": "system",
                "user": "user",
                "assistant": "assistant",
            },
            "llama3": {
                "prefix": "<|begin_of_text|>",
                "system": "<|start_header_id|>system<|end_header_id|>\n\n",
                "user": "<|start_header_id|>user<|end_header_id|>\n\n",
                "assistant": "<|start_header_id|>assistant<|end_header_id|>\n\n",
                "suffix": "<|eot_id|>",
            },
        }

    def detect_model_template(self, model_name: str) -> str:
        """Auto-detect template format based on model family"""
        model_name_lower = model_name.lower()

        if any(x in model_name_lower for x in ["qwen3", "qwen2.5"]):
            return "chatml"
        elif any(x in model_name_lower for x in ["phi", "mistral-small"]):
            return "microsoft"
        elif any(x in model_name_lower for x in ["llama", "gemma"]):
            return "llama3"
        else:
            return "chatml"  # Safe default

    def adapt_message_format(self, messages: list[dict], source_template: str, target_template: str) -> list[dict]:
        """Convert message format between different template types"""
        # For now, return as-is (templates handle formatting)
        # Future: implement sophisticated format conversion
        return messages


class DynamicModelRouter:
    """Core routing engine implementing compound engineering principles"""

    def __init__(self) -> None:
        self.memory_analyzer: MemoryBandwidthAnalyzer = MemoryBandwidthAnalyzer()
        self.template_manager: AdaptiveTemplateManager = AdaptiveTemplateManager()
        self.active_models: dict[str, ModelConfig] = {}  # Track currently loaded models
        self.request_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.performance_history: list[dict[str, Any]] = []

        # Load optimized model configurations for this hardware
        self.models: dict[str, ModelConfig] = self.load_model_registry()

    def load_model_registry(self) -> dict[str, ModelConfig]:
        """Load quantization-optimized model configurations including Hybrid Cloud fallbacks"""
        return {
            # Cloud Fallbacks for Complex Reasoning
            "gemini-3.0-pro": ModelConfig(
                name="gemini-3.0-pro",
                size_gb=0.0,
                quantization="FP16",
                context_max=2000000,
                expected_tps=50.0,
                cache_hit_rate=0.0,
                template_format="cloud",
                optimal_for_ide=[IDEPriority.ANTIGRAVITY],
                is_cloud=True,
            ),
            "claude-3.5-sonnet": ModelConfig(
                name="claude-3.5-sonnet",
                size_gb=0.0,
                quantization="FP16",
                context_max=200000,
                expected_tps=60.0,
                cache_hit_rate=0.0,
                template_format="cloud",
                optimal_for_ide=[IDEPriority.ZED],
                is_cloud=True,
            ),
            # Ultra-large models for Antigravity priority
            "qwen3-coder-next:q8_0": ModelConfig(
                name="qwen3-coder-next:q8_0",
                size_gb=84.0,
                quantization="Q8_0",
                context_max=262144,
                expected_tps=0.8,
                cache_hit_rate=0.02,
                template_format="chatml",
                optimal_for_ide=[IDEPriority.ANTIGRAVITY],
            ),
            "qwen3-coder-next:latest": ModelConfig(
                name="qwen3-coder-next:latest",
                size_gb=51.0,
                quantization="Q4_K_M",
                context_max=262144,
                expected_tps=2.5,
                cache_hit_rate=0.03,
                template_format="chatml",
                optimal_for_ide=[IDEPriority.ANTIGRAVITY, IDEPriority.ZED],
            ),
            # Medium models for balanced performance
            "qwen2.5-coder-14b-256k:latest": ModelConfig(
                name="qwen2.5-coder-14b-256k:latest",
                size_gb=9.0,
                quantization="Q4_K_M",
                context_max=32768,  # Dynamic scaling to 128k
                expected_tps=6.0,
                cache_hit_rate=0.08,
                template_format="chatml",
                optimal_for_ide=[IDEPriority.ZED, IDEPriority.OPENCODE],
            ),
            "phi4:latest": ModelConfig(
                name="phi4:latest",
                size_gb=9.1,
                quantization="Q4_K_M",
                context_max=128000,  # Dynamic scaling
                expected_tps=10.0,
                cache_hit_rate=0.09,
                template_format="microsoft",
                optimal_for_ide=[IDEPriority.ZED, IDEPriority.OPENCODE],
            ),
            # Small/fast models for quick completion
            "qwen3:8b": ModelConfig(
                name="qwen3:8b",
                size_gb=5.2,
                quantization="Q8_0",
                context_max=64000,
                expected_tps=9.0,
                cache_hit_rate=0.15,
                template_format="chatml",
                optimal_for_ide=[IDEPriority.ZED, IDEPriority.OPENCODE],
            ),
            "gemma3-4b-256k:latest": ModelConfig(
                name="gemma3-4b-256k:latest",
                size_gb=3.3,
                quantization="Q4_K_M",
                context_max=256000,
                expected_tps=12.0,
                cache_hit_rate=0.18,
                template_format="llama3",
                optimal_for_ide=[IDEPriority.OPENCODE],
            ),
        }

    async def select_optimal_model(self, request: dict[str, Any]) -> ModelConfig:
        """Intelligent model selection using compound engineering algorithm"""
        ide = IDEPriority(request.get("ide_priority", 1))
        task_type = request.get("task_type", "general")
        request.get("context_length", 0)
        request.get("urgency", "medium")

        # Calculate routing score based on multiple factors
        memory_pressure = self.memory_analyzer.analyze_memory_pressure()

        # Filter by IDE compatibility
        compatible_models = [m for m in self.models.values() if ide in m.optimal_for_ide]

        # Score each model based on current conditions
        scored_models: list[tuple[float, ModelConfig]] = []
        for model in compatible_models:
            score = self.calculate_model_score(model, request, memory_pressure)
            scored_models.append((score, model))

        # Sort by score (highest first) and return optimal choice
        scored_models.sort(key=lambda x: x[0], reverse=True)

        if scored_models:
            optimal_model = scored_models[0][1]
            logger.info(f"Selected {optimal_model.name} for {task_type} - Score: {scored_models[0][1]}")
            return optimal_model
        else:
            # Fallback to safest option
            return self.models["qwen3:8b"]

    def calculate_model_score(self, model: ModelConfig, request: dict, memory_pressure: float) -> float:
        """Compound scoring algorithm for model selection"""
        score = 0.0

        task_type: str = str(request.get("task_type", "general"))
        urgency: str = str(request.get("urgency", "medium"))

        # Base capability score
        if task_type == "coding" and ("coder" in model.name or "phi" in model.name):
            score += 200  # Massive boost for specialized coding models

        # Cloud Hybrid Routing Rules
        if (task_type == "complex_reasoning" or task_type == "architecture") and model.is_cloud:
            score += 300  # Enormously prioritize Cloud for advanced logic

        # Avoid network roundtrip of cloud if local fits for urgent tasks
        if urgency == "high" and not model.is_cloud:
            score += 15

        # Avoid cloud for simple code formatting
        if task_type == "formatting" and model.is_cloud:
            score -= 50

        # Memory efficiency score (prefer models that fit comfortably)
        memory_fit = max(0, (model.size_gb / self.memory_analyzer.available_memory_gb) * 100)
        if memory_fit < 30:
            score += 25
        elif memory_fit < 60:
            score += 15
        elif memory_fit < 80:
            score += 5

        # Performance score (tokens/second)
        performance_score = model.expected_tps * 3
        score += performance_score

        # Cache efficiency bonus
        cache_bonus = model.cache_hit_rate * 50
        score += cache_bonus

        # Quantization efficiency
        quant_bonus = {"Q8_0": 5, "Q4_K_M": 15, "Q6_K": 10, "Q3_K_M": 8}.get(model.quantization, 0)
        score += quant_bonus

        # Context window adequacy
        required_context = request.get("context_length", 1000)
        if model.context_max >= required_context:
            score += 20
        elif model.context_max >= required_context // 2:
            score += 10

        # Memory pressure penalty
        if memory_pressure > 0.8:
            if model.size_gb > 32:  # Large models penalized under pressure
                score -= 30
        elif memory_pressure > 0.6 and model.size_gb > 16:
            score -= 15

        # IDE priority alignment
        ide_weight = request.get("ide_priority", 1)
        if any(ide in model.optimal_for_ide for ide in [IDEPriority(ide_weight)]):
            score += 10 * ide_weight

        return score

    async def execute_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Execute a request with optimal model selection"""
        start_time = time.time()

        # Select optimal model
        model = await self.select_optimal_model(request)

        # Prepare request with adaptive template
        self.template_manager.detect_model_template(model.name)

        # Calculate dynamic context scaling
        max_context = min(model.context_max, self.calculate_dynamic_context_limit(model))

        # Execute via Ollama (simplified for demonstration)
        result = await self.ollama_generate(model, request, max_context)

        # Record performance for compound learning
        execution_time = time.time() - start_time
        self.record_performance(model, execution_time, len(result.get("text", "")))

        return {
            "result": result,
            "model_used": model.name,
            "execution_time": execution_time,
            "tokens_per_second": len(result.get("text", "")) / execution_time if execution_time > 0 else 0,
        }

    def calculate_dynamic_context_limit(self, model: ModelConfig) -> int:
        """Dynamic context scaling based on available memory"""
        available_memory = self.memory_analyzer.available_memory_gb

        # User-defined soft caps
        soft_caps = {
            14: 128000,  # 128k for 14B models
            30: 64000,  # 64k for 30B+ models
            70: 32768,  # 32k for 70B+ models
            80: 16384,  # 16k for 80B+ models
        }

        # Find appropriate parameter bucket
        param_billion = model.size_gb * 2  # Rough estimation (2GB per 1B parameters)
        soft_cap = 32768  # Default

        for size, cap in soft_caps.items():
            if param_billion <= size:
                soft_cap = cap
                break

        # Adjust for memory pressure
        if available_memory < 20:
            soft_cap = min(soft_cap, 8192)
        elif available_memory < 40:
            soft_cap = min(soft_cap, 16384)

        return min(soft_cap, model.context_max)

    async def ollama_generate(self, model: ModelConfig, request: dict, max_context: int) -> dict:
        """Execute Ollama generation via HTTP API.

        Uses ``httpx.AsyncClient`` to POST to ``/api/generate`` on the
        local Ollama server instead of spawning a subprocess.
        """
        import httpx

        # Token Burn Security Check
        requested_tokens: int = int(request.get("max_tokens", 4096))
        max_safe_tokens = 8192

        if requested_tokens > max_safe_tokens:
            logger.warning(
                "🚨 TOKEN BURN SECURITY ALERT: "
                f"Requested {requested_tokens} tokens for "
                f"local offload model {model.name}. "
                f"Hard-capping to {max_safe_tokens} "
                "to prevent runaway OOM/Burn loops."
            )
            requested_tokens = max_safe_tokens

        payload = {
            "model": model.name,
            "prompt": request.get("prompt", ""),
            "system": request.get("system", ""),
            "stream": False,
            "options": {
                "num_ctx": max_context,
                "temperature": request.get("temperature", 0.7),
                "top_p": request.get("top_p", 0.9),
                "num_predict": requested_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                resp = await client.post(
                    "http://localhost:11434/api/generate",
                    json=payload,
                )
                _ = resp.raise_for_status()
                data = resp.json()
                return {"text": data.get("response", ""), **data}

        except httpx.TimeoutException:
            logger.error("Ollama request timed out for model %s", model.name)
            return {"text": "", "error": "timeout"}
        except Exception as e:
            logger.error("Ollama HTTP error: %s", e)
            return {"text": "", "error": str(e)}

    def record_performance(self, model: ModelConfig, execution_time: float, response_length: int):
        """Record performance metrics for compound learning"""
        performance_data = {
            "timestamp": time.time(),
            "model": model.name,
            "execution_time": execution_time,
            "response_length": response_length,
            "tokens_per_second": response_length / execution_time if execution_time > 0 else 0,
            "memory_available": self.memory_analyzer.available_memory_gb,
            "memory_pressure": self.memory_analyzer.analyze_memory_pressure(),
        }

        self.performance_history.append(performance_data)

        # Keep history manageable (last 1000 entries)
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]

        logger.info(f"Recorded performance: {model.name} - {performance_data['tokens_per_second']:.1f} t/s")


@safe_singleton
def get_router() -> DynamicModelRouter:
    """Return a lazily-initialised singleton DynamicModelRouter."""
    return DynamicModelRouter()


# Backward-compatible module-level reference
router = get_router()


async def main():
    """Demonstration of the dynamic routing system"""
    logger.info("🚀 COHEZION Quantum-Aware Dynamic Routing Engine v1.1.48 Initializing...")
    logger.info(
        f"System: {router.memory_analyzer.total_memory_gb:.1f}GB RAM,"
        f" {router.memory_analyzer.available_memory_gb:.1f}GB available"
    )
    logger.info(
        f"L3 Cache: {router.memory_analyzer.l3_cache_mb}MB,"
        f" DDR5 Bandwidth: {router.memory_analyzer.ddr5_bandwidth_gbps}GB/s"
    )

    # Test requests
    test_requests = [
        {
            "prompt": "Write a Python function for dynamic model routing",
            "task_type": "coding",
            "ide_priority": IDEPriority.ANTIGRAVITY.value,
            "context_length": 2000,
            "urgency": "high",
        },
        {
            "prompt": "Complete this code snippet: def calculate_optimal_model(",
            "task_type": "completion",
            "ide_priority": IDEPriority.ZED.value,
            "context_length": 500,
            "urgency": "high",
        },
        {
            "prompt": "Explain compound engineering principles",
            "task_type": "analysis",
            "ide_priority": IDEPriority.OPENCODE.value,
            "context_length": 1000,
            "urgency": "medium",
        },
    ]

    for request in test_requests:
        logger.info(f"\n🎯 Processing request: {request['task_type']} for IDE priority {request['ide_priority']}")
        result = await router.execute_request(request)
        logger.info(
            f"Completed with {result['model_used']}"
            f" in {result['execution_time']:.2f}s"
            f" ({result['tokens_per_second']:.1f} t/s)"
        )


if __name__ == "__main__":
    asyncio.run(main())
