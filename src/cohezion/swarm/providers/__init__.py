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


# Auto-register local providers
try:
    import cohezion.swarm.providers.gemini_provider
    import cohezion.swarm.providers.gemma4_provider
    import cohezion.swarm.providers.ollama_provider  # noqa: F401
except ImportError:
    pass

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

import contextlib

with contextlib.suppress(Exception):
    from cohezion.swarm.providers.model_provider import GenerationResult as GenerationResult

with contextlib.suppress(Exception):
    from cohezion.swarm.providers.ollama_provider import OllamaProvider as OllamaProvider

with contextlib.suppress(Exception):
    from cohezion.swarm.providers.gemma4_provider import Gemma4Provider as Gemma4Provider

with contextlib.suppress(Exception):
    from cohezion.swarm.providers.gemini_provider import GeminiProvider as GeminiProvider

with contextlib.suppress(Exception):
    from cohezion.swarm.providers.lemonade_provider import (
        LemonadeProvider as LemonadeProvider,
    )

with contextlib.suppress(Exception):
    from cohezion.swarm.providers.multi_model_orchestrator import (
        ComputeUnit as ComputeUnit,
    )
    from cohezion.swarm.providers.multi_model_orchestrator import ModelType as ModelType
    from cohezion.swarm.providers.multi_model_orchestrator import (
        MultiModelOrchestrator as MultiModelOrchestrator,
    )

with contextlib.suppress(Exception):
    from cohezion.swarm.providers.tip_spear_provider import (
        TipSpearProvider as TipSpearProvider,
    )
