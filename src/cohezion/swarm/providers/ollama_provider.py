# ruff: noqa: B904, E402  # raise pattern in HTTP/API handlers — explicit user-facing errors / deferred imports for circular-dep workarounds
"""Ollama model provider — thin shim that routes through the lemonade router (:13305).

Phase 1 migration (2026-06-09): OllamaProvider.generate() now delegates to
LemonadeRouterClient using the R2 model-catalog map.  The class is retained
non-destructively per the non-destructive-wiring policy; Phase 4 will retire
the shell after full verification.

R2 model-catalog map (Ollama model → lemonade router model):
  qwen3:8b          → Qwen3-8B-GGUF
  deepseek-r1:7b    → DeepSeek-Qwen3-8B-GGUF
  qwen3-coder:30b   → Qwen3.6-35B-A3B-ThinkingCoder
  nomic-embed-text  → nomic-embed-text-v2-moe-GGUF

Allow-listed Ollama shim (no router equivalent as of 2026-06-09):
  phi4:latest, phi3:mini, deepseek-r1:70b
  (marked with # allow-direct-port: no router equivalent (R2))
"""

from __future__ import annotations

import logging
import time
from typing import Any

import aiohttp

from cohezion.swarm.providers.model_provider import GenerationResult, ModelProvider


logger = logging.getLogger(__name__)

# R2: Ollama model → lemonade router model-id map.
# Keys are Ollama model names as callers pass them.
_OLLAMA_TO_ROUTER: dict[str, str] = {
    "qwen3:8b": "Qwen3-8B-GGUF",
    "qwen3": "Qwen3-8B-GGUF",
    "deepseek-r1:7b": "DeepSeek-Qwen3-8B-GGUF",
    "qwen3-coder:30b": "Qwen3.6-35B-A3B-ThinkingCoder",
    "qwen3-coder": "Qwen3.6-35B-A3B-ThinkingCoder",
    "nomic-embed-text": "nomic-embed-text-v2-moe-GGUF",
}

# R2: Models with no router equivalent — retained as direct Ollama shims.
# These are the ONLY models that still hit :11434 directly.  # allow-direct-port: comment documenting R2 shim design (not a live route)
_OLLAMA_SHIM_MODELS: frozenset[str] = frozenset(
    {
        "phi4:latest",
        "phi4",
        "phi3:mini",
        "phi3",
        "deepseek-r1:70b",
        "deepseek-r1",  # catch-all for unlisted deepseek-r1 variants
    }
)

# Default router URL; callers can override via config["lemonade_router_url"].
_ROUTER_URL = "http://localhost:13305"
# Fallback Ollama URL for shim models only.
_OLLAMA_SHIM_URL = "http://localhost:11434"  # allow-direct-port: no router equivalent (R2)


class OllamaProvider(ModelProvider):
    """Ollama provider — now routes through lemonade router (:13305).

    DEPRECATED (Phase 4 retirement target).  Existing callers continue to
    work; generate() delegates to LemonadeRouterClient via the R2 map.
    Models without a router equivalent fall back to the Ollama shim.

    Features:
    - AMD ROCm 7 support (Ryzen AI MAX+ 395 optimized)
    - Local execution (zero API cost)
    - Model pool management integration
    - Health monitoring

    Configuration:
        base_url: Ollama API URL (preserved for shim callers; ignored for
                  router-mapped models)
        lemonade_router_url: Lemonade router URL (default: http://localhost:13305)
        timeout: Request timeout in seconds (default: 60)
        keep_alive: Model keep-alive duration (default: "5m")
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize Ollama provider.

        Args:
            config: Optional configuration override
        """
        super().__init__(config)

        # Retain base_url for shim path (models with no router equivalent).
        self.base_url = self.config.get("base_url", _OLLAMA_SHIM_URL)
        self.router_url = self.config.get("lemonade_router_url", _ROUTER_URL)
        self.timeout = self.config.get("timeout", 60)
        self.keep_alive = self.config.get("keep_alive", "5m")

        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs,
    ) -> GenerationResult:
        """Generate response, routing through lemonade router where possible (R2).

        For models in the catalog map: uses LemonadeRouterClient at :13305.
        For shim models (phi4, phi3, deepseek-r1:70b): falls back to Ollama.

        Args:
            model: Model name (e.g., "phi3:mini", "qwen3:8b")
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional options (Ollama options dict forwarded if shim)

        Returns:
            GenerationResult with response and metadata
        """
        router_model = _OLLAMA_TO_ROUTER.get(model)
        if router_model is not None:
            return await self._generate_via_router(
                router_model, prompt, max_tokens, temperature, **kwargs
            )
        # Check if this is a shim-only model or unknown model
        # Unknown models default to router with the model name as-is
        shim_key = model.split(":")[0] if ":" in model else model
        if shim_key in {m.split(":")[0] for m in _OLLAMA_SHIM_MODELS}:
            return await self._generate_via_ollama_shim(
                model, prompt, max_tokens, temperature, **kwargs
            )
        # Unknown model: attempt router with literal model name
        return await self._generate_via_router(model, prompt, max_tokens, temperature, **kwargs)

    async def _generate_via_router(
        self,
        router_model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        **kwargs: Any,
    ) -> GenerationResult:
        """Route through LemonadeRouterClient at :13305."""
        from cohezion.inference.router_client import LemonadeRouterClient

        options = kwargs.get("options", {})
        turbo_quant = kwargs.pop("turbo_quant", None)

        client = LemonadeRouterClient.from_ollama_options(
            self.router_url,
            model_id=router_model,
            options={
                "num_predict": max_tokens,
                "temperature": temperature,
                **options,
            },
        )
        start_time = time.time()
        result = await client.run(prompt)
        latency_ms = (time.time() - start_time) * 1000

        meta: dict[str, Any] = {}
        if turbo_quant is not None:
            meta["turbo_quant"] = {"status": "router-routed"}
        if result.dropped_options:
            meta["dropped_options"] = result.dropped_options

        return GenerationResult(
            response=result.text,
            model=router_model,
            provider="lemonade",
            confidence=0.9 if not result.error else 0.0,
            tokens_used=0,  # router doesn't return token counts in this path
            latency_ms=latency_ms,
            metadata=meta,
        )

    async def _generate_via_ollama_shim(
        self,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        **kwargs: Any,
    ) -> GenerationResult:
        """Thin shim for models with no router equivalent (phi4, phi3, deepseek-r1:70b).

        These models are retained as allow-direct-port exceptions (R2).
        # allow-direct-port: no router equivalent (R2)
        """
        session = await self._get_session()
        start_time = time.time()

        turbo_quant = kwargs.pop("turbo_quant", None)

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                **kwargs.get("options", {}),
            },
        }

        if self.keep_alive:
            payload["keep_alive"] = self.keep_alive

        try:
            async with session.post(
                f"{self.base_url}/api/generate",  # allow-direct-port: no router equivalent (R2)
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Ollama API error {response.status}: {error_text}")

                data = await response.json()

                response_text = data.get("response", "")
                tokens_used = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
                latency_ms = (time.time() - start_time) * 1000

                confidence = min(1.0, len(response_text) / max(max_tokens * 4, 100))

                meta: dict = {
                    "total_duration": data.get("total_duration", 0),
                    "load_duration": data.get("load_duration", 0),
                    "prompt_eval_count": data.get("prompt_eval_count", 0),
                    "eval_count": data.get("eval_count", 0),
                }
                if turbo_quant is not None:
                    meta["turbo_quant"] = {"status": "fallback-standard"}

                return GenerationResult(
                    response=response_text,
                    model=model,
                    provider="ollama",
                    confidence=confidence,
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    metadata=meta,
                )

        except TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            raise RuntimeError(f"Ollama request timed out after {self.timeout}s") from None

        except Exception as e:
            logger.exception(f"Ollama shim generation failed for model {model}")
            raise RuntimeError(f"Ollama generation error: {e}") from e

    async def list_models(self) -> list[str]:
        """List available models (router catalog + shim fallback).

        Returns:
            List of model names
        """
        try:
            from cohezion.inference.router_client import LemonadeRouterClient

            client = LemonadeRouterClient(self.router_url, model_id="placeholder")
            router_models = await client.list_models()
            if router_models:
                return router_models
        except Exception:
            pass

        # Fallback: list Ollama shim models  # allow-direct-port: no router equivalent (R2)
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.base_url}/api/tags",  # allow-direct-port: no router equivalent (R2)
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    logger.warning(f"Failed to list Ollama models: {response.status}")
                    return []
                data = await response.json()
                models = data.get("models", [])
                return [m.get("name", "") for m in models if m.get("name")]
        except Exception:
            logger.exception("Failed to list Ollama models")
            return []

    async def health_check(self) -> dict[str, Any]:
        """Check health against lemonade router.

        Returns:
            Dict with status, latency, available_models
        """
        start_time = time.time()

        try:
            models = await self.list_models()
            latency_ms = (time.time() - start_time) * 1000

            return {
                "status": "healthy" if models else "degraded",
                "provider": "lemonade",
                "base_url": self.router_url,
                "latency_ms": latency_ms,
                "available_models": len(models),
                "models": models[:10],
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return {
                "status": "unhealthy",
                "provider": "lemonade",
                "base_url": self.router_url,
                "latency_ms": latency_ms,
                "error": str(e),
            }

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()


# Auto-register Ollama provider
from cohezion.swarm.providers.model_provider import register_model_provider  # noqa: E402


register_model_provider("ollama", OllamaProvider)
