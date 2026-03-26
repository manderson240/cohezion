"""Anthropic Claude API provider implementation."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from cohezion.swarm.providers.model_provider import GenerationResult, ModelProvider


logger = logging.getLogger(__name__)

ANTHROPIC_MODELS = [
    "claude-sonnet-4-20250514",
    "claude-haiku-3.5-20241022",
    "claude-opus-4-20250514",
]


class AnthropicProvider(ModelProvider):
    """Anthropic Claude API provider.

    Configuration:
        api_key: Anthropic API key (default: from ANTHROPIC_API_KEY env var)
        timeout: Request timeout in seconds (default: 120)
    """

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._api_key = self.config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self._api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY env var "
                "or pass api_key in config."
            )
        self._timeout = self.config.get("timeout", 120)
        self._client: Any = None  # Lazy import to avoid hard dependency

    def _get_client(self) -> Any:
        if self._client is None:
            import anthropic

            self._client = anthropic.AsyncAnthropic(
                api_key=self._api_key,
                timeout=self._timeout,
            )
        return self._client

    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs,
    ) -> GenerationResult:
        from cohezion.reliability import get_circuit

        circuit = get_circuit("anthropic", failure_threshold=3, recovery_timeout=60.0)
        client = self._get_client()
        start_time = time.time()

        try:
            messages = [{"role": "user", "content": prompt}]
            create_kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if "system" in kwargs:
                create_kwargs["system"] = kwargs["system"]

            response = await client.messages.create(**create_kwargs)

            text = response.content[0].text if response.content else ""
            tokens_used = (response.usage.input_tokens or 0) + (response.usage.output_tokens or 0)
            latency_ms = (time.time() - start_time) * 1000

            circuit.record_success()

            return GenerationResult(
                response=text,
                model=model,
                provider="anthropic",
                confidence=0.95,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                metadata={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "stop_reason": response.stop_reason,
                },
            )
        except Exception as e:
            circuit.record_failure()
            latency_ms = (time.time() - start_time) * 1000
            logger.warning("Anthropic generation failed for %s: %s", model, e)
            raise RuntimeError(f"Anthropic generation error: {e}") from e

    async def list_models(self) -> list[str]:
        return list(ANTHROPIC_MODELS)

    async def health_check(self) -> dict[str, Any]:
        start_time = time.time()
        try:
            await self.generate(
                model="claude-haiku-3.5-20241022",
                prompt="ping",
                max_tokens=5,
                temperature=0.0,
            )
            latency_ms = (time.time() - start_time) * 1000
            return {
                "status": "healthy",
                "provider": "anthropic",
                "latency_ms": latency_ms,
                "models": ANTHROPIC_MODELS,
            }
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return {
                "status": "unhealthy",
                "provider": "anthropic",
                "latency_ms": latency_ms,
                "error": str(e),
            }

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


from cohezion.swarm.providers.model_provider import register_model_provider


register_model_provider("anthropic", AnthropicProvider)
