"""Ollama Context Manager - Dynamic context window management per model.

Manages context windows, KV cache, and memory allocation for SOTA models
on AMD Ryzen AI MAX+ 395 (128GB UMA).

Key features:
- Per-model context configuration
- Dynamic context window adjustment based on task
- KV cache management for long conversations
- Memory pressure handling across multiple models
- Context truncation strategies

Usage:
    manager = OllamaContextManager()

    # Get optimal context for model and task
    ctx = manager.get_context_config(
        model="gemma3:4b",
        task_type="long_document_analysis",
        available_memory_gb=96,
    )

    # Apply to Ollama request
    result = await ollama.generate(
        model="gemma3:4b",
        prompt=prompt,
        options={"num_ctx": ctx.window_size}
    )
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import Enum
from typing import Any


logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Task categories with different context needs."""

    QUICK_QUERY = "quick_query"  # 2K context, fast response
    CHAT = "chat"  # 4K context, conversation
    CODING = "coding"  # 8K context, code analysis
    REASONING = "reasoning"  # 16K context, step-by-step
    LONG_DOC = "long_document"  # 32K+ context, full documents
    AGENT_LOOP = "agent_loop"  # Variable, tool use
    MULTIMODAL = "multimodal"  # Vision + text


class TruncationStrategy(Enum):
    """How to handle context overflow."""

    TRUNCATE_OLD = "truncate_old"  # Keep recent, drop oldest
    TRUNCATE_MIDDLE = "truncate_middle"  # Keep start and end
    COMPRESS_SUMMARY = "compress"  # Generate summary of old
    RAISE_ERROR = "error"  # Fail if overflow


@dataclass
class ModelContextProfile:
    """Context profile for a specific model."""

    model_name: str
    max_native_ctx: int  # Model's native capability
    default_ctx: int  # Recommended default
    min_ctx: int  # Minimum viable
    kv_cache_gb_per_1k: float  # KV cache memory usage
    attention_type: str  # Full, sliding window, etc.
    supports_rope_scaling: bool  # Can extend via RoPE
    recommended_tasks: list[TaskType]

    def estimate_memory_gb(self, context_size: int) -> float:
        """Estimate memory usage for given context."""
        return (context_size / 1024) * self.kv_cache_gb_per_1k


@dataclass
class ContextConfig:
    """Runtime context configuration."""

    model: str
    window_size: int
    max_tokens: int
    truncation: TruncationStrategy
    keep_alive: str
    num_parallel: int
    estimated_memory_gb: float
    optimization_notes: list[str]


class OllamaContextManager:
    """Manages context windows for heterogeneous model fleet.

    Optimized for AMD Ryzen AI MAX+ 395:
    - 128GB UMA (shared CPU/GPU/NPU memory)
    - Up to 96GB allocatable as VRAM
    - Dynamic memory pressure management
    """

    # Model context profiles (native capabilities)
    MODEL_PROFILES: dict[str, ModelContextProfile] = {
        # === Gemma 3 Family (Apr 2026) ===
        "gemma3:1b": ModelContextProfile(
            model_name="Gemma 3 1B",
            max_native_ctx=32768,
            default_ctx=8192,
            min_ctx=2048,
            kv_cache_gb_per_1k=0.08,
            attention_type="sliding_window",
            supports_rope_scaling=False,
            recommended_tasks=[
                TaskType.QUICK_QUERY,
                TaskType.CHAT,
                TaskType.MULTIMODAL,
            ],
        ),
        "gemma3:4b": ModelContextProfile(
            model_name="Gemma 3 4B",
            max_native_ctx=131072,  # 128K context!
            default_ctx=16384,
            min_ctx=4096,
            kv_cache_gb_per_1k=0.15,
            attention_type="full",
            supports_rope_scaling=True,
            recommended_tasks=[
                TaskType.LONG_DOC,
                TaskType.REASONING,
                TaskType.MULTIMODAL,
                TaskType.CODING,
            ],
        ),
        # === Llama 3.2 Family ===
        "llama3.2:1b": ModelContextProfile(
            model_name="Llama 3.2 1B",
            max_native_ctx=131072,
            default_ctx=8192,
            min_ctx=2048,
            kv_cache_gb_per_1k=0.06,
            attention_type="sliding_window",
            supports_rope_scaling=False,
            recommended_tasks=[
                TaskType.QUICK_QUERY,
                TaskType.CHAT,
                TaskType.MULTIMODAL,
            ],
        ),
        "llama3.2:3b": ModelContextProfile(
            model_name="Llama 3.2 3B",
            max_native_ctx=131072,
            default_ctx=16384,
            min_ctx=4096,
            kv_cache_gb_per_1k=0.12,
            attention_type="full",
            supports_rope_scaling=True,
            recommended_tasks=[
                TaskType.CODING,
                TaskType.REASONING,
                TaskType.LONG_DOC,
            ],
        ),
        # === Phi-4 Family ===
        "phi4": ModelContextProfile(
            model_name="Phi-4",
            max_native_ctx=16384,  # 16K native
            default_ctx=8192,
            min_ctx=2048,
            kv_cache_gb_per_1k=0.18,
            attention_type="full",
            supports_rope_scaling=False,
            recommended_tasks=[
                TaskType.CODING,
                TaskType.REASONING,
                TaskType.CHAT,
            ],
        ),
        # === DeepSeek R1 Distill ===
        "deepseek-r1:1.5b": ModelContextProfile(
            model_name="DeepSeek-R1 1.5B",
            max_native_ctx=32768,
            default_ctx=8192,
            min_ctx=4096,  # Needs more for reasoning chain
            kv_cache_gb_per_1k=0.10,
            attention_type="sliding_window",
            supports_rope_scaling=True,
            recommended_tasks=[
                TaskType.REASONING,
                TaskType.CODING,
                TaskType.AGENT_LOOP,
            ],
        ),
    }

    # Task context requirements
    TASK_CONTEXTS: dict[TaskType, dict[str, Any]] = {
        TaskType.QUICK_QUERY: {
            "ctx_multiplier": 0.25,
            "max_tokens": 512,
            "truncation": TruncationStrategy.TRUNCATE_OLD,
            "notes": ["Minimal context for fast queries"],
        },
        TaskType.CHAT: {
            "ctx_multiplier": 0.5,
            "max_tokens": 1024,
            "truncation": TruncationStrategy.TRUNCATE_OLD,
            "notes": ["Conversation history management"],
        },
        TaskType.CODING: {
            "ctx_multiplier": 0.75,
            "max_tokens": 2048,
            "truncation": TruncationStrategy.TRUNCATE_MIDDLE,
            "notes": ["Keep function signatures, truncate middle"],
        },
        TaskType.REASONING: {
            "ctx_multiplier": 0.75,
            "max_tokens": 2048,
            "truncation": TruncationStrategy.TRUNCATE_MIDDLE,
            "notes": ["Step-by-step needs working memory"],
        },
        TaskType.LONG_DOC: {
            "ctx_multiplier": 1.0,
            "max_tokens": 4096,
            "truncation": TruncationStrategy.RAISE_ERROR,
            "notes": ["Full context required, fail if overflow"],
        },
        TaskType.AGENT_LOOP: {
            "ctx_multiplier": 0.6,
            "max_tokens": 1536,
            "truncation": TruncationStrategy.COMPRESS_SUMMARY,
            "notes": ["Variable, may need compression"],
        },
        TaskType.MULTIMODAL: {
            "ctx_multiplier": 0.5,
            "max_tokens": 1024,
            "truncation": TruncationStrategy.TRUNCATE_OLD,
            "notes": ["Vision tokens consume context"],
        },
    }

    def __init__(self, total_memory_gb: float = 128.0):
        """Initialize context manager.

        Args:
            total_memory_gb: Total UMA memory available (default 128GB for MAX+ 395)
        """
        self.total_memory_gb = total_memory_gb
        self.reserved_gb = 16.0  # OS + overhead
        self.available_gb = total_memory_gb - self.reserved_gb

        # Active model tracking
        self.active_contexts: dict[str, ContextConfig] = {}
        self.kv_cache_usage: dict[str, float] = {}  # GB used per model

    def get_context_config(
        self,
        model: str,
        task_type: TaskType | str = TaskType.CHAT,
        available_memory_gb: float | None = None,
        force_context: int | None = None,
    ) -> ContextConfig:
        """Generate optimal context configuration.

        Args:
            model: Ollama model name
            task_type: Type of task being performed
            available_memory_gb: Override available memory
            force_context: Force specific context size

        Returns:
            ContextConfig with optimized parameters
        """
        # Get profile
        profile = self.MODEL_PROFILES.get(model)
        if not profile:
            logger.warning(f"Unknown model {model}, using defaults")
            profile = self._create_default_profile(model)

        # Parse task type
        if isinstance(task_type, str):
            try:
                task_type = TaskType(task_type)
            except ValueError:
                task_type = TaskType.CHAT

        task_config = self.TASK_CONTEXTS.get(task_type, self.TASK_CONTEXTS[TaskType.CHAT])

        # Determine context window
        if force_context:
            ctx_size = min(force_context, profile.max_native_ctx)
        else:
            # Calculate based on task and available memory
            memory = available_memory_gb or self.available_gb
            ctx_size = self._calculate_context_size(profile, task_config, memory)

        # Ensure minimum for model
        ctx_size = max(ctx_size, profile.min_ctx)

        # Estimate memory
        memory_gb = profile.estimate_memory_gb(ctx_size)

        # Generate optimization notes
        notes = list(task_config["notes"])
        if ctx_size == profile.max_native_ctx:
            notes.append(f"Using maximum native context ({profile.max_native_ctx})")
        if memory_gb > 20:
            notes.append(f"High memory usage: {memory_gb:.1f}GB")

        # Keep-alive strategy
        if task_type in (TaskType.AGENT_LOOP, TaskType.REASONING):
            keep_alive = "10m"  # Keep loaded for agent/reasoning
        elif task_type == TaskType.QUICK_QUERY:
            keep_alive = "30s"  # Quick release
        else:
            keep_alive = "5m"

        return ContextConfig(
            model=model,
            window_size=ctx_size,
            max_tokens=task_config["max_tokens"],
            truncation=task_config["truncation"],
            keep_alive=keep_alive,
            num_parallel=2 if task_type == TaskType.QUICK_QUERY else 1,
            estimated_memory_gb=memory_gb,
            optimization_notes=notes,
        )

    def _calculate_context_size(
        self,
        profile: ModelContextProfile,
        task_config: dict,
        available_memory_gb: float,
    ) -> int:
        """Calculate optimal context size."""
        # Base on task multiplier
        target_ctx = int(profile.default_ctx * task_config["ctx_multiplier"])

        # Round to nearest power of 2 for efficiency
        target_ctx = 2 ** math.floor(math.log2(target_ctx))

        # Check memory constraint
        required_gb = profile.estimate_memory_gb(target_ctx)

        if required_gb > available_memory_gb * 0.5:
            # Scale down if too much memory
            scale_factor = (available_memory_gb * 0.5) / required_gb
            target_ctx = int(target_ctx * scale_factor)
            target_ctx = max(target_ctx, profile.min_ctx)
            target_ctx = 2 ** math.floor(math.log2(target_ctx))

        return min(target_ctx, profile.max_native_ctx)

    def _create_default_profile(self, model: str) -> ModelContextProfile:
        """Create default profile for unknown model."""
        # Estimate from model name
        size_indicator = model.split(":")[-1] if ":" in model else "7b"

        if "b" in size_indicator.lower():
            try:
                size = float(size_indicator.lower().replace("b", ""))
            except:
                size = 7.0
        else:
            size = 7.0

        # Larger models need more KV cache
        kv_factor = size / 7.0

        return ModelContextProfile(
            model_name=model,
            max_native_ctx=8192,
            default_ctx=4096,
            min_ctx=2048,
            kv_cache_gb_per_1k=0.12 * kv_factor,
            attention_type="unknown",
            supports_rope_scaling=False,
            recommended_tasks=[TaskType.CHAT],
        )

    def register_active_model(self, config: ContextConfig) -> None:
        """Track active model context."""
        self.active_contexts[config.model] = config
        self.kv_cache_usage[config.model] = config.estimated_memory_gb

        total_usage = sum(self.kv_cache_usage.values())
        if total_usage > self.available_gb * 0.8:
            logger.warning(f"High memory pressure: {total_usage:.1f}GB / {self.available_gb:.1f}GB")

    def release_model(self, model: str) -> None:
        """Release model from tracking."""
        self.active_contexts.pop(model, None)
        self.kv_cache_usage.pop(model, None)

    def get_memory_pressure(self) -> dict[str, Any]:
        """Get current memory pressure status."""
        total_kv = sum(self.kv_cache_usage.values())
        model_count = len(self.active_contexts)

        return {
            "total_memory_gb": self.total_memory_gb,
            "available_gb": self.available_gb,
            "kv_cache_used_gb": total_kv,
            "kv_cache_percent": (total_kv / self.available_gb) * 100,
            "active_models": model_count,
            "can_load_more": total_kv < self.available_gb * 0.7,
            "recommendation": (
                "unload_oldest"
                if total_kv > self.available_gb * 0.8
                else "proceed"
                if total_kv < self.available_gb * 0.5
                else "caution"
            ),
        }

    def get_ollama_options(self, config: ContextConfig) -> dict[str, Any]:
        """Generate Ollama options dict from config."""
        return {
            "num_ctx": config.window_size,
            "num_predict": config.max_tokens,
            "keep_alive": config.keep_alive,
        }

    def suggest_context_for_prompt(
        self,
        model: str,
        prompt: str,
        expected_response_tokens: int = 512,
    ) -> int:
        """Suggest context size for specific prompt."""
        # Rough token estimation (4 chars ≈ 1 token)
        prompt_tokens = len(prompt) // 4
        total_needed = prompt_tokens + expected_response_tokens

        # Add 20% buffer
        suggested = int(total_needed * 1.2)

        # Round to power of 2
        suggested = 2 ** math.ceil(math.log2(suggested))

        # Cap at model max
        profile = self.MODEL_PROFILES.get(model)
        if profile:
            return min(suggested, profile.max_native_ctx)

        return min(suggested, 8192)


def main():
    """Demo context management."""
    manager = OllamaContextManager()

    print("=" * 60)
    print("Ollama Context Manager - SOTA Models")
    print("=" * 60)

    # Show profiles
    print("\nModel Context Profiles:")
    for model, profile in manager.MODEL_PROFILES.items():
        print(f"\n  {model}:")
        print(f"    Max Context: {profile.max_native_ctx:,} tokens")
        print(f"    KV Cache: {profile.kv_cache_gb_per_1k:.2f}GB per 1K tokens")
        print(f"    8K ctx ≈ {profile.estimate_memory_gb(8192):.1f}GB VRAM")

    # Example configurations
    print("\n" + "=" * 60)
    print("Example Configurations")
    print("=" * 60)

    examples = [
        ("gemma3:4b", TaskType.LONG_DOC),
        ("llama3.2:3b", TaskType.CODING),
        ("deepseek-r1:1.5b", TaskType.REASONING),
        ("phi4", TaskType.CODING),
    ]

    for model, task in examples:
        config = manager.get_context_config(model, task)
        print(f"\n{model} + {task.value}:")
        print(f"  Context: {config.window_size:,} tokens")
        print(f"  Max tokens: {config.max_tokens}")
        print(f"  Keep-alive: {config.keep_alive}")
        print(f"  Memory: ~{config.estimated_memory_gb:.1f}GB")
        print(f"  Notes: {', '.join(config.optimization_notes)}")


if __name__ == "__main__":
    main()
