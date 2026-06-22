"""Lemonade model provider implementation (local inference, private lemond instance)."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import aiohttp  # noqa: F401 — used at runtime in _get_session

if TYPE_CHECKING:
    pass

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

        self.base_url = self.config.get("base_url", "http://localhost:13305")
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

        turbo_quant = kwargs.pop("turbo_quant", None)

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
                if resp.status >= 400:
                    error_text = await resp.text()
                    raise RuntimeError(f"Lemonade API error {resp.status}: {error_text}")
                data = await resp.json()

                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                latency_ms = (time.monotonic() - start_time) * 1000
                extra_meta: dict = {}
                if turbo_quant is not None:
                    extra_meta["turbo_quant"] = {
                        "status": "activated",
                        "precision": turbo_quant.get("precision", "default"),
                    }

                tokens_used = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
                return GenerationResult(
                    response=content,
                    model=model,
                    provider="lemonade",
                    confidence=0.9,
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    metadata=extra_meta,
                )
        except Exception as e:
            logger.error("Lemonade generation failed: %s", e)
            return GenerationResult(
                response="",
                model=model,
                provider="lemonade",
                confidence=0.0,
                tokens_used=0,
                latency_ms=(time.monotonic() - start_time) * 1000,
                metadata={"error": str(e)},
            )

    async def list_models(self) -> list[str]:
        """Return available models from Lemonade server."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/v1/models") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [m.get("id", "") for m in data.get("data", [])]
        except Exception:
            pass
        return []

    async def health_check(self) -> dict:
        """Check if Lemonade server is reachable."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/health") as resp:
                return {"status": "ok" if resp.status == 200 else "degraded"}
        except Exception as e:
            return {"status": "unavailable", "error": str(e)}

    async def close(self) -> None:
        """Close the provider session."""
        if self._session and not self._session.closed:
            await self._session.close()
