"""API-based LLM Executor - OpenAI/Anthropic fallback for Ollama timeouts.

Uses cloud APIs (OpenAI, Anthropic, or other) when Ollama is unavailable
or timing out. Configurable with environment variables.

Usage:
    executor = APILLMExecutor(provider="openai", model="gpt-4o-mini")
    result = await executor.execute_task(task, skill="coding")

Environment:
    OPENAI_API_KEY - Required for OpenAI
    ANTHROPIC_API_KEY - Required for Anthropic
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx


logger = logging.getLogger(__name__)


@dataclass
class APIResult:
    """Result from API LLM execution."""

    success: bool
    output: str
    latency_ms: float
    tokens_used: int
    cost_usd: float  # Estimated cost
    error: str | None = None


class APILLMExecutor:
    """Execute tasks via cloud LLM APIs.

    Supported providers:
    - openai: GPT-4, GPT-4o, GPT-3.5-turbo
    - anthropic: Claude Sonnet 4.6, Claude Opus 4.6

    Args:
        provider: "openai" or "anthropic"
        model: Model name (e.g., "gpt-4o-mini", "claude-sonnet-4-6")
        timeout: Request timeout in seconds
    """

    # Cost per 1M tokens (approximate, check current pricing)
    COSTS = {
        "openai": {
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        },
        "anthropic": {
            "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
            "claude-opus-4-6": {"input": 15.00, "output": 75.00},
        },
    }

    def __init__(
        self,
        provider: str = "openai",
        model: str | None = None,
        timeout: float = 60.0,
    ):
        self.provider = provider.lower()
        self.timeout = timeout

        # Set default models
        if model is None:
            if self.provider == "openai":
                self.model = "gpt-4o-mini"  # Cost-effective
            elif self.provider == "anthropic":
                self.model = "claude-sonnet-4-6"
            else:
                raise ValueError(f"Unknown provider: {provider}")
        else:
            self.model = model

        # Get API key
        if self.provider == "openai":
            self.api_key = os.environ.get("OPENAI_API_KEY")
            self.base_url = "https://api.openai.com/v1"
        elif self.provider == "anthropic":
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
            self.base_url = "https://api.anthropic.com/v1"
        else:
            raise ValueError(f"Unknown provider: {provider}")

        if not self.api_key:
            logger.warning("No API key configured for %s — calls will fail", provider)

    async def execute(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> APIResult:
        """Execute single LLM call via API.

        Args:
            prompt: User prompt
            system: System message (optional)
            max_tokens: Max tokens to generate
            temperature: Sampling temperature

        Returns:
            APIResult with output and metadata
        """
        import time

        start_time = time.monotonic()

        try:
            if self.provider == "openai":
                return await self._execute_openai(prompt, system, max_tokens, temperature)
            elif self.provider == "anthropic":
                return await self._execute_anthropic(prompt, system, max_tokens, temperature)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")

        except Exception as e:
            elapsed = (time.monotonic() - start_time) * 1000
            logger.error(f"API execution failed: {e}")
            return APIResult(
                success=False,
                output="",
                latency_ms=elapsed,
                tokens_used=0,
                cost_usd=0.0,
                error=str(e),
            )

    async def _execute_openai(
        self,
        prompt: str,
        system: str | None,
        max_tokens: int,
        temperature: float,
    ) -> APIResult:
        """Execute via OpenAI API."""
        import time

        start_time = time.monotonic()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

            response.raise_for_status()
            data = response.json()

            output = data["choices"][0]["message"]["content"]
            tokens_in = data["usage"]["prompt_tokens"]
            tokens_out = data["usage"]["completion_tokens"]

            # Calculate cost
            cost = self._calculate_cost(tokens_in, tokens_out)

            elapsed = (time.monotonic() - start_time) * 1000

            return APIResult(
                success=True,
                output=output,
                latency_ms=elapsed,
                tokens_used=tokens_in + tokens_out,
                cost_usd=cost,
            )

    async def _execute_anthropic(
        self,
        prompt: str,
        system: str | None,
        max_tokens: int,
        temperature: float,
    ) -> APIResult:
        """Execute via Anthropic API."""
        import time

        start_time = time.monotonic()

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system:
            payload["system"] = [
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload,
            )

            response.raise_for_status()
            data = response.json()

            output = data["content"][0]["text"]
            tokens_in = data["usage"]["input_tokens"]
            tokens_out = data["usage"]["output_tokens"]

            cost = self._calculate_cost(tokens_in, tokens_out)

            elapsed = (time.monotonic() - start_time) * 1000

            return APIResult(
                success=True,
                output=output,
                latency_ms=elapsed,
                tokens_used=tokens_in + tokens_out,
                cost_usd=cost,
            )

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate API cost in USD."""
        provider_costs = self.COSTS.get(self.provider, {})
        model_costs = provider_costs.get(self.model, {"input": 0, "output": 0})

        input_cost = (input_tokens / 1_000_000) * model_costs["input"]
        output_cost = (output_tokens / 1_000_000) * model_costs["output"]

        return input_cost + output_cost


class HybridExecutor:
    """Hybrid executor - tries Ollama first, falls back to API."""

    def __init__(
        self,
        ollama_executor: Any | None = None,
        api_executor: APILLMExecutor | None = None,
    ):
        self.ollama = ollama_executor
        self.api = api_executor or APILLMExecutor()

    async def execute(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        prefer_api: bool = False,
    ) -> APIResult:
        """Execute with fallback.

        Args:
            prompt: User prompt
            prefer_api: Use API even if Ollama available (for reliability)

        Returns:
            APIResult from whichever executor succeeded
        """
        if prefer_api or self.ollama is None:
            # Use API first or exclusively
            return await self.api.execute(prompt, system, max_tokens, temperature)

        # Try Ollama first
        try:
            # Import here to avoid circular dependency
            from cohezion.integrations.agentverse.llm_executor import LLMExecutor

            if isinstance(self.ollama, LLMExecutor):
                result = await self.ollama.execute_task(
                    task={"description": prompt, "skill": "general"},
                )
                return APIResult(
                    success=True,
                    output=result.output if hasattr(result, "output") else str(result),
                    latency_ms=1000,
                    tokens_used=0,
                    cost_usd=0.0,
                )
        except Exception as e:
            logger.warning(f"Ollama failed, falling back to API: {e}")

        # Fallback to API
        return await self.api.execute(prompt, system, max_tokens, temperature)


async def main():
    """Test the API executor."""

    # Check for API key
    if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
        return 1

    # Test execution
    executor = APILLMExecutor()
    result = await executor.execute(
        "Write a Python function to reverse a string.",
        max_tokens=256,
    )

    print(f"Success: {result.success}")
    print(f"Latency: {result.latency_ms:.1f}ms")
    print(f"Tokens: {result.tokens_used}")
    print(f"Cost: ${result.cost_usd:.6f}")
    print(f"\nOutput:\n{result.output}")

    return 0 if result.success else 1


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
