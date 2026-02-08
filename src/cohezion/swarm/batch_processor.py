"""Token-efficient batch processing for compound execution.

Implements Phase 1 (cache lookup) + Phase 2 (parallel execution) pattern:
  Phase 1: Check all items in cache, return hits immediately
  Phase 2: Execute cache misses in parallel with controlled concurrency

This maximizes cache benefit and minimizes latency for long-running inferences.
"""

import asyncio
import hashlib
import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from cohezion.core.config import CohezionConfig


logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cached result."""

    key: str
    value: Any
    tokens_used: int


@dataclass
class BatchItem:
    """Single item in a batch."""

    id: str
    prompt: str
    system: str
    model: str
    cache_entry: CacheEntry | None = None
    result: str | None = None
    tokens_used: int = 0
    error: str | None = None
    cached: bool = False


@dataclass
class BatchResult:
    """Result of batch processing."""

    items: list[BatchItem]
    total_tokens: int
    cache_hits: int
    cache_misses: int
    total_duration_ms: float
    parallel_executions: int

    @property
    def cache_hit_rate(self) -> float:
        """Percentage of cache hits."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    @property
    def tokens_saved(self) -> int:
        """Tokens saved from caching."""
        return sum(item.cache_entry.tokens_used for item in self.items
                   if item.cached and item.cache_entry)


class BatchProcessor:
    """Process multiple LLM requests efficiently with caching and parallelism.

    Two-phase approach:
      Phase 1: Cache lookup (zero cost)
      Phase 2: Parallel execution of cache misses (controlled concurrency)
    """

    def __init__(
        self,
        token_client: Any,
        config: CohezionConfig | None = None,
        cache: dict[str, CacheEntry] | None = None,
    ):
        """Initialize batch processor.

        Args:
            token_client: TokenEfficientClient instance
            config: CohezionConfig with batch settings
            cache: Pre-populated cache dictionary
        """
        self.token_client = token_client
        self.config = config or CohezionConfig()
        self.cache = cache or {}
        self._concurrency_semaphore = asyncio.Semaphore(
            self.config.batch.parallel_tasks
        )

    def _cache_key(self, prompt: str, system: str, model: str) -> str:
        """Generate cache key."""
        combined = f"{prompt}|{system}|{model}"
        return hashlib.sha256(combined.encode()).hexdigest()

    async def process_batch(
        self,
        items: list[BatchItem],
        execute_fn: Callable[[BatchItem], Coroutine[Any, Any, tuple[str, int]]],
    ) -> BatchResult:
        """Process batch with Phase 1 cache + Phase 2 parallel execution.

        Args:
            items: List of items to process
            execute_fn: Async function that executes single item,
                returns (output, tokens)

        Returns:
            BatchResult with results, metrics, and cache statistics
        """
        import time
        start_time = time.time()

        # Phase 1: Cache Lookup (O(n) but zero latency)
        logger.info("Phase 1: Checking cache for %d items", len(items))
        cache_hits = 0
        cache_misses_list = []

        for item in items:
            key = self._cache_key(item.prompt, item.system, item.model)
            if key in self.cache:
                entry = self.cache[key]
                item.cache_entry = entry
                item.result = entry.value
                item.tokens_used = entry.tokens_used
                item.cached = True
                cache_hits += 1
                logger.debug("Cache hit: %s", item.id)
            else:
                cache_misses_list.append((item, key))
                cache_hits += 1 if item not in items else 0

        cache_misses = len(cache_misses_list)
        logger.info(
            "Phase 1 complete: %d hits, %d misses (%.1f%% hit rate)",
            cache_hits,
            cache_misses,
            100.0 * cache_hits / len(items) if items else 0,
        )

        # Phase 2: Parallel Execution of Cache Misses (controlled concurrency)
        if cache_misses > 0:
            logger.info(
                "Phase 2: Executing %d cache misses in parallel (concurrency=%d)",
                cache_misses,
                self.config.batch.parallel_tasks,
            )

            tasks = [
                self._execute_with_concurrency(item, key, execute_fn)
                for item, key in cache_misses_list
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for (item, key), result in zip(cache_misses_list, results, strict=False):
                if isinstance(result, BaseException):
                    item.error = str(result)
                    item.tokens_used = 0
                    logger.error("Execution failed for %s: %s", item.id, result)
                else:
                    output, tokens = result
                    item.result = output
                    item.tokens_used = tokens

                    # Cache the result
                    self.cache[key] = CacheEntry(
                        key=key,
                        value=output,
                        tokens_used=tokens,
                    )

        elapsed_ms = (time.time() - start_time) * 1000.0

        return BatchResult(
            items=items,
            total_tokens=sum(item.tokens_used for item in items),
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            total_duration_ms=round(elapsed_ms, 2),
            parallel_executions=min(cache_misses, self.config.batch.parallel_tasks),
        )

    async def _execute_with_concurrency(
        self,
        item: BatchItem,
        key: str,
        execute_fn: Callable[[BatchItem], Coroutine[Any, Any, tuple[str, int]]],
    ) -> tuple[str, int]:
        """Execute with semaphore-controlled concurrency."""
        async with self._concurrency_semaphore:
            logger.debug(
                "Executing %s (model=%s, semaphore_count=%d)",
                item.id,
                item.model,
                self._concurrency_semaphore._value,
            )
            return await execute_fn(item)

    def clear_cache(self) -> None:
        """Clear the cache."""
        self.cache.clear()
        logger.info("Cache cleared")

    def cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self.cache),
            "max_cache_size": self.config.cache.max_size,
            "cache_enabled": self.config.cache.enabled,
            "parallel_tasks": self.config.batch.parallel_tasks,
        }
