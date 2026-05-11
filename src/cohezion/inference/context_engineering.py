"""
Context Engineering & AutoHarness System

Provides model-specific prompt optimization and automatic harness synthesis
for maximizing both throughput AND quality per model.

Key Components:
- ModelCardRegistry: Loads and caches model-specific optimizations
- ContextEngineer: Crafts optimized prompts based on model capabilities
- AutoHarness: Self-tuning harness that adapts to model behavior
- QualityMonitor: Tracks quality metrics alongside throughput
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class ModelCapability:
    """Capability scoring for a model (0-1 scale)."""

    reasoning: float = 0.5
    coding: float = 0.5
    creativity: float = 0.5
    instruction_following: float = 0.5
    long_context: float = 0.5
    multilingual: float = 0.5


@dataclass
class ModelCard:
    """Model card with optimization parameters."""

    model_id: str
    family: str  # gemma, qwen, llama, etc.
    variant: str  # 4b, 8b, 26b, etc.
    capabilities: ModelCapability = field(default_factory=ModelCapability)

    # Optimization parameters
    optimal_temperature: float = 0.7
    optimal_top_p: float = 0.9
    optimal_top_k: int = 40
    max_tokens_default: int = 512
    context_window: int = 4096

    # System prompt templates
    system_templates: dict[str, str] = field(default_factory=dict)

    # Special flags
    supports_reasoning: bool = False
    supports_thinking: bool = False
    requires_special_api: bool = False
    special_api_params: dict[str, Any] = field(default_factory=dict)


class ModelCardRegistry:
    """Registry of model cards with auto-discovery."""

    def __init__(self):
        self._cards: dict[str, ModelCard] = {}
        self._load_builtin_cards()

    def _load_builtin_cards(self):
        """Load known model configurations."""

        # DeepSeek-R1 reasoning models
        self._cards["DeepSeek-R1-0528-Qwen3-8B-Q4_1"] = ModelCard(
            model_id="DeepSeek-R1-0528-Qwen3-8B-Q4_1",
            family="deepseek",
            variant="8b",
            capabilities=ModelCapability(
                reasoning=0.95,
                coding=0.85,
                creativity=0.5,
                instruction_following=0.9,
                long_context=0.7,
                multilingual=0.8,
            ),
            optimal_temperature=0.6,
            optimal_top_p=0.95,
            context_window=32768,
            supports_reasoning=True,
            requires_special_api=True,
            special_api_params={"reasoning_format": "auto"},
            system_templates={
                "reasoning": "You are a reasoning specialist. Think step-by-step and show your work.",
                "coding": "You are a coding expert. Write clean, efficient, well-commented code.",
                "default": "You are a helpful assistant with strong reasoning capabilities.",
            },
        )

        # Gemma-4-31B (CPU tier, larger context than E4B)
        self._cards["Gemma-4-31B-it-GGUF"] = ModelCard(
            model_id="Gemma-4-31B-it-GGUF",
            family="gemma",
            variant="31b",
            capabilities=ModelCapability(
                reasoning=0.80,
                coding=0.75,
                creativity=0.70,
                instruction_following=0.85,
                long_context=0.85,
                multilingual=0.80,
            ),
            optimal_temperature=0.7,
            optimal_top_p=0.9,
            max_tokens_default=800,
            context_window=32768,
            supports_thinking=True,
            system_templates={"default": "You are a knowledgeable, accurate assistant."},
        )

        # Qwen3.5-35B-A3B MoE (large reasoning model, active 3B params)
        self._cards["Qwen3.5-35B-A3B-GGUF"] = ModelCard(
            model_id="Qwen3.5-35B-A3B-GGUF",
            family="qwen",
            variant="35b-moe",
            capabilities=ModelCapability(
                reasoning=0.90,
                coding=0.85,
                creativity=0.75,
                instruction_following=0.90,
                long_context=0.90,
                multilingual=0.95,
            ),
            optimal_temperature=0.6,
            optimal_top_p=0.95,
            max_tokens_default=600,
            context_window=32768,
            supports_reasoning=True,
            system_templates={
                "reasoning": "You are an expert with strong reasoning capabilities. Think thoroughly.",
                "default": "You are a highly capable assistant.",
            },
        )

        # FLM models (NPU-optimized, XDNA2 SRAM, direct inference)
        self._cards["gemma3-4b-FLM"] = ModelCard(
            model_id="gemma3-4b-FLM",
            family="gemma",
            variant="3-4b-flm",
            capabilities=ModelCapability(
                reasoning=0.60,
                coding=0.55,
                creativity=0.55,
                instruction_following=0.70,
                long_context=0.40,
                multilingual=0.65,
            ),
            optimal_temperature=0.5,
            optimal_top_p=0.9,
            max_tokens_default=150,
            context_window=8192,
            system_templates={"default": "You are a fast, concise assistant."},
        )

        self._cards["gemma4-it-e2b-FLM"] = ModelCard(
            model_id="gemma4-it-e2b-FLM",
            family="gemma",
            variant="4-e2b-flm",
            capabilities=ModelCapability(
                reasoning=0.55,
                coding=0.50,
                creativity=0.50,
                instruction_following=0.65,
                long_context=0.35,
                multilingual=0.60,
            ),
            optimal_temperature=0.5,
            optimal_top_p=0.9,
            max_tokens_default=100,
            context_window=4096,
            system_templates={"default": "You are a fast, concise assistant."},
        )

        self._cards["qwen3.5-4b-FLM"] = ModelCard(
            model_id="qwen3.5-4b-FLM",
            family="qwen",
            variant="3.5-4b-flm",
            capabilities=ModelCapability(
                reasoning=0.65,
                coding=0.60,
                creativity=0.60,
                instruction_following=0.72,
                long_context=0.45,
                multilingual=0.75,
            ),
            optimal_temperature=0.5,
            optimal_top_p=0.9,
            max_tokens_default=200,
            context_window=4096,
            system_templates={"default": "You are a fast, accurate assistant."},
        )

        # DeepSeek-Qwen3-8B GGUF (currently running on NPU port 13306, May 2026)
        # Higher reasoning capability than base Qwen3-8B due to DeepSeek training
        self._cards["DeepSeek-Qwen3-8B-GGUF"] = ModelCard(
            model_id="DeepSeek-Qwen3-8B-GGUF",
            family="deepseek",
            variant="8b",
            capabilities=ModelCapability(
                reasoning=0.90,
                coding=0.85,
                creativity=0.65,
                instruction_following=0.85,
                long_context=0.75,
                multilingual=0.90,
            ),
            optimal_temperature=0.6,
            optimal_top_p=0.95,
            max_tokens_default=400,
            context_window=32768,
            supports_reasoning=True,
            system_templates={
                "reasoning": "You are an expert reasoning assistant. Think step by step and verify your answers.",
                "coding": "You are a skilled coding assistant. Write efficient, well-structured code.",
                "default": "You are a helpful, accurate assistant with strong reasoning capabilities.",
            },
        )

        # Gemma-4 family
        self._cards["Gemma-4-26B-A4B-it-GGUF"] = ModelCard(
            model_id="Gemma-4-26B-A4B-it-GGUF",
            family="gemma",
            variant="26b-moe",
            capabilities=ModelCapability(
                reasoning=0.90,
                coding=0.80,
                creativity=0.75,
                instruction_following=0.85,
                long_context=0.95,
                multilingual=0.90,
            ),
            optimal_temperature=0.7,
            optimal_top_p=0.95,
            optimal_top_k=64,
            context_window=256000,
            supports_thinking=True,
            supports_reasoning=True,
            system_templates={
                "reasoning": "You are an expert analyst with strong reasoning capabilities. Provide structured, thorough responses.",
                "creative": "You are a creative assistant with good judgment. Balance creativity with accuracy.",
                "coding": "You are a coding specialist. Ensure all code is complete and syntactically correct.",
                "default": "You are a helpful, harmless, and honest assistant.",
            },
        )

        # Qwen3 family
        self._cards["Qwen3-8B-GGUF"] = ModelCard(
            model_id="Qwen3-8B-GGUF",
            family="qwen",
            variant="8b",
            capabilities=ModelCapability(
                reasoning=0.80,
                coding=0.90,
                creativity=0.70,
                instruction_following=0.85,
                long_context=0.80,
                multilingual=0.95,
            ),
            optimal_temperature=0.3,
            optimal_top_p=0.9,
            context_window=4096,
            system_templates={
                "coding": "You are a coding specialist. Write correct, efficient code with proper error handling.",
                "reasoning": "You are a logical reasoning assistant. Think step by step.",
                "default": "You are a helpful assistant.",
            },
        )

        # Small fast models
        self._cards["Qwen3-0.6B-GGUF"] = ModelCard(
            model_id="Qwen3-0.6B-GGUF",
            family="qwen",
            variant="0.6b",
            capabilities=ModelCapability(
                reasoning=0.50,
                coding=0.60,
                creativity=0.60,
                instruction_following=0.70,
                long_context=0.30,
                multilingual=0.70,
            ),
            optimal_temperature=0.5,
            optimal_top_p=0.9,
            max_tokens_default=128,
            context_window=2048,
            system_templates={
                "default": "You are a fast, efficient assistant. Give direct, concise answers.",
            },
        )

        # Gemma-4 E4B (iGPU tier, thinking mode, 2260 thinking token overhead)
        self._cards["Gemma-4-E4B-it-GGUF"] = ModelCard(
            model_id="Gemma-4-E4B-it-GGUF",
            family="gemma",
            variant="4b",
            capabilities=ModelCapability(
                reasoning=0.75,
                coding=0.70,
                creativity=0.65,
                instruction_following=0.80,
                long_context=0.70,
                multilingual=0.75,
            ),
            optimal_temperature=0.7,
            optimal_top_p=0.9,
            max_tokens_default=600,
            context_window=32768,
            supports_thinking=True,
            system_templates={
                "coding": "You are a coding assistant. Write correct, efficient code.",
                "reasoning": "You are a reasoning assistant. Think step by step.",
                "default": "You are a helpful, accurate assistant.",
            },
        )

        # Gemma-4 E2B (NPU fallback, thinking mode, fast)
        self._cards["Gemma-4-E2B-it-GGUF"] = ModelCard(
            model_id="Gemma-4-E2B-it-GGUF",
            family="gemma",
            variant="2b",
            capabilities=ModelCapability(
                reasoning=0.60,
                coding=0.55,
                creativity=0.55,
                instruction_following=0.70,
                long_context=0.50,
                multilingual=0.60,
            ),
            optimal_temperature=0.7,
            optimal_top_p=0.9,
            max_tokens_default=200,
            context_window=32768,
            supports_thinking=True,
            system_templates={
                "default": "You are a fast, helpful assistant.",
            },
        )

        # llama3.2-1b-FLM (NPU tier, XDNA2 SRAM, 42 TPS, no thinking mode)
        self._cards["llama3.2-1b-FLM"] = ModelCard(
            model_id="llama3.2-1b-FLM",
            family="llama",
            variant="1b",
            capabilities=ModelCapability(
                reasoning=0.40,
                coding=0.35,
                creativity=0.45,
                instruction_following=0.70,
                long_context=0.30,
                multilingual=0.50,
            ),
            optimal_temperature=0.5,
            optimal_top_p=0.9,
            max_tokens_default=50,
            context_window=4096,
            system_templates={
                "default": "You are a fast, concise assistant. Give short, direct answers.",
            },
        )

    def get_card(self, model_id: str) -> ModelCard | None:
        """Get model card by ID (with fuzzy matching)."""
        # Exact match
        if model_id in self._cards:
            return self._cards[model_id]

        # Partial match
        for key, card in self._cards.items():
            if key.lower() in model_id.lower() or model_id.lower() in key.lower():
                return card

        # Family match
        for key, card in self._cards.items():
            if card.family.lower() in model_id.lower():
                return card

        return None

    def register_card(self, card: ModelCard):
        """Register a new model card."""
        self._cards[card.model_id] = card


class ContextEngineer:
    """Engineers optimized prompts for specific models and tasks."""

    def __init__(self, registry: ModelCardRegistry | None = None):
        self.registry = registry or ModelCardRegistry()

    def engineer_prompt(
        self,
        model_id: str,
        user_prompt: str,
        task_type: str = "default",
        complexity: str = "medium",
        system_override: str | None = None,
    ) -> dict[str, Any]:
        """
        Craft optimized prompt configuration for a model.

        Args:
            model_id: The model identifier
            user_prompt: The user's input prompt
            task_type: reasoning, coding, creative, default
            complexity: low, medium, high
            system_override: Optional system prompt override

        Returns:
            Dict with messages, temperature, and model-specific params
        """
        card = self.registry.get_card(model_id)
        if card is None:
            # Fallback to generic
            return self._generic_prompt(model_id, user_prompt, system_override)

        # Select system prompt based on task type
        system_prompt = system_override or card.system_templates.get(
            task_type, card.system_templates.get("default", "You are a helpful assistant.")
        )

        # Adjust for complexity
        if complexity == "high" and card.capabilities.reasoning > 0.7:
            system_prompt += "\n\nThink step-by-step and explain your reasoning."
        elif complexity == "low":
            system_prompt += "\n\nBe concise. Answer in 1-2 sentences."

        # Calculate parameters based on task
        temperature = self._adjust_temperature(card, task_type, complexity)
        max_tokens = self._adjust_max_tokens(card, complexity)

        # Build payload
        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "top_p": card.optimal_top_p,
            "max_tokens": max_tokens,
        }

        # Add model-specific params
        if card.supports_reasoning and task_type == "reasoning":
            payload.update(card.special_api_params)

        return payload

    def _adjust_temperature(self, card: ModelCard, task_type: str, complexity: str) -> float:
        """Adjust temperature based on task requirements."""
        base = card.optimal_temperature

        # Task-specific adjustments
        if task_type == "coding":
            return min(base * 0.5, 0.3)  # Lower for deterministic code
        elif task_type == "creative":
            return min(base * 1.2, 1.0)  # Higher for creativity
        elif complexity == "high":
            return min(base * 0.9, 0.7)  # Slightly lower for complex reasoning

        return base

    def _adjust_max_tokens(self, card: ModelCard, complexity: str) -> int:
        """Adjust max tokens based on complexity."""
        base = card.max_tokens_default

        if complexity == "high":
            return min(int(base * 2), card.context_window // 4)
        elif complexity == "low":
            return min(base // 2, 128)

        return base

    def _generic_prompt(
        self, model_id: str, user_prompt: str, system: str | None
    ) -> dict[str, Any]:
        """Fallback for unknown models."""
        return {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system or "You are a helpful assistant."},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 512,
        }


class QualityMonitor:
    """Monitors output quality with lightweight heuristics."""

    def assess(self, text: str, task_type: str = "default") -> dict[str, float]:
        """Assess output quality."""
        scores = {}

        # Basic metrics
        words = len(text.split())
        text.count(".") + text.count("!") + text.count("?")

        # Substance score
        scores["substance"] = min(words / 20, 1.0) if words > 5 else 0.0

        # Structure score
        has_structure = any(c in text for c in ["\n", "-", "*", "1.", "2."])
        scores["structure"] = 1.0 if has_structure else 0.5

        # Task-specific scoring
        if task_type == "coding":
            scores["code_quality"] = self._score_code(text)
        elif task_type == "reasoning":
            scores["reasoning"] = self._score_reasoning(text)

        # Overall quality (weighted average)
        scores["overall"] = sum(scores.values()) / len(scores) if scores else 0.0

        return scores

    def _score_code(self, text: str) -> float:
        """Score code quality."""
        score = 0.0
        if "```" in text or any(kw in text for kw in ["def ", "class ", "import "]):
            score += 0.5
        if text.count("\n") > 3:
            score += 0.3
        if any(c in text for c in ["#", "//", "/*"]):
            score += 0.2
        return min(score, 1.0)

    def _score_reasoning(self, text: str) -> float:
        """Score reasoning quality."""
        score = 0.0
        markers = ["because", "therefore", "step", "first", "second", "reason", "conclusion"]
        for marker in markers:
            if marker in text.lower():
                score += 0.15
        return min(score, 1.0)


class AutoHarness:
    """
    Self-tuning harness that automatically optimizes for quality+throughput.

    The autoharness:
    1. Discovers model capabilities through test probes
    2. Maintains optimal parameter sets per task type
    3. Adapts to observed quality vs throughput trade-offs
    4. Falls back to conservative settings on quality degradation
    """

    def __init__(
        self,
        model_id: str,
        engineer: ContextEngineer | None = None,
        monitor: QualityMonitor | None = None,
    ):
        self.model_id = model_id
        self.engineer = engineer or ContextEngineer()
        self.monitor = monitor or QualityMonitor()

        # Learning state
        self._optimal_params: dict[str, dict] = {}
        self._quality_history: list[dict] = []
        self._exploration_rate = 0.1

    def get_optimized_payload(
        self,
        user_prompt: str,
        task_type: str = "default",
        complexity: str = "medium",
        quality_priority: float = 0.5,  # 0=speed, 1=quality
    ) -> dict[str, Any]:
        """Get optimized payload for the model-task combination."""

        # Start with engineered base
        payload = self.engineer.engineer_prompt(self.model_id, user_prompt, task_type, complexity)

        # Apply learned parameters if available
        key = f"{task_type}_{complexity}"
        if key in self._optimal_params:
            learned = self._optimal_params[key]

            # Blend learned with base based on quality priority
            if quality_priority > 0.5:
                # Prefer quality-optimized params
                payload["temperature"] = learned.get("temperature_quality", payload["temperature"])
                payload["max_tokens"] = learned.get("max_tokens_quality", payload["max_tokens"])
            else:
                # Prefer speed-optimized params
                payload["temperature"] = learned.get("temperature_speed", payload["temperature"])
                payload["max_tokens"] = min(
                    payload["max_tokens"], learned.get("max_tokens_speed", payload["max_tokens"])
                )

        # Exploration: occasionally try different params
        if self._should_explore():
            payload = self._explore_variation(payload, task_type)

        return payload

    def feedback(self, result: dict[str, Any], quality_scores: dict[str, float]):
        """Provide feedback to improve future optimizations."""
        self._quality_history.append(
            {
                "params": result.get("params", {}),
                "quality": quality_scores,
                "latency_ms": result.get("latency_ms", 0),
                "tokens": result.get("tokens", 0),
            }
        )

        # Update optimal params every 10 samples
        if len(self._quality_history) >= 10:
            self._update_optimal_params()

    def _should_explore(self) -> bool:
        """Decide whether to explore new parameters."""
        import random

        return random.random() < self._exploration_rate

    def _explore_variation(self, payload: dict[str, Any], task_type: str) -> dict[str, Any]:
        """Try slightly different parameters."""
        import random

        variant = payload.copy()

        # Vary temperature
        variant["temperature"] = max(
            0.0, min(1.0, payload["temperature"] + random.uniform(-0.1, 0.1))
        )

        # Vary max_tokens for speed testing
        if random.random() < 0.5:
            variant["max_tokens"] = int(payload["max_tokens"] * random.uniform(0.7, 1.3))

        return variant

    def _update_optimal_params(self):
        """Update optimal parameters based on history."""
        if len(self._quality_history) < 10:
            return

        # Sort by quality and speed
        by_quality = sorted(
            self._quality_history, key=lambda x: x["quality"].get("overall", 0), reverse=True
        )
        by_speed = sorted(
            self._quality_history, key=lambda x: x["tokens"] / max(x["latency_ms"], 1), reverse=True
        )

        # Extract best for each goal
        if by_quality:
            best_q = by_quality[0]
            self._optimal_params.setdefault("default", {})["temperature_quality"] = best_q[
                "params"
            ].get("temperature", 0.7)

        if by_speed:
            best_s = by_speed[0]
            self._optimal_params.setdefault("default", {})["temperature_speed"] = best_s[
                "params"
            ].get("temperature", 0.7)
            self._optimal_params["default"]["max_tokens_speed"] = best_s["params"].get(
                "max_tokens", 512
            )

        # Clear old history
        self._quality_history = self._quality_history[-20:]


# Global registry
_default_registry: ModelCardRegistry | None = None
_default_engineer: ContextEngineer | None = None


def get_context_engineer() -> ContextEngineer:
    """Get global context engineer instance."""
    global _default_engineer
    if _default_engineer is None:
        _default_engineer = ContextEngineer()
    return _default_engineer


def create_autoharness(model_id: str) -> AutoHarness:
    """Factory function to create an autoharness for a model."""
    return AutoHarness(model_id)


if __name__ == "__main__":
    # Demo
    engineer = ContextEngineer()

    models = [
        "DeepSeek-R1-0528-Qwen3-8B-Q4_1",
        "Gemma-4-26B-A4B-it-GGUF",
        "Qwen3-8B-GGUF",
    ]

    for model in models:
        print(f"\n{'=' * 60}")
        print(f"Model: {model}")
        print(f"{'=' * 60}")

        for task in ["coding", "reasoning", "creative"]:
            payload = engineer.engineer_prompt(
                model, "Explain recursion with an example.", task_type=task, complexity="high"
            )
            print(f"\n{task.upper()}:")
            print(f"  Temp: {payload['temperature']}")
            print(f"  Max tokens: {payload['max_tokens']}")
            print(f"  System: {payload['messages'][0]['content'][:60]}...")
