# ruff: noqa: RUF012  # class attrs treated as immutable config; never mutated per-instance
"""Demo ngrok AI Gateway - routes to local Ollama models without API keys.

This demonstrates the ngrok AI Gateway architecture using your local Ollama
setup instead of external API providers. Perfect for testing and demo purposes.

Features:
- Multi-model routing (qwen, deepseek, phi3)
- Cost estimation (simulated)
- Metrics tracking
- No API keys required - uses local Ollama

Usage:
    from cohezion.gateway.demo_gateway import DemoGateway

    gateway = DemoGateway(ollama_url="http://localhost:11434")
    response, tokens = await gateway.generate(
        prompt="Hello",
        model="qwen3-coder:30b"
    )
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any

import requests  # type: ignore[import-untyped]


logger = logging.getLogger(__name__)


@dataclass
class DemoMetrics:
    """Metrics for demo gateway."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    cache_hits: int = 0
    start_time: float = 0.0

    def __post_init__(self) -> None:
        if self.start_time == 0.0:
            self.start_time = time.time()

    def get_uptime(self) -> float:
        return time.time() - self.start_time


class DemoGateway:
    """Demo gateway using local Ollama models (no API keys needed)."""

    # Simulated pricing for demo (not real)
    MODEL_COSTS = {
        "qwen3-coder:30b": {"input": 0.001, "output": 0.002},
        "deepseek-r1:70b": {"input": 0.002, "output": 0.004},
        "phi3:mini": {"input": 0.0005, "output": 0.001},
    }

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        timeout: float = 300.0,
        max_retries: int = 3,
    ):
        """Initialize demo gateway.

        Args:
            ollama_url: Local Ollama server URL
            timeout: Request timeout
            max_retries: Retry attempts
        """
        self.ollama_url = ollama_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.metrics = DemoMetrics()
        self._response_cache: dict[str, tuple[str, int]] = {}

        logger.info(f"Demo Gateway initialized (Ollama: {ollama_url})")

    def _cache_key(self, prompt: str, system: str, model: str) -> str:
        """Generate cache key."""
        combined = f"{prompt}|{system}|{model}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate simulated cost."""
        costs = self.MODEL_COSTS.get(model, {"input": 0.001, "output": 0.002})
        input_cost = input_tokens * costs["input"] / 1000
        output_cost = output_tokens * costs["output"] / 1000
        return input_cost + output_cost

    async def generate(
        self,
        prompt: str,
        model: str = "qwen3-coder:30b",
        system: str = "",
    ) -> tuple[str, int]:
        """Generate response via local Ollama.

        Args:
            prompt: User prompt
            model: Model name (qwen3-coder:30b, deepseek-r1:70b, phi3:mini)
            system: System prompt

        Returns:
            Tuple of (response_text, tokens_used)
        """
        self.metrics.total_requests += 1

        # Check cache
        cache_key = self._cache_key(prompt, system, model)
        if cache_key in self._response_cache:
            response, tokens = self._response_cache[cache_key]
            self.metrics.cache_hits += 1
            logger.debug(f"Cache hit for {model} (saved {tokens} tokens)")
            return response, tokens

        # Call Ollama
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "system": system,
                    "stream": False,
                    "num_predict": 256,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            text = data.get("response", "")
            tokens = data.get("eval_count", 0)

            self.metrics.successful_requests += 1
            self.metrics.total_tokens += tokens

            # Cache result
            self._response_cache[cache_key] = (text, tokens)

            logger.debug(f"Generated {len(text)} chars, {tokens} tokens via {model}")
            return text, tokens

        except Exception as e:
            self.metrics.failed_requests += 1
            logger.error(f"Generation failed: {e}")
            raise RuntimeError(f"Ollama request failed: {e}") from e

    def get_metrics(self) -> dict[str, Any]:
        """Get gateway metrics."""
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
            "cache_hits": self.metrics.cache_hits,
            "success_rate": round(success_rate, 2),
            "total_tokens": self.metrics.total_tokens,
            "uptime_seconds": round(uptime, 2),
            "requests_per_minute": round((self.metrics.total_requests / uptime * 60), 2)
            if uptime > 0
            else 0.0,
            "available_models": list(self.MODEL_COSTS.keys()),
            "note": "This is a DEMO gateway - costs are simulated, all requests use local Ollama",
        }

    def get_providers(self) -> dict[str, Any]:
        """Get available models."""
        return {
            "provider": "Local Ollama (Demo)",
            "note": "No API keys required - uses local models",
            "models": [
                {
                    "name": "qwen3-coder:30b",
                    "description": "Fast, good for coding",
                    "simulated_cost": {"input": 0.001, "output": 0.002},
                },
                {
                    "name": "deepseek-r1:70b",
                    "description": "Powerful reasoning model",
                    "simulated_cost": {"input": 0.002, "output": 0.004},
                },
                {
                    "name": "phi3:mini",
                    "description": "Lightweight, fast",
                    "simulated_cost": {"input": 0.0005, "output": 0.001},
                },
            ],
        }

    def cost_estimate(self, model: str, input_tokens: int, output_tokens: int) -> dict[str, Any]:
        """Estimate cost (simulated for demo)."""
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        return {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "simulated_cost_usd": round(cost, 6),
            "note": "This is simulated pricing for demo - actual cost is $0 (local Ollama)",
        }

    def clear_cache(self) -> None:
        """Clear response cache."""
        self._response_cache.clear()
        logger.info("Cache cleared")

    def reset_metrics(self) -> None:
        """Reset metrics."""
        self.metrics = DemoMetrics()
        logger.debug("Metrics reset")
