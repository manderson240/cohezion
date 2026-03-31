"""Gemini model provider implementation (Google Cloud, multi-tier cost optimization).

Supports Gemini Flash-Lite, Flash, and Pro models via the Google Generative AI API.
Cost tiers: Flash-Lite ($0.075/M) → Flash ($0.30/M) → Pro ($2.00/M).

Reference: GEMINI_SPECIALIST_PRIME.md — Gemini CLI, Google ADK, 6-protocol stack.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import aiohttp

from cohezion.swarm.providers.model_provider import GenerationResult, ModelProvider


logger = logging.getLogger(__name__)

# Gemini model cost per million tokens (input + output average)
GEMINI_COST_PER_M_TOKENS: dict[str, float] = {
    "gemini-2.0-flash-lite": 0.075,
    "gemini-2.0-flash": 0.30,
    "gemini-2.5-flash": 0.30,
    "gemini-2.5-pro": 2.00,
}

# Model context window sizes
GEMINI_CONTEXT_WINDOWS: dict[str, int] = {
    "gemini-2.0-flash-lite": 1_000_000,
    "gemini-2.0-flash": 1_000_000,
    "gemini-2.5-flash": 1_000_000,
    "gemini-2.5-pro": 2_000_000,
}


class GeminiProvider(ModelProvider):
    """Google Gemini provider for cloud model inference.

    Features:
    - Multi-tier cost optimization (Flash-Lite/Flash/Pro)
    - 1M-2M context windows
    - Multimodal support (text, image, video, audio)
    - Google ADK integration path

    Configuration:
        api_key: Google AI API key (or GOOGLE_API_KEY env var)
        base_url: API base URL (default: generativelanguage.googleapis.com)
        timeout: Request timeout in seconds (default: 30)

    Cost routing (from CLAUDE.md):
        70% simple → Flash-Lite ($0.075/M, near-free)
        20% medium → Flash ($0.30/M)
        10% hard   → Pro ($2.00/M)
    """

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)

        self.api_key = self.config.get("api_key") or os.environ.get("GOOGLE_API_KEY", "")
        self.base_url = self.config.get(
            "base_url", "https://generativelanguage.googleapis.com/v1beta"
        )
        self.timeout = self.config.get("timeout", 30)
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
        """Generate response using Gemini API.

        Args:
            model: Gemini model name (e.g., "gemini-2.5-flash")
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional options (top_p, top_k, system_instruction)

        Returns:
            GenerationResult with response and cost metadata
        """
        if not self.api_key:
            raise RuntimeError("Gemini API key not configured (set GOOGLE_API_KEY)")

        session = await self._get_session()
        start_time = time.time()

        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"

        # Build request payload
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }

        # Optional system instruction
        system_instruction = kwargs.get("system_instruction")
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        # Optional top_p / top_k
        if "top_p" in kwargs:
            payload["generationConfig"]["topP"] = kwargs["top_p"]
        if "top_k" in kwargs:
            payload["generationConfig"]["topK"] = kwargs["top_k"]

        try:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                latency_ms = (time.time() - start_time) * 1000

                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Gemini API error {response.status}: {error_text}")

                data = await response.json()

                # Extract response text
                candidates = data.get("candidates", [])
                if not candidates:
                    raise RuntimeError("Gemini returned no candidates")

                parts = candidates[0].get("content", {}).get("parts", [])
                response_text = "".join(p.get("text", "") for p in parts)

                # Extract token usage
                usage = data.get("usageMetadata", {})
                prompt_tokens = usage.get("promptTokenCount", 0)
                completion_tokens = usage.get("candidatesTokenCount", 0)
                tokens_used = prompt_tokens + completion_tokens

                # Confidence from finish reason
                finish_reason = candidates[0].get("finishReason", "STOP")
                confidence = 0.9 if finish_reason == "STOP" else 0.5

                # Cost estimate
                cost_per_m = GEMINI_COST_PER_M_TOKENS.get(model, 0.30)
                estimated_cost = (tokens_used / 1_000_000) * cost_per_m

                return GenerationResult(
                    response=response_text,
                    model=model,
                    provider="gemini",
                    confidence=confidence,
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    metadata={
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "finish_reason": finish_reason,
                        "estimated_cost_usd": estimated_cost,
                        "cost_per_m_tokens": cost_per_m,
                        "context_window": GEMINI_CONTEXT_WINDOWS.get(model, 1_000_000),
                    },
                )

        except TimeoutError:
            raise RuntimeError(f"Gemini request timed out after {self.timeout}s")

        except aiohttp.ClientError as e:
            raise RuntimeError(f"Gemini connection error: {e}")

    async def list_models(self) -> list[str]:
        """List available Gemini models.

        Returns:
            List of Gemini model identifiers
        """
        if not self.api_key:
            return list(GEMINI_COST_PER_M_TOKENS.keys())

        session = await self._get_session()

        try:
            url = f"{self.base_url}/models?key={self.api_key}"
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    logger.warning("Failed to list Gemini models: %s", response.status)
                    return list(GEMINI_COST_PER_M_TOKENS.keys())

                data = await response.json()
                models = data.get("models", [])
                return [
                    m.get("name", "").replace("models/", "")
                    for m in models
                    if "generateContent" in str(m.get("supportedGenerationMethods", []))
                ]

        except Exception:
            logger.exception("Failed to list Gemini models")
            return list(GEMINI_COST_PER_M_TOKENS.keys())

    async def health_check(self) -> dict[str, Any]:
        """Check Gemini API health.

        Returns:
            Dict with status, latency, available_models
        """
        start_time = time.time()

        try:
            models = await self.list_models()
            latency_ms = (time.time() - start_time) * 1000

            has_key = bool(self.api_key)
            return {
                "status": "healthy" if has_key and models else "degraded",
                "provider": "gemini",
                "api_configured": has_key,
                "latency_ms": latency_ms,
                "available_models": len(models),
                "models": models[:10],
                "cost_tiers": {
                    "lite": "$0.075/M",
                    "flash": "$0.30/M",
                    "pro": "$2.00/M",
                },
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return {
                "status": "unhealthy",
                "provider": "gemini",
                "latency_ms": latency_ms,
                "error": str(e),
            }

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()


# Auto-register Gemini provider
from cohezion.swarm.providers.model_provider import register_model_provider

register_model_provider("gemini", GeminiProvider)
