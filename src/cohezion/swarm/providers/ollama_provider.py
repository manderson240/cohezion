# ruff: noqa: B904, E402  # raise pattern in HTTP/API handlers — explicit user-facing errors / deferred imports for circular-dep workarounds
"""Ollama model provider implementation (local inference, AMD ROCm optimized)."""

from __future__ import annotations  # noqa: E402

import logging  # noqa: E402
import time  # noqa: E402
from typing import Any  # noqa: E402

import aiohttp  # noqa: E402

from cohezion.swarm.providers.model_provider import GenerationResult, ModelProvider  # noqa: E402


logger = logging.getLogger(__name__)


class OllamaProvider(ModelProvider):
    """Ollama provider for local model inference.

    Features:
    - AMD ROCm 7 support (Ryzen AI MAX+ 395 optimized)
    - Local execution (zero API cost)
    - Model pool management integration
    - Health monitoring

    Configuration:
        base_url: Ollama API URL (default: http://localhost:11434)
        timeout: Request timeout in seconds (default: 60)
        keep_alive: Model keep-alive duration (default: "5m")
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize Ollama provider.

        Args:
            config: Optional configuration override
        """
        super().__init__(config)

        self.base_url = self.config.get("base_url", "http://localhost:11434")
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
        """Generate response using Ollama.

        Args:
            model: Model name (e.g., "phi3:mini", "qwen2-math:7b")
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional Ollama options (top_p, top_k, etc.)

        Returns:
            GenerationResult with response and metadata
        """
        session = await self._get_session()
        start_time = time.time()

        turbo_quant = kwargs.pop("turbo_quant", None)

        # Prepare request
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,  # Non-streaming for simplicity
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                **kwargs.get("options", {}),
            },
        }

        # Add keep_alive if specified
        if self.keep_alive:
            payload["keep_alive"] = self.keep_alive

        try:
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Ollama API error {response.status}: {error_text}")

                data = await response.json()

                # Extract response
                response_text = data.get("response", "")
                tokens_used = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
                latency_ms = (time.time() - start_time) * 1000

                # Estimate confidence (Ollama doesn't provide this, use heuristics)
                # Length-based heuristic: longer responses = higher confidence
                # This is a simplification; could use logprobs in future
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
            logger.exception(f"Ollama generation failed for model {model}")
            raise RuntimeError(f"Ollama generation error: {e}") from e

    async def list_models(self) -> list[str]:
        """List available Ollama models.

        Returns:
            List of model names (e.g., ["phi3:mini", "qwen2-math:7b"])
        """
        session = await self._get_session()

        try:
            async with session.get(
                f"{self.base_url}/api/tags",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    logger.warning(f"Failed to list Ollama models: {response.status}")
                    return []

                data = await response.json()
                models = data.get("models", [])

                # Extract model names
                return [m.get("name", "") for m in models if m.get("name")]

        except Exception:
            logger.exception("Failed to list Ollama models")
            return []

    async def health_check(self) -> dict[str, Any]:
        """Check Ollama health.

        Returns:
            Dict with status, latency, available_models
        """
        start_time = time.time()

        try:
            # Try to list models as health check
            models = await self.list_models()
            latency_ms = (time.time() - start_time) * 1000

            return {
                "status": "healthy" if models else "degraded",
                "provider": "ollama",
                "base_url": self.base_url,
                "latency_ms": latency_ms,
                "available_models": len(models),
                "models": models[:10],  # First 10 models only
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return {
                "status": "unhealthy",
                "provider": "ollama",
                "base_url": self.base_url,
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
