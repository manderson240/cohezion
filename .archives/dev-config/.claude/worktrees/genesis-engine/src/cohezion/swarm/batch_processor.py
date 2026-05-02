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
from cohezion.swarm.dynamic_concurrency_gate import get_concurrency_gate


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
    semantic_confidence: float | None = None  # Confidence from L2 semantic cache hit


@dataclass
class BatchResult:
    """Result of batch processing."""

    items: list[BatchItem]
    total_tokens: int
    cache_hits: int
    cache_misses: int
    total_duration_ms: float
    parallel_executions: int
    semantic_hits: int = 0  # L2 semantic cache hits

    @property
    def cache_hit_rate(self) -> float:
        """Percentage of cache hits (L1 + L2)."""
        total = self.cache_hits + self.semantic_hits + self.cache_misses
        return (self.cache_hits + self.semantic_hits) / total if total > 0 else 0.0

    @property
    def tokens_saved(self) -> int:
        """Tokens saved from caching."""
        return sum(item.cache_entry.tokens_used for item in self.items if item.cached and item.cache_entry)

    @property
    def avg_semantic_confidence(self) -> float:
        """Average confidence of semantic cache hits."""
        confidences = [item.semantic_confidence for item in self.items if item.semantic_confidence is not None]
        return sum(confidences) / len(confidences) if confidences else 0.0


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
        # Phase 1: Use dynamic concurrency gate instead of hardcoded limit
        self.concurrency_gate = get_concurrency_gate()
        # Initialize with default concurrency (will be updated dynamically in process_batch)
        initial_concurrency = self.config.batch.parallel_tasks
        self._concurrency_semaphore = asyncio.Semaphore(initial_concurrency)

    def _cache_key(self, prompt: str, system: str, model: str) -> str:
        """Generate cache key."""
        combined = f"{prompt}|{system}|{model}"
        return hashlib.sha256(combined.encode()).hexdigest()

    async def process_batch(
        self,
        items: list[BatchItem],
        execute_fn: Callable[[BatchItem], Coroutine[Any, Any, tuple[str, int]]],
    ) -> BatchResult:
        """Process batch with Phase 1 cache + Phase 1.5 semantic + Phase 2 parallel execution.

        Phase 1: Cache Lookup (exact hash matches)
        Phase 1.5: Semantic cache lookup (fuzzy matching) for L1 misses
        Phase 1.6: Deduplicate identical prompts within remaining cache misses
        Phase 2: Parallel Execution of unique cache misses (controlled concurrency)
        Phase 2.5: Replicate results to all duplicate prompts

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
        logger.info("Phase 1: Checking L1 exact cache for %d items", len(items))
        cache_hits = 0
        semantic_hits = 0
        cache_misses_list = []
        actual_concurrency = self.config.batch.parallel_tasks  # Default

        for item in items:
            key = self._cache_key(item.prompt, item.system, item.model)
            if key in self.cache:
                entry = self.cache[key]
                item.cache_entry = entry
                item.result = entry.value
                item.tokens_used = entry.tokens_used
                item.cached = True
                cache_hits += 1
                logger.debug("L1 cache hit: %s", item.id)
            else:
                cache_misses_list.append((item, key))

        cache_misses = len(cache_misses_list)
        logger.info(
            "Phase 1 complete: %d L1 hits, %d misses (%.1f%% hit rate)",
            cache_hits,
            cache_misses,
            100.0 * cache_hits / len(items) if items else 0,
        )

        # Phase 1.5: Semantic cache lookup (L2 fuzzy matching) for remaining misses
        if cache_misses > 0 and hasattr(self.token_client, "semantic_cache") and self.token_client.semantic_cache:
            logger.info("Phase 1.5: Checking L2 semantic cache for %d misses", cache_misses)
            remaining_misses = []

            for item, key in cache_misses_list:
                try:
                    semantic_hit = await self.token_client.semantic_cache.get(item.prompt, item.system)
                    if semantic_hit:
                        item.cache_entry = CacheEntry(
                            key=key,
                            value=semantic_hit.value,
                            tokens_used=0,
                        )
                        item.result = semantic_hit.value
                        item.tokens_used = 0
                        item.cached = True
                        item.semantic_confidence = semantic_hit.confidence
                        semantic_hits += 1
                        logger.debug(
                            "L2 semantic cache hit: %s (confidence=%.3f)",
                            item.id,
                            semantic_hit.confidence,
                        )
                    else:
                        remaining_misses.append((item, key))
                except Exception as e:
                    logger.debug(f"L2 semantic cache lookup failed for {item.id}, continuing: {e}")
                    remaining_misses.append((item, key))

            cache_misses_list = remaining_misses
            cache_misses = len(cache_misses_list)
            if semantic_hits > 0:
                logger.info(
                    "Phase 1.5 complete: %d L2 semantic hits, %d remaining misses",
                    semantic_hits,
                    cache_misses,
                )

        # Phase 1.6: Deduplicate identical prompts within cache misses (Phase 2.4)
        if cache_misses > 0:
            unique_misses, duplicate_map = self._deduplicate_misses(cache_misses_list)
            dedup_savings = cache_misses - len(unique_misses)
            if dedup_savings > 0:
                logger.info(
                    "Phase 1.5: Batch deduplication found %d duplicate prompts (%.1f%% savings)",
                    dedup_savings,
                    100.0 * dedup_savings / cache_misses,
                )
            else:
                unique_misses = cache_misses_list
                duplicate_map = {}

        # Phase 2: Parallel Execution of unique cache misses (controlled concurrency)
        if cache_misses > 0 and unique_misses:
            # Get dynamic concurrency based on hardware state
            actual_concurrency = self.concurrency_gate.get_safe_concurrency()
            logger.info(
                "Phase 2: Executing %d unique cache misses in parallel (dynamic concurrency=%d)",
                len(unique_misses),
                actual_concurrency,
            )

            # Create fresh semaphore with dynamic concurrency level
            self._concurrency_semaphore = asyncio.Semaphore(actual_concurrency)

            tasks = [self._execute_with_concurrency(item, key, execute_fn) for item, key in unique_misses]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Phase 2.5: Replicate results to all duplicates
            for (representative_item, key), result in zip(unique_misses, results, strict=False):
                if isinstance(result, BaseException):
                    representative_item.error = str(result)
                    representative_item.tokens_used = 0
                    logger.error("Execution failed for %s: %s", representative_item.id, result)
                else:
                    output, tokens = result
                    representative_item.result = output
                    representative_item.tokens_used = tokens

                    # Cache the result
                    self.cache[key] = CacheEntry(
                        key=key,
                        value=output,
                        tokens_used=tokens,
                    )

                # Replicate to duplicate items
                if key in duplicate_map:
                    for dup_item, _ in duplicate_map[key]:
                        dup_item.result = representative_item.result
                        dup_item.tokens_used = representative_item.tokens_used
                        dup_item.error = representative_item.error
                        dup_item.cached = not bool(representative_item.error)
                        logger.debug("Replicated result to duplicate: %s", dup_item.id)

        elapsed_ms = (time.time() - start_time) * 1000.0

        return BatchResult(
            items=items,
            total_tokens=sum(item.tokens_used for item in items),
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            total_duration_ms=round(elapsed_ms, 2),
            parallel_executions=min(len(unique_misses) if cache_misses > 0 else 0, actual_concurrency),
            semantic_hits=semantic_hits,
        )

    def _deduplicate_misses(
        self, cache_misses_list: list[tuple[BatchItem, str]]
    ) -> tuple[list[tuple[BatchItem, str]], dict[str, list[tuple[BatchItem, str]]]]:
        """Deduplicate identical prompts within cache misses.

        Phase 2.4 optimization: identifies and deduplicates cache misses.
        Returns unique misses and a map of duplicates for later replication.

        Args:
            cache_misses_list: List of (item, key) tuples for cache misses

        Returns:
            Tuple of (unique_misses, duplicate_map)
            - unique_misses: List of (item, key) for unique prompts
            - duplicate_map: Dict mapping representative_key → [(dup_item, dup_key), ...]
        """
        # Map from prompt signature to list of (item, key) tuples
        prompt_groups: dict[str, list[tuple[BatchItem, str]]] = {}

        for item, key in cache_misses_list:
            # Create signature from prompt + system + model
            signature = f"{item.prompt}|{item.system}|{item.model}"

            if signature not in prompt_groups:
                prompt_groups[signature] = []

            prompt_groups[signature].append((item, key))

        # Extract unique representative and collect duplicates
        unique_misses = []
        duplicate_map = {}

        for _, items_with_keys in prompt_groups.items():
            if len(items_with_keys) == 1:
                # No duplicates, just add to unique
                unique_misses.append(items_with_keys[0])
            else:
                # Multiple items with same prompt - execute first, replicate to others
                representative = items_with_keys[0]
                unique_misses.append(representative)

                # Map representative key to duplicates (excluding representative itself)
                representative_key = representative[1]
                if representative_key not in duplicate_map:
                    duplicate_map[representative_key] = []

                duplicate_map[representative_key].extend(items_with_keys[1:])

        return unique_misses, duplicate_map

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
