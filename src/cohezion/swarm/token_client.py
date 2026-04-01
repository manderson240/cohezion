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

import requests  # type: ignore[import-untyped]

from cohezion.core.config import CohezionConfig
from cohezion.swarm.batch_processor import BatchItem, BatchProcessor, BatchResult
from cohezion.swarm.persistent_token_cache import PersistentTokenCache
from cohezion.swarm.semantic_cache import SemanticCache


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
        timeout: float = 1200.0,
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
        model: str = "phi4:latest",
        system: str = "",
        **kwargs: Any,
    ) -> tuple[str, int]:
        """Generate response from Ollama via standard API.

        Args:
            prompt: User prompt
            model: Model name
            system: System prompt

        Returns:
            Tuple of (response_text, tokens_used)
        """
        for attempt in range(self.max_retries):
            try:
                # Construct standard Ollama messages
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})

                # Normalize base URL: strip trailing slashes, /api, or /v1 to prevent doubling
                clean_base = self.base_url.rstrip("/")
                if clean_base.endswith("/api"):
                    clean_base = clean_base[:-4]
                if clean_base.endswith("/v1"):
                    clean_base = clean_base[:-3]

                # Using /api/chat for better compatibility with message structures
                num_predict = kwargs.get("max_tokens", 2048)
                response = requests.post(
                    f"{clean_base}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "num_predict": num_predict,
                        },
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()

                data = response.json()
                content = data.get("message", {}).get("content", "")
                tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)

                return content, tokens

            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(
                        f"Ollama request failed after {self.max_retries} retries: {e}"
                    ) from e

                wait_time = 0.5 * (2**attempt)
                logger.warning(
                    "Ollama request failed (attempt %s/%s), retrying in %s seconds: %s",
                    attempt + 1,
                    self.max_retries,
                    f"{wait_time:.1f}",
                    e,
                )
                await asyncio.sleep(wait_time)

        raise RuntimeError("Unexpected retry loop exit")


class TokenEfficientClient:
    """Token-efficient Ollama/ngrok client with caching and batch processing.

    Two-layer optimization:
      Layer 1: Cache (SHA-256 hash) - Eliminates redundant API calls
      Layer 2: Batch (Phase 1 cache lookup + Phase 2 parallel) - Maximizes throughput

    Supports multi-provider routing via ngrok AI Gateway with fallback to local Ollama.

    Example usage::

        client = TokenEfficientClient(config=CohezionConfig())
        response, tokens = await client.generate(
            prompt="Explain quantum computing",
            model="qwen3-coder:30b"
        )

        # With ngrok gateway
        client = TokenEfficientClient(
            ngrok_endpoint="https://xxxxx.ngrok.app/v1",
            ngrok_api_key="your-key",
            enable_ngrok_failover=True,
        )
    """

    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        router: Any = None,
        config: CohezionConfig | None = None,
        use_persistent_cache: bool = True,
        cache_dir: str = "data/cache",
        use_semantic_cache: bool = True,
        semantic_threshold: float = 0.95,
        ngrok_endpoint: str | None = None,
        ngrok_api_key: str | None = None,
        enable_ngrok_failover: bool = True,
    ):
        """Initialize token-efficient client.

        Args:
            ollama_base_url: Ollama API base URL
            router: Model router (e.g., AdaptiveRouterAdapter) for routing decisions
            config: CohezionConfig with cache, batch, inference settings
            use_persistent_cache: Whether to use persistent JSONL cache (default: True)
            cache_dir: Directory for cache storage (default: data/cache)
            use_semantic_cache: Whether to use L2 semantic fuzzy matching (default: True)
            semantic_threshold: Min cosine similarity for semantic match (default: 0.95)
            ngrok_endpoint: ngrok gateway endpoint (enables multi-provider routing)
            ngrok_api_key: ngrok API key for authentication
            enable_ngrok_failover: Whether to failover to Ollama if ngrok fails (default: True)
        """
        # Normalize base URL: strip trailing slashes, /api, or /v1
        clean_base = ollama_base_url.rstrip("/")
        if clean_base.endswith("/api"):
            clean_base = clean_base[:-4]
        if clean_base.endswith("/v1"):
            clean_base = clean_base[:-3]

        # Initialize with ngrok gateway if configured
        if ngrok_endpoint:
            from cohezion.gateway import NgrokAIGateway

            self.ollama = NgrokAIGateway(
                ngrok_endpoint=ngrok_endpoint,
                ngrok_api_key=ngrok_api_key,
                fallback_ollama_url=clean_base,
                enable_failover=enable_ngrok_failover,
            )
            from urllib.parse import urlparse

            _safe_host = urlparse(ngrok_endpoint).netloc
            logger.info("TokenEfficientClient using ngrok gateway host: %s", _safe_host)
        else:
            self.ollama = ResilientOllamaClient(base_url=clean_base)

        self.router = router
        self.config = config or CohezionConfig()
        self.semantic_threshold = semantic_threshold

        # Initialize cache - persistent by default for session restore
        if use_persistent_cache:
            persistent_cache = PersistentTokenCache(
                cache_dir=cache_dir, persistence_enabled=True, auto_restore=True
            )
            self.batch_processor = BatchProcessor(self, self.config, cache=persistent_cache)
        else:
            self.batch_processor = BatchProcessor(self, self.config)

        # Initialize L2 semantic cache (non-blocking)
        self.semantic_cache: SemanticCache | None = None
        if use_semantic_cache:
            try:
                self.semantic_cache = SemanticCache(
                    similarity_threshold=semantic_threshold,
                    embedding_dim=384,
                    max_entries=1000,
                    cache_dir=cache_dir,
                )
                logger.debug("SemanticCache initialized for L2 fuzzy matching")
            except Exception as e:
                logger.warning(f"Failed to initialize semantic cache, disabling L2: {e}")
                self.semantic_cache = None

        # Metrics
        self._total_tokens = 0
        self._cache_hits = 0  # L1 exact hits
        self._semantic_hits = 0  # L2 semantic hits
        self._semantic_confidence_sum = 0.0  # For average confidence
        self._cache_misses = 0
        self._api_calls = 0
        self._start_time = time.time()

    async def generate(
        self,
        prompt: str,
        model: str = "phi3:mini",
        system: str = "",
        **kwargs: Any,
    ) -> tuple[str, int]:
        """Generate response with three-tier caching (L1 exact, L2 semantic, L3 persistent).

        Cache hierarchy:
          L1: Exact SHA-256 hash (0-1ms) - in-memory
          L2: Semantic fuzzy matching (2-5ms) - semantic embeddings
          L3: Persistent JSONL (10-50ms) - disk
          Fallback: Generate new via Ollama

        Args:
            prompt: User prompt
            model: Model name
            system: System prompt

        Returns:
            Tuple of (response_text, tokens_used)
        """
        # L1: Check exact cache
        cache_key = self._cache_key(prompt, system, model)
        if cache_key in self.batch_processor.cache:
            entry = self.batch_processor.cache[cache_key]
            self._cache_hits += 1
            logger.debug("L1 cache hit for prompt (saved %d tokens)", entry.tokens_used)
            return entry.value, entry.tokens_used

        # L2: Check semantic cache (fuzzy matching)
        if self.semantic_cache:
            try:
                semantic_hit = await self.semantic_cache.get(prompt, system)
                if semantic_hit:
                    self._semantic_hits += 1
                    self._semantic_confidence_sum += semantic_hit.confidence
                    logger.debug(
                        "L2 semantic cache hit with confidence %.3f (saved %d tokens)",
                        semantic_hit.confidence,
                        0,  # Semantic hits don't have token count in the hit object
                    )
                    # Store in L1 cache for future exact matches
                    from cohezion.swarm.batch_processor import CacheEntry

                    self.batch_processor.cache[cache_key] = CacheEntry(
                        key=cache_key,
                        value=semantic_hit.value,
                        tokens_used=0,  # Semantic hits don't consume tokens
                    )
                    return semantic_hit.value, 0
            except Exception as e:
                logger.debug(f"L2 semantic cache lookup failed, continuing: {e}")

        # L3/Fallback: Call Ollama (cache miss)
        self._cache_misses += 1
        self._api_calls += 1

        # Use the router if available to select the optimal model
        selected_model = model
        if self.router:
            try:
                # The adapter maps context to SmartRouter TaskType
                selection = await self.router.select_optimal_model(
                    {"task_type": kwargs.get("task_type", "general"), "context_length": len(prompt)}
                )
                selected_model = selection.name
            except Exception as e:
                logger.warning(f"Router selection failed, falling back to {model}: {e}")

        # Use the resilient client with modern chat parameters
        response, tokens = await self.ollama.generate(
            prompt=prompt,
            model=selected_model,
            system=system,
        )

        self._total_tokens += tokens

        # Cache result in both L1 and L2
        from cohezion.swarm.batch_processor import CacheEntry

        cache_entry = CacheEntry(
            key=cache_key,
            value=response,
            tokens_used=tokens,
        )
        self.batch_processor.cache[cache_key] = cache_entry

        # Also store in L2 semantic cache for fuzzy matching
        if self.semantic_cache:
            try:
                await self.semantic_cache.put(
                    prompt=prompt,
                    system=system,
                    model=model,
                    value=response,
                    cache_key=cache_key,
                )
            except Exception as e:
                logger.debug(f"Failed to store in L2 semantic cache: {e}")

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

    @property
    def _cache(self) -> dict:
        """Cache dict for persistence compatibility (WarmCacheLoader)."""
        return self.batch_processor.cache

    @property
    def _cache_max_size(self) -> int:
        """Max cache size for persistence compatibility (WarmCacheLoader)."""
        return self.config.cache.max_size

    def get_metrics(self) -> dict[str, Any]:
        """Get token efficiency metrics including L1 exact and L2 semantic cache.

        Returns:
            Dict with cache hit rates, semantic confidence, tokens, latency, etc.
        """
        elapsed = time.time() - self._start_time
        total_cache_hits = self._cache_hits + self._semantic_hits
        total_ops = total_cache_hits + self._cache_misses
        l1_hit_rate = self._cache_hits / total_ops if total_ops > 0 else 0.0
        l2_hit_rate = self._semantic_hits / total_ops if total_ops > 0 else 0.0
        combined_hit_rate = total_cache_hits / total_ops if total_ops > 0 else 0.0

        semantic_confidence_avg = (
            self._semantic_confidence_sum / self._semantic_hits if self._semantic_hits > 0 else 0.0
        )

        # Estimate tokens saved
        estimated_tokens_saved = self._cache_hits * self.config.cache.cache_hit_value

        metrics = {
            # L1 (exact cache)
            "l1_hit_rate": l1_hit_rate,
            "l1_hits": self._cache_hits,
            # L2 (semantic cache)
            "l2_hit_rate": l2_hit_rate,
            "l2_hits": self._semantic_hits,
            "l2_avg_confidence": round(semantic_confidence_avg, 4),
            # Combined
            "combined_hit_rate": combined_hit_rate,
            "total_cache_hits": total_cache_hits,
            "cache_misses": self._cache_misses,
            "total_operations": total_ops,
            # Tokens and performance
            "total_tokens": self._total_tokens,
            "api_calls": self._api_calls,
            "estimated_tokens_saved": estimated_tokens_saved,
            "elapsed_seconds": round(elapsed, 2),
            "tokens_per_second": round(self._total_tokens / elapsed, 2) if elapsed > 0 else 0.0,
        }

        # Add semantic cache stats if available
        if self.semantic_cache:
            try:
                semantic_stats = self.semantic_cache.get_stats()
                metrics["semantic_cache_stats"] = semantic_stats
            except Exception as e:
                logger.debug(f"Failed to get semantic cache stats: {e}")

        return metrics

    def clear_cache(self) -> None:
        """Clear the token cache."""
        self.batch_processor.clear_cache()
        logger.info("Token cache cleared")

    def reset_metrics(self) -> None:
        """Reset all metrics including semantic cache."""
        self._total_tokens = 0
        self._cache_hits = 0
        self._semantic_hits = 0
        self._semantic_confidence_sum = 0.0
        self._cache_misses = 0
        self._api_calls = 0
        self._start_time = time.time()
        logger.debug("Metrics reset")
