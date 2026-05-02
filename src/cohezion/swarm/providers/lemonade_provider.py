"""Lemonade model provider implementation (local inference, private lemond instance)."""

from __future__ import annotations

import logging
import time
from typing import Any

import aiohttp

from cohezion.swarm.providers.model_provider import GenerationResult, ModelProvider


logger = logging.getLogger(__name__)


class LemonadeProvider(ModelProvider):
    """Lemonade provider for private embeddable server inference.

    Features:
    - Dedicated lemond subprocess management
    - Hardware-specific optimizations (gfx1151)
    - Private execution (isolated from system service)
    - OpenAI-compatible API

    Configuration:
        base_url: Lemonade API URL (default: http://localhost:13307)
        timeout: Request timeout in seconds (default: 120)
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize Lemonade provider.

        Args:
            config: Optional configuration override
        """
        super().__init__(config)

        self.base_url = self.config.get("base_url", "http://localhost:13307")
        self.timeout = self.config.get("timeout", 120)

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
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> GenerationResult:
        """Generate response using private Lemonade instance.

        Args:
            model: Model name
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional options
        """
        session = await self._get_session()
        start_time = time.monotonic()

        # Lemonade follows OpenAI Chat Completions or similar
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
            **kwargs,
        }

        try:
            async with session.post(
                f"{self.base_url}/v1/chat/completions", json=payload, timeout=self.timeout
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})

                latency_ms = (time.monotonic() - start_time) * 1000

                return GenerationResult(
                    text=content,
                    model=model,
                    latency_ms=latency_ms,
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                    success=True,
                )
        except Exception as e:
            logger.error("Lemonade generation failed: %s", e)
            return GenerationResult(
                text="",
                model=model,
                latency_ms=(time.monotonic() - start_time) * 1000,
                success=False,
                error=str(e),
            )

    async def close(self) -> None:
        """Close the provider session."""
        if self._session and not self._session.closed:
            await self._session.close()
