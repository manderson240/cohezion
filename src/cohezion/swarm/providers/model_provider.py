"""Model provider abstraction for technology-agnostic inference.

Enables runtime swapping between Ollama, vLLM, HuggingFace, Groq, Together.ai
without changing application code.

Design Pattern: Strategy + Registry
- Strategy: ModelProvider interface with multiple implementations
- Registry: Runtime provider selection via configuration
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Result from model generation."""

    response: str
    model: str
    provider: str
    confidence: float  # 0.0-1.0
    tokens_used: int
    latency_ms: float
    metadata: dict[str, Any]


class ModelProvider(ABC):
    """Abstract interface for model providers.

    Implementations:
    - OllamaProvider: Local Ollama (AMD ROCm optimized)
    - vLLMProvider: Local vLLM (CUDA/ROCm, faster inference)
    - HuggingFaceProvider: Cloud HuggingFace API
    - GroqProvider: Cloud Groq (ultra-fast inference)
    - TogetherProvider: Cloud Together.ai (many open models)
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize provider.

        Args:
            config: Provider-specific configuration (API keys, base URLs, etc.)
        """
        self.config = config or {}

    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs,
    ) -> GenerationResult:
        """Generate response from model.

        Args:
            model: Model identifier (provider-specific)
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            **kwargs: Provider-specific options

        Returns:
            GenerationResult with response, confidence, metrics
        """
        pass

    @abstractmethod
    async def list_models(self) -> list[str]:
        """List available models for this provider.

        Returns:
            List of model identifiers
        """
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check provider health.

        Returns:
            Dict with status, latency, available_models
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close provider connections/sessions."""
        pass


# =============================================================================
# Provider Registry
# =============================================================================

_provider_registry: dict[str, type[ModelProvider]] = {}
_provider_instances: dict[str, ModelProvider] = {}


def register_model_provider(name: str, provider_class: type[ModelProvider]) -> None:
    """Register a model provider implementation.

    Args:
        name: Provider name (e.g., "ollama", "vllm", "groq")
        provider_class: ModelProvider subclass
    """
    _provider_registry[name] = provider_class
    logger.info(f"Registered model provider: {name}")


def get_model_provider(name: str, config: dict[str, Any] | None = None, use_singleton: bool = True) -> ModelProvider:
    """Get model provider by name.

    Args:
        name: Provider name (e.g., "ollama", "vllm", "groq")
        config: Provider configuration (optional)
        use_singleton: If True, return cached instance (default: True)

    Returns:
        ModelProvider instance

    Raises:
        ValueError: If provider not registered
    """
    if name not in _provider_registry:
        available = ", ".join(_provider_registry.keys())
        raise ValueError(f"Model provider '{name}' not registered. Available: {available}")

    # Return singleton instance if requested and available
    if use_singleton and name in _provider_instances:
        return _provider_instances[name]

    # Create new instance
    provider_class = _provider_registry[name]
    instance = provider_class(config=config)

    # Cache if singleton
    if use_singleton:
        _provider_instances[name] = instance

    return instance


def list_providers() -> list[str]:
    """List all registered provider names.

    Returns:
        List of provider names (e.g., ["ollama", "vllm", "groq"])
    """
    return list(_provider_registry.keys())
