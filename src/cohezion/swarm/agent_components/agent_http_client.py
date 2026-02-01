"""Agent HTTP Client - HTTP connection management with retry logic."""

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class HTTPClientConfig:
    """Configuration for HTTP client."""

    base_url: str = "http://localhost:11434"
    timeout: float = 300.0
    connect_timeout: float = 10.0
    max_retries: int = 3
    retry_backoff_base: float = 1.0


class AgentHTTPClient:
    """Async HTTP client with retry logic for agent model calls."""

    def __init__(self, config: HTTPClientConfig | None = None):
        """Initialize HTTP client with configuration.

        Args:
            config: HTTP client configuration. Uses defaults if not provided.
        """
        self.config = config or HTTPClientConfig()
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-initialize the HTTP client.

        Returns:
            Async HTTP client instance.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(
                    self.config.timeout, connect=self.config.connect_timeout
                ),
            )
            logger.debug(f"HTTP client initialized: {self.config.base_url}")
        return self._client

    async def post(self, endpoint: str, payload: dict, timeout: int = 30) -> dict:
        """POST request with exponential backoff retry logic.

        Args:
            endpoint: API endpoint path (e.g., "/api/generate").
            payload: Request payload as dictionary.
            timeout: Override timeout in seconds for this request.

        Returns:
            JSON response as dictionary.

        Raises:
            httpx.HTTPStatusError: If all retries fail with HTTP error.
            httpx.RequestError: If all retries fail with network error.
        """
        last_exception = None

        for attempt in range(self.config.max_retries):
            try:
                timeout_override = httpx.Timeout(
                    timeout, connect=self.config.connect_timeout
                )
                response = await self.client.post(
                    endpoint, json=payload, timeout=timeout_override
                )
                response.raise_for_status()

                logger.debug(f"POST {endpoint} succeeded on attempt {attempt + 1}")
                return response.json()

            except httpx.HTTPStatusError as e:
                last_exception = e
                logger.warning(
                    f"HTTP error on attempt {attempt + 1}/{self.config.max_retries}: {e.response.status_code}"
                )
                if attempt < self.config.max_retries - 1:
                    await self._backoff(attempt)

            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_exception = e
                logger.warning(
                    f"Request error on attempt {attempt + 1}/{self.config.max_retries}: {type(e).__name__}"
                )
                if attempt < self.config.max_retries - 1:
                    await self._backoff(attempt)

        raise last_exception

    async def _backoff(self, attempt: int) -> None:
        """Calculate and apply exponential backoff delay.

        Args:
            attempt: Current attempt number (0-indexed).
        """
        delay = self.config.retry_backoff_base * (2**attempt)
        logger.debug(f"Backing off for {delay:.1f}s before retry")
        await asyncio.sleep(delay)

    async def close(self) -> None:
        """Close the HTTP client connection.

        Safe to call multiple times.
        """
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("HTTP client closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


import asyncio
