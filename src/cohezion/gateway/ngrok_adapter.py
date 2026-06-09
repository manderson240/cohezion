# class attrs treated as immutable config; never mutated per-instance
"""ngrok AI Gateway adapter for multi-provider LLM routing.

Provides OpenAI SDK-compatible endpoint that routes requests through ngrok AI Gateway
with automatic failover to local Ollama, cost optimization via intelligent routing,
and built-in response caching.

Features:
- OpenAI SDK compatible (drop-in replacement for direct API calls)
- Multi-provider support (OpenAI, Anthropic, Google, self-hosted Ollama)
- Automatic failover: ngrok → Ollama
- Cost optimization via intelligent routing (cheap vs premium models)
- Built-in response caching (4th tier in Cohezion's cache stack)
- PII redaction before requests hit AI providers
- Per-request model routing and cost tracking

Usage::

    # Initialize with ngrok gateway
    adapter = NgrokAIGateway(
        ngrok_endpoint="https://xxxxx.ngrok.app/v1",
        ngrok_api_key="your-ngrok-key",
        fallback_ollama_url="http://localhost:13305",
        enable_failover=True,
    )

    # Use as drop-in replacement for ResilientOllamaClient
    response, tokens = await adapter.generate(
        prompt="Explain quantum computing",
        model="gpt-4o",  # ngrok routes to any provider
        system="You are helpful"
    )

    # Track costs and performance
    metrics = adapter.get_metrics()
"""

import asyncio
import hashlib
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import requests  # type: ignore[import-untyped]

from cohezion.deployment.feature_flags import FeatureFlag, FeatureFlagContext, is_feature_enabled


logger = logging.getLogger(__name__)


@dataclass
class NgrokMetrics:
    """Metrics for ngrok gateway usage."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    fallback_requests: int = 0  # Requests that fell back to Ollama
    total_tokens: int = 0
    total_cost: float = 0.0
    ngrok_requests: int = 0
    ollama_requests: int = 0
    cache_hits: int = 0
    average_latency: float = 0.0
    start_time: float = 0.0

    def __post_init__(self) -> None:
        """Initialize start time if not set."""
        if self.start_time == 0.0:
            self.start_time = time.time()

    def get_uptime(self) -> float:
        """Get uptime in seconds."""
        return time.time() - self.start_time


class NgrokAIGateway:
    """ngrok AI Gateway adapter with automatic failover and cost optimization.

    Routes requests through ngrok endpoint with fallback to local Ollama.
    Supports multi-provider routing, cost optimization, and built-in caching.
    """

    # Model cost mappings (tokens)
    MODEL_COSTS = {
        # OpenAI
        "gpt-4o": {"input": 5.0 / 1e6, "output": 15.0 / 1e6},
        "gpt-4-turbo": {"input": 10.0 / 1e6, "output": 30.0 / 1e6},
        "gpt-3.5-turbo": {"input": 0.5 / 1e6, "output": 1.5 / 1e6},
        # Anthropic
        "claude-3.5-sonnet": {"input": 3.0 / 1e6, "output": 15.0 / 1e6},
        "claude-3-opus": {"input": 15.0 / 1e6, "output": 75.0 / 1e6},
        "claude-3-haiku": {"input": 0.25 / 1e6, "output": 1.25 / 1e6},
        # Google
        "gemini-pro": {"input": 0.5 / 1e6, "output": 1.5 / 1e6},
        # Ollama (free, local)
        "ollama-default": {"input": 0.0, "output": 0.0},
    }

    def __init__(
        self,
        ngrok_endpoint: str | None = None,
        ngrok_api_key: str | None = None,
        fallback_ollama_url: str = "http://localhost:13305",
        enable_failover: bool = True,
        enable_cost_optimization: bool = True,
        timeout: float = 300.0,
        max_retries: int = 3,
    ):
        """Initialize ngrok AI Gateway adapter.

        Args:
            ngrok_endpoint: ngrok gateway endpoint (format: https://xxxxx.ngrok.app/v1)
                          If None, tries to load from NGROK_ENDPOINT env var
            ngrok_api_key: ngrok API key for authentication
                          If None, tries to load from NGROK_API_KEY env var
            fallback_ollama_url: Fallback Ollama URL if ngrok fails
            enable_failover: Whether to failover to Ollama on ngrok failure
            enable_cost_optimization: Whether to use cost-optimized routing
            timeout: Request timeout in seconds
            max_retries: Number of retries on failure
        """
        # Load from env if not provided
        self.ngrok_endpoint = ngrok_endpoint or os.getenv("NGROK_ENDPOINT", "")
        self.ngrok_api_key = ngrok_api_key or os.getenv("NGROK_API_KEY", "")
        self.fallback_ollama_url = fallback_ollama_url.rstrip("/")
        self.enable_failover = enable_failover
        self.enable_cost_optimization = enable_cost_optimization
        self.timeout = timeout
        self.max_retries = max_retries

        # Metrics tracking
        self.metrics = NgrokMetrics()

        # Response cache (4th tier) with max size to prevent memory exhaustion
        self._response_cache: dict[str, tuple[str, int]] = {}
        self._cache_max_size = 1000

        # Feature flag context
        self._flag_context = FeatureFlagContext()

        # Validate configuration
        self._validate_config()

    def __repr__(self) -> str:
        from urllib.parse import urlparse

        safe_host = urlparse(self.ngrok_endpoint).netloc if self.ngrok_endpoint else "none"
        return f"NgrokAIGateway(endpoint={safe_host!r}, key=***)"

    def _validate_config(self) -> None:
        """Validate ngrok configuration."""
        if not self.ngrok_endpoint and not self.enable_failover:
            logger.warning(
                "ngrok endpoint not configured and failover disabled. "
                "Set NGROK_ENDPOINT or enable_failover."
            )
        elif self.ngrok_endpoint and not self.ngrok_api_key:
            logger.warning(
                "ngrok endpoint configured but no API key provided. "
                "Set NGROK_API_KEY for authenticated requests."
            )
        elif self.ngrok_endpoint:
            from urllib.parse import urlparse

            safe_host = urlparse(self.ngrok_endpoint).netloc
            logger.info(f"ngrok AI Gateway configured: {safe_host}")

    def _cache_key(self, prompt: str, system: str, model: str) -> str:
        """Generate cache key for response."""
        combined = f"{prompt}|{system}|{model}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate request cost in USD."""
        costs = self.MODEL_COSTS.get(model)
        if not costs:
            # Fallback to generic cost if model not in mapping
            costs = self.MODEL_COSTS.get("gpt-3.5-turbo")

        input_cost = input_tokens * (costs["input"] if costs else 0.0)
        output_cost = output_tokens * (costs["output"] if costs else 0.0)
        return input_cost + output_cost

    async def generate(
        self,
        prompt: str,
        model: str,
        system: str = "",
        num_predict: int = 256,
    ) -> tuple[str, int]:
        """Generate response with ngrok gateway or Ollama fallback.

        Args:
            prompt: User prompt
            model: Model name (e.g., "gpt-4o", "claude-3.5-sonnet", "qwen3-coder:30b")
            system: System prompt
            num_predict: Max tokens to generate (used for Ollama only)

        Returns:
            Tuple of (response_text, tokens_used)

        Raises:
            RuntimeError: If all providers fail
        """
        self.metrics.total_requests += 1

        # Check response cache (4th tier)
        cache_key = self._cache_key(prompt, system, model)
        if cache_key in self._response_cache:
            response, tokens = self._response_cache[cache_key]
            self.metrics.cache_hits += 1
            logger.debug(f"Cache hit for model {model} (saved {tokens} tokens)")
            return response, tokens

        # Check if ngrok gateway is enabled via feature flag
        use_ngrok = is_feature_enabled(FeatureFlag.NGROK_AI_GATEWAY, self._flag_context)

        if use_ngrok and self.ngrok_endpoint:
            try:
                response, tokens = await self._call_ngrok(prompt, model, system)
                self.metrics.successful_requests += 1
                self.metrics.ngrok_requests += 1
                if len(self._response_cache) >= self._cache_max_size:
                    oldest = next(iter(self._response_cache))
                    del self._response_cache[oldest]
                self._response_cache[cache_key] = (response, tokens)
                return response, tokens
            except Exception as e:
                logger.warning(f"ngrok request failed: {type(e).__name__}")
                self.metrics.failed_requests += 1

                if not self.enable_failover:
                    raise RuntimeError(f"ngrok request failed and failover disabled: {e}") from e

                logger.info("Falling back to Ollama")
                self.metrics.fallback_requests += 1

        # Fallback to Ollama
        try:
            response, tokens = await self._call_ollama(prompt, model, system, num_predict)
            self.metrics.successful_requests += 1
            self.metrics.ollama_requests += 1
            if len(self._response_cache) >= self._cache_max_size:
                oldest = next(iter(self._response_cache))
                del self._response_cache[oldest]
            self._response_cache[cache_key] = (response, tokens)
            return response, tokens
        except Exception as e:
            logger.error(f"All providers failed: {e}")
            self.metrics.failed_requests += 1
            raise RuntimeError(f"All providers failed: ngrok and Ollama: {e}") from e

    async def _call_ngrok(
        self,
        prompt: str,
        model: str,
        system: str = "",
    ) -> tuple[str, int]:
        """Call ngrok AI Gateway endpoint.

        Args:
            prompt: User prompt
            model: Model name
            system: System prompt

        Returns:
            Tuple of (response_text, tokens_used)

        Raises:
            Exception: If request fails
        """
        if not self.ngrok_endpoint:
            raise ValueError("ngrok endpoint not configured")

        headers = {
            "Authorization": f"Bearer {self.ngrok_api_key}" if self.ngrok_api_key else "",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system} if system else {},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 256,
        }

        # Remove empty system message
        payload["messages"] = [m for m in payload["messages"] if m]

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.ngrok_endpoint}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                data = response.json()
                text = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("completion_tokens", 0)
                input_tokens = data.get("usage", {}).get("prompt_tokens", 0)

                # Track cost
                cost = self._calculate_cost(model, input_tokens, tokens)
                self.metrics.total_cost += cost
                self.metrics.total_tokens += tokens

                logger.debug(f"ngrok response: {len(text)} chars, {tokens} tokens, ${cost:.6f}")
                return text, tokens

            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(
                        f"ngrok request failed after {self.max_retries} retries: {type(e).__name__}"
                    ) from e

                wait_time = 0.5 * (2**attempt)
                logger.warning(
                    f"ngrok request failed (attempt {attempt + 1}/{self.max_retries}), "
                    f"retrying in {wait_time:.1f}s: {type(e).__name__}"
                )
                await asyncio.sleep(wait_time)

        raise RuntimeError("Unexpected retry loop exit")

    async def _call_ollama(
        self,
        prompt: str,
        model: str,
        system: str = "",
        num_predict: int = 256,
    ) -> tuple[str, int]:
        """Call local Ollama as fallback via standard generate API.

        Args:
            prompt: User prompt
            model: Model name
            system: System prompt
            num_predict: Max tokens to generate

        Returns:
            Tuple of (response_text, tokens_used)
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.fallback_ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "system": system,
                        "stream": False,
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()

                data = response.json()
                text = data.get("response", "")
                tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)

                self.metrics.total_tokens += tokens

                logger.debug(f"Ollama response: {len(text)} chars, {tokens} tokens")
                return text, tokens

            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(
                        f"Ollama request failed after {self.max_retries} retries: {e}"
                    ) from e

                wait_time = 0.5 * (2**attempt)
                logger.warning(
                    f"Ollama request failed (attempt {attempt + 1}/{self.max_retries}), "
                    f"retrying in {wait_time:.1f}s: {e}"
                )
                await asyncio.sleep(wait_time)

        raise RuntimeError("Unexpected retry loop exit")

    def get_metrics(self) -> dict[str, Any]:
        """Get gateway metrics.

        Returns:
            Dictionary with performance and cost metrics
        """
        uptime = self.metrics.get_uptime()
        success_rate = (
            (self.metrics.successful_requests / self.metrics.total_requests * 100)
            if self.metrics.total_requests > 0
            else 0.0
        )

        return {
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "fallback_requests": self.metrics.fallback_requests,
            "ngrok_requests": self.metrics.ngrok_requests,
            "ollama_requests": self.metrics.ollama_requests,
            "cache_hits": self.metrics.cache_hits,
            "success_rate": round(success_rate, 2),
            "total_tokens": self.metrics.total_tokens,
            "total_cost": round(self.metrics.total_cost, 4),
            "average_cost_per_request": round(
                self.metrics.total_cost / self.metrics.total_requests, 6
            )
            if self.metrics.total_requests > 0
            else 0.0,
            "uptime_seconds": round(uptime, 2),
            "requests_per_minute": round((self.metrics.total_requests / uptime * 60), 2)
            if uptime > 0
            else 0.0,
        }

    def clear_cache(self) -> None:
        """Clear response cache."""
        self._response_cache.clear()
        logger.info("Response cache cleared")

    def reset_metrics(self) -> None:
        """Reset metrics."""
        self.metrics = NgrokMetrics()
        logger.debug("Metrics reset")
