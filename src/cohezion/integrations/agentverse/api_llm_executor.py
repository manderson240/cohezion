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
    cache_read_tokens: int = 0  # Anthropic: tokens served from cache (0.10× rate)
    cache_write_tokens: int = 0  # Anthropic: tokens written to cache (1.25× rate)


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
            usage = data["usage"]
            tokens_in = usage["input_tokens"]
            tokens_out = usage["output_tokens"]
            cache_read = usage.get("cache_read_input_tokens", 0)
            cache_write = usage.get("cache_write_input_tokens", 0)

            cost = self._calculate_cost_with_cache(tokens_in, tokens_out, cache_read, cache_write)

            elapsed = (time.monotonic() - start_time) * 1000

            return APIResult(
                success=True,
                output=output,
                latency_ms=elapsed,
                tokens_used=tokens_in + tokens_out,
                cost_usd=cost,
                cache_read_tokens=cache_read,
                cache_write_tokens=cache_write,
            )

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate API cost in USD (no cache adjustment)."""
        return self._calculate_cost_with_cache(input_tokens, output_tokens)

    def _calculate_cost_with_cache(
        self,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> float:
        """Calculate Anthropic cost accounting for prompt-cache token rates.

        Anthropic prompt caching rates (GA, all Sonnet/Opus/Haiku models):
          - Normal input:      1.00× base input rate
          - Cache write:       1.25× base input rate (25% premium for storing)
          - Cache read:        0.10× base input rate (90% discount for retrieval)
          - Output:            standard output rate (unchanged)
        """
        provider_costs = self.COSTS.get(self.provider, {})
        model_costs = provider_costs.get(self.model, {"input": 0, "output": 0})
        input_rate = model_costs["input"] / 1_000_000
        output_rate = model_costs["output"] / 1_000_000

        return (
            input_tokens * input_rate
            + cache_write_tokens * input_rate * 1.25
            + cache_read_tokens * input_rate * 0.10
            + output_tokens * output_rate
        )

    async def batch_submit(
        self,
        requests: list[dict[str, Any]],
    ) -> str:
        """Submit a Message Batch to the Anthropic Batches API.

        Use for bulk async work (skill evals, autoresearch sweeps, retro jobs)
        where up to 24h latency is acceptable in exchange for 50% cost savings.

        Args:
            requests: List of dicts with keys:
                custom_id (str): caller-assigned identifier for result matching
                prompt (str): user message
                system (str | None): system prompt (will be cache-controlled)
                max_tokens (int, optional): default 1024
                temperature (float, optional): default 0.7

        Returns:
            batch_id: Anthropic batch identifier to pass to batch_poll().
        """
        if self.provider != "anthropic":
            raise ValueError("batch_submit only supports provider='anthropic'")

        batch_requests = []
        for req in requests:
            params: dict[str, Any] = {
                "model": self.model,
                "max_tokens": req.get("max_tokens", 1024),
                "temperature": req.get("temperature", 0.7),
                "messages": [{"role": "user", "content": req["prompt"]}],
            }
            system = req.get("system")
            if system:
                params["system"] = [
                    {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
                ]
            batch_requests.append({"custom_id": req["custom_id"], "params": params})

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/messages/batches",
                headers=headers,
                json={"requests": batch_requests},
            )
            response.raise_for_status()
            return response.json()["id"]

    async def batch_poll(
        self,
        batch_id: str,
    ) -> list[dict[str, Any]] | None:
        """Poll a Message Batch for completion and return results.

        Returns None if the batch is still processing.
        Returns a list of result dicts (keyed by custom_id) when ended.

        Each result dict has:
            custom_id (str), success (bool), output (str),
            tokens_used (int), cost_usd (float),
            cache_read_tokens (int), cache_write_tokens (int),
            error (str | None)
        """
        if self.provider != "anthropic":
            raise ValueError("batch_poll only supports provider='anthropic'")

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            status_resp = await client.get(
                f"{self.base_url}/messages/batches/{batch_id}",
                headers=headers,
            )
            status_resp.raise_for_status()
            status_data = status_resp.json()

            if status_data["processing_status"] != "ended":
                return None

            results_resp = await client.get(
                f"{self.base_url}/messages/batches/{batch_id}/results",
                headers=headers,
            )
            results_resp.raise_for_status()

        results = []
        for line in results_resp.text.splitlines():
            if not line.strip():
                continue
            import json as _json

            item = _json.loads(line)
            custom_id = item["custom_id"]
            result_type = item["result"]["type"]

            if result_type == "succeeded":
                msg = item["result"]["message"]
                usage = msg.get("usage", {})
                tokens_in = usage.get("input_tokens", 0)
                tokens_out = usage.get("output_tokens", 0)
                cache_read = usage.get("cache_read_input_tokens", 0)
                cache_write = usage.get("cache_write_input_tokens", 0)
                output = msg["content"][0]["text"] if msg.get("content") else ""
                cost = self._calculate_cost_with_cache(
                    tokens_in, tokens_out, cache_read, cache_write
                )
                results.append(
                    {
                        "custom_id": custom_id,
                        "success": True,
                        "output": output,
                        "tokens_used": tokens_in + tokens_out,
                        "cost_usd": cost,
                        "cache_read_tokens": cache_read,
                        "cache_write_tokens": cache_write,
                        "error": None,
                    }
                )
            else:
                error_detail = item["result"].get("error", {}).get("message", result_type)
                results.append(
                    {
                        "custom_id": custom_id,
                        "success": False,
                        "output": "",
                        "tokens_used": 0,
                        "cost_usd": 0.0,
                        "cache_read_tokens": 0,
                        "cache_write_tokens": 0,
                        "error": error_detail,
                    }
                )

        return results

    async def batch_execute(
        self,
        requests: list[dict[str, Any]],
        poll_interval_s: float = 5.0,
        max_wait_s: float = 86_400.0,
    ) -> list[dict[str, Any]]:
        """Submit a batch and poll until complete. Blocking convenience wrapper.

        Submits via batch_submit, then polls with exponential backoff until
        processing_status == 'ended' or max_wait_s is exceeded.

        Args:
            requests: Same format as batch_submit (custom_id, prompt, system, …).
            poll_interval_s: Initial polling interval (doubles each miss, capped at 60s).
            max_wait_s: Maximum total seconds to wait before raising TimeoutError.

        Returns:
            List of result dicts (same format as batch_poll).

        Raises:
            TimeoutError: If batch hasn't finished within max_wait_s.
        """
        import asyncio as _asyncio

        batch_id = await self.batch_submit(requests)
        logger.info("Batch %s submitted (%d requests)", batch_id, len(requests))

        waited = 0.0
        interval = poll_interval_s
        while waited < max_wait_s:
            results = await self.batch_poll(batch_id)
            if results is not None:
                total_cost = sum(r["cost_usd"] for r in results)
                cache_read = sum(r["cache_read_tokens"] for r in results)
                logger.info(
                    "Batch %s done: %d/%d succeeded, cost=$%.6f, cache_read=%d tokens",
                    batch_id,
                    sum(1 for r in results if r["success"]),
                    len(results),
                    total_cost,
                    cache_read,
                )
                return results
            await _asyncio.sleep(interval)
            waited += interval
            interval = min(interval * 2.0, 60.0)

        raise TimeoutError(f"Batch {batch_id} did not complete within {max_wait_s:.0f}s")


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

    async def batch_execute(
        self,
        requests: list[dict[str, Any]],
        poll_interval_s: float = 5.0,
        max_wait_s: float = 86_400.0,
    ) -> list[APIResult]:
        """Execute multiple independent prompts as a batch.

        When the underlying API executor is Anthropic, routes through
        batch_submit / batch_poll for 50% cost savings. Falls back to
        asyncio.gather of individual execute() calls for all other providers.

        Args:
            requests: List of dicts with keys: custom_id, prompt, system (opt),
                      max_tokens (opt), temperature (opt).
            poll_interval_s: Batch API polling interval (Anthropic path only).
            max_wait_s: Max wait for batch completion (Anthropic path only).

        Returns:
            List of APIResult in the same order as requests.
        """
        import asyncio as _asyncio

        if self.api.provider == "anthropic":
            raw = await self.api.batch_execute(requests, poll_interval_s, max_wait_s)
            # Re-order to match input order and convert to APIResult
            id_to_raw = {r["custom_id"]: r for r in raw}
            results = []
            for req in requests:
                r = id_to_raw.get(req["custom_id"])
                if r is None:
                    results.append(
                        APIResult(
                            success=False,
                            output="",
                            latency_ms=0,
                            tokens_used=0,
                            cost_usd=0,
                            error="missing from batch response",
                        )
                    )
                else:
                    results.append(
                        APIResult(
                            success=r["success"],
                            output=r["output"],
                            latency_ms=0,
                            tokens_used=r["tokens_used"],
                            cost_usd=r["cost_usd"],
                            error=r["error"],
                            cache_read_tokens=r["cache_read_tokens"],
                            cache_write_tokens=r["cache_write_tokens"],
                        )
                    )
            return results

        # Non-Anthropic: fire in parallel
        coros = [
            self.execute(
                req["prompt"],
                req.get("system"),
                req.get("max_tokens", 1024),
                req.get("temperature", 0.7),
            )
            for req in requests
        ]
        return list(await _asyncio.gather(*coros))


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
