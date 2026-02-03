from cohezion.infrastructure import SemanticPrefetcher, get_semantic_prefetcher


class TieredCacheManager:
    """Unified cache manager with tiered architecture."""

    def __init__(self):
        self._backends: list[CacheBackend] = []
        self._metrics = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "prefetch_hits": 0,
            "prefetch_misses": 0,
        }
        self._lock = asyncio.Lock()
        self._prefetcher = get_semantic_prefetcher()
        self._middleware = PrefetchMiddleware(self._prefetcher)

    async def get(
        self, model: str, prompt: str, images: list[str] | None = None
    ) -> Any | None:
        """Get cached entry with automatic tier traversal."""
        key = CacheKey.create(model, prompt, images)

        # Check if we have prefetch predictions for this agent
        if hasattr(self, "_current_agent") and self._current_agent:
            await self._middleware.process_request(self._current_agent, prompt)

        # Traverse tiers from fastest to slowest
        for backend in self._backends:
            try:
                entry = await backend.get(key)
                if entry:
                    # Update metrics and return
                    self._metrics["hits"] += 1
                    return entry.response

            except Exception as e:
                logger.warning(f"Cache backend failed: {e}")
                continue

        # Cache miss
        self._metrics["misses"] += 1
        return None

    async def set(
        self,
        model: str,
        prompt: str,
        response: Any,
        images: list[str] | None = None,
        ttl_seconds: int = 3600,
        **metadata,
    ) -> None:
        """Set cache entry with automatic tier writing."""
        key = CacheKey.create(model, prompt, images)

        # Create cache entry
        entry = CacheEntry(
            key=key,
            response=response,
            metadata=metadata,
            created_at=datetime.now(),
            ttl_seconds=ttl_seconds,
        )

        # Write to all tiers
        tasks = []
        for backend in self._backends:
            tasks.append(backend.set(key, entry))

        # Record behavior for prefetching
        if hasattr(self, "_current_agent") and self._current_agent:
            cache_result = "hit" if response is not None else "miss"
            asyncio.create_task(
                self._prefetcher.record_behavior(
                    self._current_agent, prompt, cache_result
                )
            )

        # Wait for all writes to complete
        await asyncio.gather(*tasks, return_exceptions=True)

    async def warmup_cache(self, agent: BaseAgent, prompt: str) -> None:
        """Warm up cache with intelligent prefetching."""
        if not hasattr(self, "_current_agent"):
            return

        self._current_agent = agent
        await self._middleware.process_request(agent, prompt)
        self._current_agent = None


# Global semantic prefetcher instance
_global_prefetcher = None


def get_semantic_prefetcher() -> SemanticPrefetcher:
    """Get global semantic prefetcher instance."""
    global _global_prefetcher
    if _global_prefetcher is None:
        _global_prefetcher = SemanticPrefetcher()
    return _global_prefetcher


def reset_semantic_prefetcher() -> None:
    """Reset global prefetcher instance."""
    global _global_prefetcher
    _global_prefetcher = None
