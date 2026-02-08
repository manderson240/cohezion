"""Token-efficient Ollama client with SHA-256 caching and batch processing.

Combines:
- SHA-256 hash-based prompt caching (eliminates redundant API calls)
- Phase 1 + Phase 2 batch processing (cache hits + parallel execution)
- Per-operation model routing (via AdaptiveRouterAdapter)
- Token tracking and metrics

Usage::

    # Single request (cached)
    client = TokenEfficientClient(
        ollama_base_url="http://localhost:11434",
        router=AdaptiveRouterAdapter(selector),
        config=CohezionConfig()
    )
    response, tokens = await client.generate(
        prompt="Explain quantum computing",
        model="qwen3-coder:30b"
    )

    # Batch request (Phase 1 cache + Phase 2 parallel)
    items = [
        BatchItem(id="1", prompt="Task 1", system="sys", model="qwen"),
        BatchItem(id="2", prompt="Task 2", system="sys", model="phi3"),
    ]
    result = await client.batch_generate(items)
    print(f"Cache hits: {result.cache_hits}, Tokens: {result.total_tokens}")
"""

import asyncio
import hashlib
import logging
import time
from typing import Any

import requests

from cohezion.core.config import CohezionConfig
from cohezion.swarm.batch_processor import BatchItem, BatchProcessor, BatchResult


logger = logging.getLogger(__name__)


class ResilientOllamaClient:
    """Wrapper around Ollama API with retry logic and error handling.

    Handles:
    - Connection retries with exponential backoff
    - Timeout management
    - Response validation
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: float = 300.0,
        max_retries: int = 3,
    ):
        """Initialize Ollama client.

        Args:
            base_url: Ollama API base URL
            timeout: Request timeout in seconds
            max_retries: Number of retries on failure
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    async def generate(
        self,
        prompt: str,
        model: str,
        system: str = "",
        num_predict: int = 256,
    ) -> tuple[str, int]:
        """Generate response from Ollama.

        Args:
            prompt: User prompt
            model: Model name (e.g., "qwen3-coder:30b")
            system: System prompt
            num_predict: Max tokens to generate

        Returns:
            Tuple of (response_text, tokens_used)

        Raises:
            RuntimeError: If all retries fail
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "system": system,
                        "stream": False,
                        "num_predict": num_predict,
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()

                data = response.json()
                return data.get("response", ""), data.get("eval_count", 0)

            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(
                        f"Ollama request failed after {self.max_retries} retries: {e}"
                    ) from e

                wait_time = 0.5 * (2 ** attempt)
                logger.warning(
                    "Ollama request failed (attempt %d/%d), retrying in %.1f seconds: %s",
                    attempt + 1,
                    self.max_retries,
                    wait_time,
                    e,
                )
                await asyncio.sleep(wait_time)

        raise RuntimeError("Unexpected retry loop exit")


class TokenEfficientClient:
    """Token-efficient Ollama client with caching and batch processing.

    Two-layer optimization:
      Layer 1: Cache (SHA-256 hash) - Eliminates redundant API calls
      Layer 2: Batch (Phase 1 cache lookup + Phase 2 parallel) - Maximizes throughput

    Example usage::

        client = TokenEfficientClient(config=CohezionConfig())
        response, tokens = await client.generate(
            prompt="Explain quantum computing",
            model="qwen3-coder:30b"
        )
    """

    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        router: Any = None,
        config: CohezionConfig | None = None,
    ):
        """Initialize token-efficient client.

        Args:
            ollama_base_url: Ollama API base URL
            router: Model router (e.g., AdaptiveRouterAdapter) for routing decisions
            config: CohezionConfig with cache, batch, inference settings
        """
        self.ollama = ResilientOllamaClient(base_url=ollama_base_url)
        self.router = router
        self.config = config or CohezionConfig()
        self.batch_processor = BatchProcessor(self, self.config)

        # Metrics
        self._total_tokens = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._api_calls = 0
        self._start_time = time.time()

    async def generate(
        self,
        prompt: str,
        model: str = "phi3:mini",
        system: str = "",
    ) -> tuple[str, int]:
        """Generate response with caching.

        Args:
            prompt: User prompt
            model: Model name
            system: System prompt

        Returns:
            Tuple of (response_text, tokens_used)
        """
        # Check cache
        cache_key = self._cache_key(prompt, system, model)
        if cache_key in self.batch_processor.cache:
            entry = self.batch_processor.cache[cache_key]
            self._cache_hits += 1
            logger.debug("Cache hit for prompt (saved %d tokens)", entry.tokens_used)
            return entry.value, entry.tokens_used

        # Cache miss - call Ollama
        self._cache_misses += 1
        self._api_calls += 1

        num_predict = self.config.inference.num_predict_default
        response, tokens = await self.ollama.generate(
            prompt=prompt,
            model=model,
            system=system,
            num_predict=num_predict,
        )

        self._total_tokens += tokens

        # Cache result
        from cohezion.swarm.batch_processor import CacheEntry

        self.batch_processor.cache[cache_key] = CacheEntry(
            key=cache_key,
            value=response,
            tokens_used=tokens,
        )

        return response, tokens

    async def batch_generate(
        self,
        items: list[BatchItem],
    ) -> BatchResult:
        """Process batch of requests with Phase 1 cache + Phase 2 parallel.

        Phase 1: Check all items in cache (O(n), zero latency)
        Phase 2: Execute cache misses in parallel with concurrency control

        Args:
            items: List of BatchItem to process

        Returns:
            BatchResult with results, metrics, cache statistics
        """
        async def execute_item(item: BatchItem) -> tuple[str, int]:
            """Execute single item (used by Phase 2)."""
            return await self.generate(
                prompt=item.prompt,
                model=item.model,
                system=item.system,
            )

        # Run Phase 1 + Phase 2 batch processing
        result = await self.batch_processor.process_batch(items, execute_item)

        # Note: Metrics (_total_tokens, _cache_hits, _cache_misses, _api_calls)
        # are already updated in generate() calls via execute_item.
        # No additional updates needed here.

        return result

    def _cache_key(self, prompt: str, system: str, model: str) -> str:
        """Generate SHA-256 cache key."""
        combined = f"{prompt}|{system}|{model}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def get_metrics(self) -> dict[str, Any]:
        """Get token efficiency metrics.

        Returns:
            Dict with cache_hit_rate, total_tokens, api_calls, elapsed_seconds, etc.
        """
        elapsed = time.time() - self._start_time
        total_ops = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_ops if total_ops > 0 else 0.0

        # Estimate tokens saved (assume cache hits save ~150 tokens each)
        estimated_tokens_saved = self._cache_hits * self.config.cache.cache_hit_value

        return {
            "cache_hit_rate": hit_rate,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "total_operations": total_ops,
            "total_tokens": self._total_tokens,
            "api_calls": self._api_calls,
            "estimated_tokens_saved": estimated_tokens_saved,
            "elapsed_seconds": round(elapsed, 2),
            "tokens_per_second": round(self._total_tokens / elapsed, 2)
            if elapsed > 0
            else 0.0,
        }

    def clear_cache(self) -> None:
        """Clear the token cache."""
        self.batch_processor.clear_cache()
        logger.info("Token cache cleared")

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self._total_tokens = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._api_calls = 0
        self._start_time = time.time()
        logger.debug("Metrics reset")
