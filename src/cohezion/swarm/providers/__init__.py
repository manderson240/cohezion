"""Provider abstraction layer for dynamic technology swapping.

Enables runtime switching between model providers (Ollama, vLLM, HuggingFace, Groq, Together)
and UI generation providers (Stitch, v0, bolt.new, Vercel) without code changes.

Architecture:
  ModelProvider (interface)
    ├─ OllamaProvider (local, AMD ROCm)
    ├─ vLLMProvider (local, CUDA/ROCm)
    ├─ HuggingFaceProvider (cloud API)
    ├─ GroqProvider (cloud, fast)
    └─ TogetherProvider (cloud, many models)

  UIGenerationProvider (interface)
    ├─ StitchProvider (Google Stitch MCP)
    ├─ V0Provider (Vercel v0)
    ├─ BoltNewProvider (StackBlitz bolt.new)
    └─ VercelAIProvider (Vercel AI SDK)

Usage:
    from cohezion.swarm.providers import get_model_provider

    # Runtime selection (from config or env)
    provider = get_model_provider("ollama")  # or "vllm", "groq", etc.
    result = await provider.generate(model="phi3:mini", prompt="Hello")

    # Swap providers without code changes
    provider = get_model_provider("vllm")  # Same interface!
    result = await provider.generate(model="phi3:mini", prompt="Hello")
"""

from cohezion.swarm.providers.model_provider import (
    ModelProvider,
    get_model_provider,
    register_model_provider,
)

try:
    from cohezion.swarm.providers.ui_generation_provider import (
        UIGenerationProvider,
        get_ui_provider,
        register_ui_provider,
    )
except ImportError:
    UIGenerationProvider = None  # type: ignore[assignment, misc]
    get_ui_provider = None  # type: ignore[assignment]
    register_ui_provider = None  # type: ignore[assignment]


__all__ = [
    "ModelProvider",
    "get_model_provider",
    "register_model_provider",
]
