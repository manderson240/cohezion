"""Ollama Cloud provider — remote Ollama with auth headers."""

from __future__ import annotations

import logging
import os
from typing import Any

import aiohttp

from cohezion.swarm.providers.model_provider import GenerationResult
from cohezion.swarm.providers.ollama_provider import OllamaProvider


logger = logging.getLogger(__name__)


class OllamaCloudProvider(OllamaProvider):
    """Cloud-hosted Ollama provider.

    Same API as local Ollama but with remote base URL and Bearer auth.

    Configuration:
        base_url: Cloud Ollama URL (default: from OLLAMA_CLOUD_URL env var)
        api_key: Auth token (default: from OLLAMA_CLOUD_API_KEY env var)
        timeout: Request timeout in seconds (default: 120)
    """

    def __init__(self, config: dict[str, Any] | None = None):
        config = config or {}
        cloud_url = config.get("base_url") or os.environ.get("OLLAMA_CLOUD_URL", "")
        if not cloud_url:
            raise ValueError(
                "Ollama Cloud URL required. Set OLLAMA_CLOUD_URL env var "
                "or pass base_url in config."
            )
        merged = {
            "base_url": cloud_url,
            "timeout": config.get("timeout", 120),
            "keep_alive": config.get("keep_alive", "5m"),
        }
        super().__init__(config=merged)
        self._api_key = config.get("api_key") or os.environ.get("OLLAMA_CLOUD_API_KEY", "")

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers: dict[str, str] = {}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs,
    ) -> GenerationResult:
        from cohezion.reliability import get_circuit

        circuit = get_circuit("ollama-cloud", failure_threshold=3, recovery_timeout=30.0)

        try:
            result = await super().generate(model, prompt, max_tokens, temperature, **kwargs)
            # Override provider name to distinguish from local
            result = GenerationResult(
                response=result.response,
                model=result.model,
                provider="ollama-cloud",
                confidence=result.confidence,
                tokens_used=result.tokens_used,
                latency_ms=result.latency_ms,
                metadata=result.metadata,
            )
            circuit.record_success()
            return result
        except Exception as e:
            circuit.record_failure()
            logger.warning("Ollama Cloud generation failed for %s: %s", model, e)
            raise RuntimeError(f"Ollama Cloud error: {e}") from e

    async def health_check(self) -> dict[str, Any]:
        result = await super().health_check()
        result["provider"] = "ollama-cloud"
        return result


from cohezion.swarm.providers.model_provider import register_model_provider


register_model_provider("ollama-cloud", OllamaCloudProvider)
