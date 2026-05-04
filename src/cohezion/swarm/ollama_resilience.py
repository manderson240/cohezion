"""Resilient Ollama client with circuit breaker, retry, and fallback.

Wraps Ollama HTTP API calls with:
- Circuit breaker protection (CLOSED/OPEN/HALF_OPEN)
- Resource monitor capacity gating
- Configurable retry with exponential backoff
- Graceful fallback for degraded operation
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from cohezion.reliability import get_circuit
from cohezion.reliability.monitor import get_resource_monitor


logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:11434"
_DEFAULT_TIMEOUT = 120.0


class ResilientOllamaClient:
    """Ollama client with circuit breaker, retry, and fallback.

    Parameters
    ----------
    model : str
        Default Ollama model name.
    base_url : str
        Ollama API base URL.
    failure_threshold : int
        Number of failures before circuit opens.
    recovery_timeout : float
        Seconds before attempting recovery.
    max_retries : int
        Maximum retry attempts per call.
    """

    def __init__(
        self,
        model: str = "phi3:mini",
        base_url: str = _DEFAULT_BASE_URL,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.max_retries = max_retries
        self.circuit = get_circuit(
            "ollama",
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
        self.monitor = get_resource_monitor()
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-initialize the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=_DEFAULT_TIMEOUT,
            )
        return self._client

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        num_predict: int = 2048,
        **kwargs: Any,
    ) -> str:
        """Generate a response with circuit breaker protection.

        Parameters
        ----------
        prompt : str
            The prompt to send.
        model : str | None
            Override the default model.
        system : str | None
            System prompt.
        temperature : float
            Sampling temperature.
        num_predict : int
            Maximum tokens to generate.

        Returns
        -------
        str
            Generated text response.

        Raises
        ------
        RuntimeError
            If circuit is open and fallback is not available.
        httpx.HTTPError
            If all retries are exhausted.
        """
        if not self.circuit.allow_request():
            logger.warning("Circuit breaker OPEN for Ollama — using fallback")
            return self._fallback(prompt)

        await self.monitor.wait_for_capacity()
        try:
            result = await self._call_with_retry(
                prompt=prompt,
                model=model or self.model,
                system=system,
                temperature=temperature,
                num_predict=num_predict,
                **kwargs,
            )
            self.circuit.record_success()
            return result
        except Exception as exc:
            self.circuit.record_failure()
            logger.error("Ollama call failed: %s", exc)
            raise
        finally:
            self.monitor.release_capacity()

    async def _call_with_retry(
        self,
        prompt: str,
        model: str,
        system: str | None,
        temperature: float,
        num_predict: int,
        **kwargs: Any,
    ) -> str:
        """Call Ollama with exponential backoff retry."""
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
            },
        }
        if system:
            payload["system"] = system
        payload.update(kwargs)

        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = await self.client.post("/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "")
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    delay = 2**attempt
                    logger.warning(
                        "Ollama attempt %d/%d failed (%s), retrying in %ds",
                        attempt + 1,
                        self.max_retries + 1,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)

        raise last_exc  # type: ignore[misc]

    @staticmethod
    def _fallback(prompt: str) -> str:
        """Provide a degraded response when the circuit is open."""
        return f"[Ollama unavailable — circuit breaker open] Cannot process: {prompt[:100]}..."

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
